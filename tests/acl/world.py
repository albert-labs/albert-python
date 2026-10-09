"""Seeded record trees, one per access class, each carrying a unique canary token.

Built once per session by the admin client using SDK create calls (creation is not under
test here). Seed failures raise ``AclSetupError``: a broken seed must never be reported
as an ACL finding or silently skipped.

Tree per project class::

    Project ─┬─ GeneralTask ─┬─ Note ── Attachment
             │               └─ Notebook
             ├─ Notebook
             ├─ Formula (worksheet column) ── Lot
             ├─ BatchTask (on formula)
             └─ PropertyTask (on raw-material lot)
    Inventory (raw material, class) ─┬─ Lot
                                     ├─ Pricing
                                     └─ Note
"""

import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from albert import Albert
from albert.collections.worksheets import WorksheetCollection
from albert.core.shared.enums import SecurityClass
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.companies import Company
from albert.resources.inventory import InventoryCategory, InventoryItem, InventoryUnitCategory
from albert.resources.locations import Location
from albert.resources.lots import Lot
from albert.resources.notebooks import Notebook
from albert.resources.notes import Note
from albert.resources.pricings import Pricing
from albert.resources.projects import Project, ProjectClass
from albert.resources.sheets import Component
from albert.resources.tasks import BatchSizeUnit, BatchTask, GeneralTask, TaskInventoryInformation
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.http import call
from tests.acl.identities import AclSetupError

DATA_FILE = Path(__file__).parents[1] / "data" / "dontpanic.jpg"


@dataclass
class Tree:
    access_class: AccessClass
    canary: str
    ids: dict[Kind, str] = field(default_factory=dict)
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class World:
    prefix: str
    location: Location
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
    company = _must(
        "company", lambda: admin.companies.get_or_create(company=Company(name=f"{prefix} - Co"))
    )
    world = World(prefix=prefix, location=location, company=company)
    world.created += [("locations", location.id), ("companies", company.id)]
    for cls in (AccessClass.SHARED, AccessClass.PRIVATE, AccessClass.CONFIDENTIAL):
        world.inventories[cls] = _seed_inventory(admin, world, cls)
        world.projects[cls] = _seed_project(admin, world, cls)
    return world


def _seed_inventory(admin: Albert, world: World, cls: AccessClass) -> Tree:
    canary = f"acl{uuid.uuid4().hex[:12]}"
    tree = Tree(cls, canary)
    item = _must(
        f"{cls} inventory",
        lambda: admin.inventory.create(
            inventory_item=InventoryItem(
                name=f"{world.prefix} {canary} RM {cls.value}",
                description=f"ACL canary {canary}",
                category=InventoryCategory.RAW_MATERIALS,
                unit_category=InventoryUnitCategory.MASS,
                security_class=SecurityClass(cls.value),
                company=world.company,
            )
        ),
    )
    tree.ids[Kind.INVENTORY] = item.id
    world.created.append(("inventories", item.id))
    lots = _must(
        "inventory lot",
        lambda: admin.lots.create(
            lots=[Lot(inventory_id=item.id, inventory_on_hand=10.0, initial_quantity=10.0)]
        ),
    )
    tree.ids[Kind.LOT] = lots[0].id
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
    note = _must(
        "inventory note",
        lambda: admin.notes.create(note=Note(parent_id=item.id, note=f"ACL canary {canary}")),
    )
    tree.ids[Kind.INVENTORY_CHILD] = note.id
    return tree


def _seed_project(admin: Albert, world: World, cls: AccessClass) -> Tree:
    canary = f"acl{uuid.uuid4().hex[:12]}"
    tree = Tree(cls, canary)
    project = _must(
        f"{cls} project",
        lambda: admin.projects.create(
            project=Project(
                description=f"{world.prefix} {canary} project {cls.value}",
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
                name=f"{world.prefix} {canary} general",
                parent_id=pid,
                project=project,
                location=world.location,
                inventory_information=[
                    TaskInventoryInformation(
                        inventory_id=world.inventories[cls].ids[Kind.INVENTORY]
                    )
                ],
            )
        ),
    )
    tree.ids[Kind.GENERAL_TASK] = task.id
    world.created.append(("tasks", task.id))

    note = _must(
        "task note",
        lambda: admin.notes.create(note=Note(parent_id=task.id, note=f"ACL canary {canary}")),
    )
    tree.ids[Kind.TASK_CHILD] = note.id
    with DATA_FILE.open("rb") as fh:
        att_note = _must(
            "task attachment",
            lambda: admin.attachments.upload_and_attach_file_as_note(
                parent_id=task.id,
                file_data=fh,
                note_text=f"ACL canary {canary} attachment",
                file_name=f"{canary}.jpg",
            ),
        )
    tree.extra["task_attachment_note"] = att_note.id

    task_nb = _must(
        "task notebook",
        lambda: admin.notebooks.create(
            notebook=Notebook(name=f"{world.prefix} {canary} task nb", parent_id=task.id)
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

    _seed_formula_chain(admin, world, tree, pid)
    return tree


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
            formulation_name=f"{world.prefix} {tree.canary} formula",
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
                name=f"{world.prefix} {tree.canary} batch",
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
    lots = _must(
        "formula lot",
        lambda: admin.lots.create(
            lots=[Lot(inventory_id=fid, inventory_on_hand=5.0, initial_quantity=5.0)]
        ),
    )
    tree.ids[Kind.LOT] = lots[0].id


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
