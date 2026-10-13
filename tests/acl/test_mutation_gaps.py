"""Mutation surfaces reported in the ACL Gaps project, one probe per report.

Each probe drives the exact request shape the report describes, as a user who must be
denied, and expects a clean denial. Destructive probes target throwaway records the
admin creates per scenario, never the shared seeded world.
"""

import uuid
from collections.abc import Iterator

import pytest

from albert import Albert
from albert.collections.worksheets import WorksheetCollection
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError
from albert.resources.lots import Lot
from albert.resources.projects import Project, ProjectClass
from albert.resources.sheets import Component
from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import call
from tests.acl.identities import AclSetupError
from tests.acl.world import World, grant, revoke


def _created_id(resp, what: str) -> str:
    body = resp.body
    if isinstance(body, list) and body:
        body = body[0]
    rid = isinstance(body, dict) and (body.get("albertId") or body.get("id"))
    if not rid:
        raise AclSetupError(f"seeding {what} failed: {resp.status} {resp.body}")
    return rid


def _create_project(admin: Albert, world: World, cls: ProjectClass) -> str:
    try:
        project = admin.projects.create(
            project=Project(
                description=f"{world.prefix} mutation-gap {cls.value}",
                locations=[EntityLink(id=world.location.id)],
                project_class=cls,
            )
        )
    except AlbertHTTPError as err:
        raise AclSetupError(f"seeding {cls.value} project failed: {err}") from err
    return project.id


@pytest.fixture(scope="module")
def private_project(admin: Albert, world: World) -> Iterator[str]:
    """A throwaway private project, the target for parent-keyed deletes (PLSV-813)."""
    pid = _create_project(admin, world, ProjectClass.PRIVATE)
    yield pid
    call(admin, "DELETE", f"/api/v3/projects/{pid}")


@pytest.fixture(scope="module")
def shared_project(admin: Albert, world: World) -> Iterator[str]:
    """A throwaway shared project, the target for class changes (PLSV-829)."""
    pid = _create_project(admin, world, ProjectClass.SHARED)
    yield pid
    call(admin, "DELETE", f"/api/v3/projects/{pid}")


@pytest.fixture(scope="module")
def foreign_link(admin: Albert, world: World) -> Iterator[str]:
    """A link created by the admin between two inventory items (PLSV-826)."""
    resp = call(
        admin,
        "POST",
        "/api/v3/links",
        json=[
            {
                "Parent": {"id": world.inventories[AccessClass.SHARED].ids[Kind.INVENTORY]},
                "Child": {"id": world.inventories[AccessClass.RESTRICTED].ids[Kind.INVENTORY]},
                "category": "linkedInventory",
            }
        ],
    )
    lid = _created_id(resp, "link")
    yield lid
    call(admin, "DELETE", f"/api/v3/links/{lid}")


@pytest.fixture(scope="module")
def throwaway_lot(admin: Albert, world: World) -> Iterator[str]:
    """A lot on the shared inventory item, created per run (PLSV-826)."""
    lots = admin.lots.create(
        lots=[
            Lot(
                inventory_id=world.inventories[AccessClass.SHARED].ids[Kind.INVENTORY],
                storage_location=EntityLink(id=world.storage_location.id),
                initial_quantity=1.0,
                inventory_on_hand=1.0,
            )
        ]
    )
    if not lots:
        raise AclSetupError("seeding lot failed: nothing returned")
    lid = lots[0].id
    yield lid
    call(admin, "DELETE", "/api/v3/lots", params={"id": lid})


@pytest.fixture(scope="module")
def private_template(admin: Albert, world: World) -> Iterator[str]:
    """A private data template, the target for a class change (PLSV-830)."""
    resp = call(
        admin,
        "POST",
        "/api/v3/datatemplates",
        json={"name": f"{world.prefix} acl-template", "class": "private"},
    )
    tid = _created_id(resp, "data template")
    current = call(admin, "GET", f"/api/v3/datatemplates/{tid}")
    if isinstance(current.body, dict) and current.body.get("class") != "private":
        fix = call(
            admin,
            "PATCH",
            f"/api/v3/datatemplates/{tid}",
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "class",
                        "oldValue": current.body.get("class"),
                        "newValue": "private",
                    }
                ]
            },
        )
        if fix.status >= 300:
            raise AclSetupError(f"could not make template private: {fix.status} {fix.body}")
    yield tid
    call(admin, "DELETE", f"/api/v3/datatemplates/{tid}")


