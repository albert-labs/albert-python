"""Seeded record trees, one per access class, each carrying a unique canary token.

Built once per session by the admin client using SDK create calls (creation is not under
test here). Seed failures raise ``AclSetupError``: a broken seed must never be reported
as an ACL finding or silently skipped.

Tree per project class::

    Project ─┬─ GeneralTask
             ├─ Notebook
             ├─ Formula (worksheet column) ── Lot
             └─ BatchTask (on formula) ─┬─ Note ── Attachment
                                        └─ Notebook
    Inventory (raw material, class) ─┬─ Lot
                                     ├─ Pricing
                                     └─ Note

Task children hang off the batch task because batch tasks inherit project access, while
general and property tasks are governed by the caller's Tasks policies alone.

Every inventory item, formula, general task, batch task and project notebook also gets a
plain note, a note-wrapped attachment, and a direct attachment (``Tree.children``), so
child-follows-parent checks cover each way a file can hang off a record. The project
notebook additionally embeds a canary-named image for document search.
"""

import shutil
import tempfile
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from albert import Albert
from albert.collections.worksheets import WorksheetCollection
from albert.core.shared.enums import SecurityClass
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.attachments import Attachment, AttachmentCategory
from albert.resources.companies import Company
from albert.resources.inventory import InventoryCategory, InventoryItem, InventoryUnitCategory
from albert.resources.locations import Location
from albert.resources.lots import Lot
from albert.resources.notebooks import ImageBlock, ImageContent, Notebook
from albert.resources.notes import Note
from albert.resources.pricings import Pricing
from albert.resources.projects import Project, ProjectClass
from albert.resources.sheets import Component
from albert.resources.storage_locations import StorageLocation
from albert.resources.tasks import BatchSizeUnit, BatchTask, GeneralTask, TaskInventoryInformation
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.http import call
from tests.acl.identities import AclSetupError

DATA_FILE = Path(__file__).parents[1] / "data" / "dontpanic.jpg"
SDS_FILE = Path(__file__).parents[1] / "data" / "SDS_HCL.pdf"

# Child types seeded under every parent in ``Tree.children``.
NOTE = "note"
ATTACHMENT_NOTE = "attachment_note"
NOTE_ATTACHMENT = "note_attachment"
ATTACHMENT = "attachment"
CHILD_TYPES = (NOTE, ATTACHMENT_NOTE, NOTE_ATTACHMENT, ATTACHMENT)

# Inventory has no private class; projects have no restricted class by default.
INVENTORY_CLASSES = (AccessClass.SHARED, AccessClass.RESTRICTED, AccessClass.CONFIDENTIAL)
PROJECT_CLASSES = (AccessClass.SHARED, AccessClass.PRIVATE, AccessClass.CONFIDENTIAL)


@dataclass
class Tree:
    access_class: AccessClass
    canary: str
    ids: dict[Kind, str] = field(default_factory=dict)
    extra: dict[str, str] = field(default_factory=dict)
    children: dict[Kind, dict[str, str]] = field(default_factory=dict)


@dataclass
class World:
    prefix: str
    location: Location
    storage_location: StorageLocation
    company: Company
    projects: dict[AccessClass, Tree] = field(default_factory=dict)
    inventories: dict[AccessClass, Tree] = field(default_factory=dict)
    created: list[tuple[str, str]] = field(default_factory=list)


def _must(what: str, fn):
    try:
        return fn()
    except AlbertHTTPError as err:
        raise AclSetupError(f"seeding {what} failed: {err}") from err


def build_world(admin: Albert) -> World:
    prefix = f"SDK-ACL-{uuid.uuid4().hex[:8]}"
    location = _must(
        "location",
        lambda: admin.locations.get_or_create(
            location=Location(
                name=f"{prefix} - Lab",
                latitude=40.7,
                longitude=-74.0,
                address="1 ACL Test Way",
            )
        ),
    )
    storage_location = _must(
        "storage location",
        lambda: admin.storage_locations.get_or_create(
            storage_location=StorageLocation(
                name=f"{prefix} - Shelf",
                location=EntityLink(id=location.id),
                address="1 ACL Test Way",
            )
        ),
    )
    company = _must(
        "company", lambda: admin.companies.get_or_create(company=Company(name=f"{prefix} - Co"))
    )
    world = World(
        prefix=prefix, location=location, storage_location=storage_location, company=company
    )
    world.created += [
        ("locations", location.id),
        ("storage_locations", storage_location.id),
        ("companies", company.id),
    ]
    for cls in INVENTORY_CLASSES:
        world.inventories[cls] = _seed_inventory(admin, world, cls)
    for cls in PROJECT_CLASSES:
        world.projects[cls] = _seed_project(admin, world, cls)
    return world