@pytest.fixture(scope="module")
def chat_records(admin: Albert, switcher, world: World) -> Iterator[dict[str, str]]:
    """A chat session and folder owned by userA, plus a session created with a
    caller-supplied ``class`` (AI-2245)."""
    owner = switcher.use("ask-albert", ["AskAlbertFullAccess"])
    session = call(
        owner,
        "POST",
        "/api/v3/chats/sessions",
        json={"name": f"{world.prefix} chat", "sourceSessionId": str(uuid.uuid4())},
    )
    sid = _created_id(session, "chat session")
    folder = call(owner, "POST", "/api/v3/chats/folders", json={"name": f"{world.prefix} folder"})
    fid = _created_id(folder, "chat folder")
    shared = call(
        owner,
        "POST",
        "/api/v3/chats/sessions",
        json={
            "name": f"{world.prefix} chat-class",
            "sourceSessionId": str(uuid.uuid4()),
            "class": "shared",
        },
    )
    shared_sid = _created_id(shared, "chat session with class")
    yield {"session": sid, "folder": fid, "shared_session": shared_sid}
    call(admin, "DELETE", f"/api/v3/chats/sessions/{sid}")
    call(admin, "DELETE", f"/api/v3/chats/folders/{fid}")
    call(admin, "DELETE", f"/api/v3/chats/sessions/{shared_sid}")


def test_link_delete_foreign_user(request, admin, user_b, foreign_link):
    """Test that a standard user cannot delete another user's link (PLSV-826)."""
    admin_control(call(admin, "GET", f"/api/v3/links/{foreign_link}"), "link.read")
    check(
        request,
        scenario="PLSV-826:shared_delete",
        subject="no-grant",
        action="link.delete",
        expect=Expect.DENY,
        resp=call(user_b, "DELETE", f"/api/v3/links/{foreign_link}"),
    )


@pytest.mark.parametrize("base", ["tasks", "inventories"], ids=lambda b: b)
def test_parent_keyed_delete(request, admin, user_b, private_project, base):
    """Test that a no-grant user cannot run a parent-keyed delete against a private
    project (PLSV-813)."""
    path = f"/api/v3/{base}/project/{private_project}"
    admin_control(call(admin, "GET", f"/api/v3/projects/{private_project}"), f"{base}.parent")
    check(
        request,
        scenario="PLSV-813:parent_delete",
        subject="no-grant",
        action=f"{base}.delete_by_parent",
        expect=Expect.DENY,
        resp=call(user_b, "DELETE", path),
    )


def test_lot_delete_edit_policy(request, admin, switcher, throwaway_lot):
    """Test that an Inventory Edit policy holder cannot deactivate a lot (PLSV-826;
    lot delete is Full-tier only per PLSV-780)."""
    user = switcher.use("inventory-edit", ["InventoryEditAccess"])
    admin_control(call(admin, "GET", f"/api/v3/lots/{throwaway_lot}"), "lot.read")
    check(
        request,
        scenario="PLSV-826:shared_delete",
        subject="InventoryEditAccess",
        action="lot.delete",
        expect=Expect.DENY,
        resp=call(user, "DELETE", "/api/v3/lots", params={"id": throwaway_lot}),
    )


def test_inventory_bulk_update_confidential(request, admin, switcher, world):
    """Test that an Inventory Edit policy holder cannot bulk-edit a confidential inventory
    item through the collection-level update (PLSV-826)."""
    inv = world.inventories[AccessClass.CONFIDENTIAL].ids[Kind.INVENTORY]
    current = call(admin, "GET", f"/api/v3/inventories/{inv}")
    admin_control(current, "inventory.read")
    description = current.body.get("description") if isinstance(current.body, dict) else None
    user = switcher.use("inventory-edit", ["InventoryEditAccess"])
    try:
        check(
            request,
            scenario="PLSV-826:bulk_update",
            subject="InventoryEditAccess",
            action="inventory.bulk_update",
            expect=Expect.DENY,
            resp=call(
                user,
                "PATCH",
                "/api/v3/inventories",
                json=[
                    {
                        "id": inv,
                        "data": [
                            {
                                "operation": "update",
                                "attribute": "description",
                                "oldValue": description,
                                "newValue": "acl-gap",
                            }
                        ],
                    }
                ],
            ),
        )
    finally:
        call(
            admin,
            "PATCH",
            f"/api/v3/inventories/{inv}",
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "description",
                        "oldValue": "acl-gap",
                        "newValue": description,
                    }
                ]
            },
        )


def test_attribute_values_delete(request, admin, switcher, world):
    """Test that an Inventory Edit policy holder cannot delete values off a confidential
    inventory item by its parent id (PLSV-813, PLSV-826)."""
    listing = call(admin, "GET", "/api/v3/attributes", params={"limit": 1})
    admin_control(listing, "attributes.list")
    items = listing.items()
    if not items:
        raise AclSetupError("no attributes on tenant to build the delete-values probe")
    attribute_id = items[0].get("albertId")
    inv = world.inventories[AccessClass.CONFIDENTIAL].ids[Kind.INVENTORY]
    user = switcher.use("inventory-edit", ["InventoryEditAccess"])
    check(
        request,
        scenario="PLSV-813:parent_delete",
        subject="InventoryEditAccess",
        action="attributes.delete_values",
        expect=Expect.DENY,
        resp=call(
            user,
            "DELETE",
            f"/api/v3/attributes/values/{inv}",
            params={"attributeId": [attribute_id]},
        ),
    )


def test_project_class_change(request, admin, switcher, user_ids, shared_project):
    """Test that only an owner-level grant may change a project's class (PLSV-829)."""
    body = {
        "data": [
            {
                "operation": "update",
                "attribute": "class",
                "oldValue": "shared",
                "newValue": "confidential",
            }
        ]
    }
    path = f"/api/v3/projects/{shared_project}"
    grant(admin, shared_project, user_ids["userA"], "ProjectEditor")
    try:
        editor = switcher.use("projects-edit", ["ProjectsEditAccess"])
        check(
            request,
            scenario="PLSV-829:class_change",
            subject="ProjectsEditAccess+ProjectEditor",
            action="project.class_change",
            expect=Expect.DENY,
            resp=call(editor, "PATCH", path, json=body),
        )
        revoke(admin, shared_project, user_ids["userA"])
        grant(admin, shared_project, user_ids["userA"], "ProjectOwner")
        current = call(admin, "GET", path)
        admin_control(current, "project.read")
        old_value = current.body.get("class", "shared")
        owner_body = {
            "data": [
                {
                    "operation": "update",
                    "attribute": "class",
                    "oldValue": old_value,
                    "newValue": "confidential" if old_value != "confidential" else "shared",
                }
            ]
        }
        owner = switcher.use("projects-full", ["ProjectsFullAccess"])
        check(
            request,
            scenario="PLSV-829:class_change",
            subject="ProjectsFullAccess+ProjectOwner",
            action="project.class_change",
            expect=Expect.ALLOW,
            resp=call(owner, "PATCH", path, json=owner_body),
        )
    finally:
        revoke(admin, shared_project, user_ids["userA"])


def test_datatemplate_class_change(request, switcher, private_template):
    """Test that a Data Templates Edit policy holder cannot flip a template's class to
    a wider audience (PLSV-830)."""
    user = switcher.use("datatemplates-edit", ["DataTemplatesEditAccess"])
    check(
        request,
        scenario="PLSV-830:class_change",
        subject="DataTemplatesEditAccess",
        action="datatemplate.class_change",
        expect=Expect.DENY,
        resp=call(
            user,
            "PATCH",
            f"/api/v3/datatemplates/{private_template}",
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "class",
                        "oldValue": "private",
                        "newValue": "restricted",
                    }
                ]
            },
        ),
    )