def _seed_inventory(admin: Albert, world: World, cls: AccessClass) -> Tree:
    canary = f"acl{uuid.uuid4().hex[:12]}"
    tree = Tree(cls, canary)
    item = _must(
        f"{cls} inventory",
        lambda: admin.inventory.create(
            inventory_item=InventoryItem(
                name=f"{canary} {world.prefix} RM {cls.value}",
                description=f"ACL canary {canary}",
                category=InventoryCategory.RAW_MATERIALS,
                unit_category=InventoryUnitCategory.MASS,
                security_class=SecurityClass(cls.value),
                company=world.company,
            )
        ),
    )
    tree.ids[Kind.INVENTORY] = item.id
    world.created.append(("inventory", item.id))
    tree.ids[Kind.LOT] = _seed_lot(
        admin,
        world,
        "inventory lot",
        inventory_id=item.id,
        quantity=10.0,
        cost=1.0,
        manufacturer_lot_number=f"ACL-{canary}",
    )
    pricing = _must(
        "pricing",
        lambda: admin.pricings.create(
            pricing=Pricing(
                inventory_id=item.id,
                company=world.company,
                location=world.location,
                price=1.0,
                description=f"ACL canary {canary}",
            )
        ),
    )
    tree.extra["pricing"] = pricing.id
    tree.children[Kind.INVENTORY] = _seed_children(admin, item.id, canary, inventory=True)
    tree.ids[Kind.INVENTORY_CHILD] = tree.children[Kind.INVENTORY][NOTE]
    return tree


def _seed_project(admin: Albert, world: World, cls: AccessClass) -> Tree:
    canary = f"acl{uuid.uuid4().hex[:12]}"
    tree = Tree(cls, canary)
    project = _must(
        f"{cls} project",
        lambda: admin.projects.create(
            project=Project(
                description=f"{canary} {world.prefix} project {cls.value}",
                locations=[EntityLink(id=world.location.id)],
                project_class=ProjectClass(cls.value),
            )
        ),
    )
    pid = project.id
    tree.ids[Kind.PROJECT] = pid
    world.created.append(("projects", pid))

    task = _must(
        "general task",
        lambda: admin.tasks.create(
            task=GeneralTask(
                name=f"{canary} {world.prefix} general",
                parent_id=pid,
                project=project,
                location=world.location,
                inventory_information=[
                    TaskInventoryInformation(
                        inventory_id=world.inventories.get(
                            cls, world.inventories[AccessClass.CONFIDENTIAL]
                        ).ids[Kind.INVENTORY]
                    )
                ],
            )
        ),
    )
    tree.ids[Kind.GENERAL_TASK] = task.id
    world.created.append(("tasks", task.id))

    _seed_formula_chain(admin, world, tree, pid)
    batch_id = tree.ids[Kind.BATCH_TASK]

    for kind in (Kind.GENERAL_TASK, Kind.BATCH_TASK):
        tree.children[kind] = _seed_children(admin, tree.ids[kind], canary)
    tree.children[Kind.FORMULA] = _seed_children(
        admin, tree.ids[Kind.FORMULA], canary, inventory=True
    )
    tree.ids[Kind.TASK_CHILD] = tree.children[Kind.BATCH_TASK][NOTE]
    tree.extra["task_attachment_note"] = tree.children[Kind.BATCH_TASK][ATTACHMENT_NOTE]

    task_nb = _must(
        "task notebook",
        lambda: admin.notebooks.create(
            notebook=Notebook(name=f"{world.prefix} {canary} task nb", parent_id=batch_id)
        ),
    )
    tree.extra["task_notebook"] = task_nb.id
    proj_nb = _must(
        "project notebook",
        lambda: admin.notebooks.create(
            notebook=Notebook(name=f"{world.prefix} {canary} project nb", parent_id=pid)
        ),
    )
    tree.ids[Kind.PROJECT_CHILD] = proj_nb.id
    tree.children[Kind.PROJECT_CHILD] = _seed_children(admin, proj_nb.id, canary)
    _seed_notebook_image(admin, proj_nb, canary)
    return tree


def _seed_children(
    admin: Albert, parent_id: str, canary: str, *, inventory: bool = False
) -> dict[str, str]:
    """Seed a note, a note-wrapped attachment, and a direct attachment under ``parent_id``.

    Inventory parents only accept SDS attachments directly, so they get one.
    """
    note = _must(
        f"note on {parent_id}",
        lambda: admin.notes.create(note=Note(parent_id=parent_id, note=f"ACL canary {canary}")),
    )
    with DATA_FILE.open("rb") as fh:
        wrapper = _must(
            f"note attachment on {parent_id}",
            lambda: admin.attachments.upload_and_attach_file_as_note(
                parent_id=parent_id,
                file_data=fh,
                note_text=f"ACL canary {canary} attachment",
                file_name=f"{canary}.jpg",
            ),
        )
    if not wrapper.attachments:
        raise AclSetupError(f"note attachment on {parent_id} has no attachment")
    with tempfile.TemporaryDirectory() as tmp:
        if inventory:
            sds = Path(tmp) / f"{canary}.pdf"
            shutil.copy(SDS_FILE, sds)
            direct = _must(
                f"SDS attachment on {parent_id}",
                lambda: admin.attachments.upload_and_attach_sds_to_inventory_item(
                    inventory_id=parent_id,
                    file_sds=sds,
                    revision_date=date(2024, 1, 1),
                    storage_class="10-13",
                    un_number="N/A",
                ),
            )
        else:
            key = f"{parent_id}/acl/{canary}.jpg"
            with DATA_FILE.open("rb") as fh:
                _must(
                    f"upload for {parent_id}",
                    lambda: admin.files.sign_and_upload_file(
                        data=fh, name=key, namespace="result", content_type="image/jpeg"
                    ),
                )
            direct = _must(
                f"direct attachment on {parent_id}",
                lambda: admin.attachments.create(
                    attachment=Attachment(
                        parent_id=parent_id,
                        name=f"{canary}.jpg",
                        key=key,
                        namespace="result",
                        category=AttachmentCategory.OTHER,
                    )
                ),
            )
    return {
        NOTE: note.id,
        ATTACHMENT_NOTE: wrapper.id,
        NOTE_ATTACHMENT: wrapper.attachments[0].id,
        ATTACHMENT: direct.id,
    }