def test_sheet_template_delete_keeps_formulas(request, admin, world):
    """Test that deleting a sheet template leaves the source project's formula inventory
    untouched (PLSV-785)."""
    pid = _create_project(admin, world, ProjectClass.PRIVATE)
    fid = None
    try:
        sheets = WorksheetCollection(session=admin.session)
        try:
            wks = sheets.get_by_project_id(project_id=pid)
        except AlbertHTTPError:
            wks = sheets.setup_worksheet(project_id=pid)
        if not wks.sheets:
            wks = sheets.add_sheet(project_id=pid, sheet_name="acl")
        raw = admin.inventory.get_by_id(
            id=world.inventories[AccessClass.SHARED].ids[Kind.INVENTORY]
        )
        column = wks.sheets[0].add_formulation(
            formulation_name=f"{world.prefix} template formula",
            components=[Component(inventory_item=raw, amount=100)],
        )
        fid = column.inventory_id
        if not fid:
            raise AclSetupError("add_formulation returned no formula inventory id")
        template = sheets.create_sheet_template(
            project_id=pid,
            source_sheet_name=wks.sheets[0].name,
            template_name=f"{world.prefix} acl template",
        )
        admin_control(
            call(admin, "DELETE", f"/api/v3/customtemplates/{template.id}"), "template.delete"
        )
        check(
            request,
            scenario="PLSV-785:template_cascade",
            subject="admin",
            action="formula.survives_template_delete",
            expect=Expect.ALLOW,
            resp=call(admin, "GET", f"/api/v3/inventories/{fid}"),
            canary=fid,
        )
    finally:
        call(admin, "DELETE", f"/api/v3/projects/{pid}")


@pytest.mark.parametrize("verb", ["GET", "PATCH", "DELETE"], ids=lambda v: v.lower())
def test_chat_session_owner_only(request, user_b, chat_records, verb):
    """Test that a non-owner cannot read, rename, or delete another user's chat session
    (AI-2245)."""
    kwargs = (
        {"json": {"data": [{"operation": "update", "attribute": "name", "newValue": "acl"}]}}
        if verb == "PATCH"
        else {}
    )
    check(
        request,
        scenario="AI-2245:chat_owner",
        subject="no-grant",
        action=f"chat_session.{verb.lower()}",
        expect=Expect.DENY,
        resp=call(user_b, verb, f"/api/v3/chats/sessions/{chat_records['session']}", **kwargs),
    )


@pytest.mark.parametrize("verb", ["GET", "DELETE"], ids=lambda v: v.lower())
def test_chat_folder_owner_only(request, user_b, chat_records, verb):
    """Test that a non-owner cannot read or delete another user's chat folder (AI-2245)."""
    check(
        request,
        scenario="AI-2245:chat_owner",
        subject="no-grant",
        action=f"chat_folder.{verb.lower()}",
        expect=Expect.DENY,
        resp=call(user_b, verb, f"/api/v3/chats/folders/{chat_records['folder']}"),
    )


def test_chat_messages_owner_only(request, admin, user_b, chat_records):
    """Test that a non-owner cannot list another user's chat messages (AI-2245)."""
    path = f"/api/v3/chats/sessions/{chat_records['session']}/messages"
    admin_control(call(admin, "GET", path), "chat_messages.list")
    check(
        request,
        scenario="AI-2245:chat_owner",
        subject="no-grant",
        action="chat_messages.list",
        expect=Expect.DENY,
        resp=call(user_b, "GET", path),
    )


def test_chat_session_class_is_server_enforced(request, admin, chat_records):
    """Test that a caller-supplied class on chat create is ignored and the record stays
    confidential (AI-2245)."""
    check(
        request,
        scenario="AI-2245:chat_class",
        subject="AskAlbertFullAccess",
        action="chat_session.class_default",
        expect=Expect.ALLOW,
        resp=call(admin, "GET", f"/api/v3/acl/{chat_records['shared_session']}"),
        canary="confidential",
    )