def _seed_notebook_image(admin: Albert, notebook: Notebook, canary: str) -> None:
    """Embed a canary-named image, the kind of file project document search indexes."""
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / f"{canary}.jpg"
        shutil.copy(DATA_FILE, image)
        notebook.blocks = [ImageBlock(content=ImageContent(file_path=image, title=canary))]
        _must("notebook image", lambda: admin.notebooks.update_block_content(notebook=notebook))


def _seed_formula_chain(admin: Albert, world: World, tree: Tree, pid: str) -> None:
    sheets = WorksheetCollection(session=admin.session)
    try:
        wks = sheets.get_by_project_id(project_id=pid)
    except AlbertHTTPError:
        wks = _must("worksheet", lambda: sheets.setup_worksheet(project_id=pid))
    if not wks.sheets:
        wks = _must("sheet", lambda: sheets.add_sheet(project_id=pid, sheet_name="acl"))
    raw = admin.inventory.get_by_id(id=world.inventories[AccessClass.SHARED].ids[Kind.INVENTORY])
    column = _must(
        "formula",
        lambda: wks.sheets[0].add_formulation(
            formulation_name=f"{tree.canary} {world.prefix} formula",
            components=[Component(inventory_item=raw, amount=100)],
        ),
    )
    if not column.inventory_id:
        raise AclSetupError("add_formulation returned no formula inventory id")
    fid = column.inventory_id
    tree.ids[Kind.FORMULA] = fid
    batch = _must(
        "batch task",
        lambda: admin.tasks.create(
            task=BatchTask(
                name=f"{tree.canary} {world.prefix} batch",
                batch_size_unit=BatchSizeUnit.GRAMS,
                inventory_information=[
                    TaskInventoryInformation(inventory_id=fid, batch_size=10.0)
                ],
                location=world.location,
                project=EntityLink(id=pid),
                parent_id=pid,
            )
        ),
    )
    tree.ids[Kind.BATCH_TASK] = batch.id
    world.created.append(("tasks", batch.id))
    tree.ids[Kind.LOT] = _seed_lot(admin, world, "formula lot", inventory_id=fid, quantity=5.0)


def _seed_lot(
    admin: Albert, world: World, what: str, *, inventory_id: str, quantity: float, **extra
) -> str:
    lot = Lot(
        inventory_id=inventory_id,
        storage_location=EntityLink(id=world.storage_location.id),
        initial_quantity=quantity,
        inventory_on_hand=quantity,
        **extra,
    )
    created = _must(what, lambda: admin.lots.create(lots=[lot]))
    if not created:
        raise AclSetupError(f"seeding {what} returned no lot (partial failure)")
    return created[0].id


def grant(admin: Albert, resource_id: str, principal_id: str, level: str) -> None:
    resp = call(
        admin,
        "PATCH",
        f"/api/v3/acl/{resource_id}",
        json={
            "data": [
                {
                    "operation": "add",
                    "attribute": "ACL",
                    "newValue": [{"id": principal_id, "fgc": level}],
                }
            ]
        },
    )
    if resp.status >= 300:
        raise AclSetupError(f"grant {level} on {resource_id} failed: {resp.status} {resp.body}")


def revoke(admin: Albert, resource_id: str, principal_id: str) -> None:
    resp = call(
        admin,
        "PATCH",
        f"/api/v3/acl/{resource_id}",
        json={
            "data": [
                {"operation": "delete", "attribute": "ACL", "oldValue": [{"id": principal_id}]}
            ]
        },
    )
    if resp.status >= 300 and resp.status != 404:
        raise AclSetupError(f"revoke on {resource_id} failed: {resp.status} {resp.body}")


def acl_entries(admin: Albert, resource_id: str) -> list[dict]:
    resp = call(admin, "GET", f"/api/v3/acl/{resource_id}")
    if resp.status != 200:
        raise AclSetupError(f"read ACL {resource_id}: {resp.status}")
    return resp.body.get("ACL") or []


def teardown(admin: Albert, world: World) -> None:
    for collection, rid in reversed(world.created):
        with suppress(AlbertHTTPError):
            getattr(admin, collection).delete(id=rid)


__all__ = ["ACL", "AccessControlLevel", "World", "Tree", "build_world", "grant", "revoke"]
