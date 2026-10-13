"""Mutation surfaces reported in the ACL Gaps project, one probe per report.

Each probe drives the exact request shape the report describes, as a user who must be
denied, and expects a clean denial. Destructive probes target throwaway records the
admin creates per scenario, never the shared seeded world.
"""

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
from tests.acl.world import World


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
                cost=1.0,
                manufacturer_lot_number=f"ACL-{world.prefix}",
            )
        ]
    )
    if not lots:
        raise AclSetupError("seeding lot failed: nothing returned")
    lid = lots[0].id
    yield lid
    call(admin, "DELETE", "/api/v3/lots", params={"id": lid})


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
    old = float(current.body.get("onHand") or 0) if isinstance(current.body, dict) else 0.0

    def set_on_hand(value: float) -> list[dict]:
        return [
            {
                "id": inv,
                "data": [{"operation": "update", "attribute": "onHand", "newValue": value}],
            }
        ]

    user = switcher.use("inventory-edit", ["InventoryEditAccess"])
    resp = call(user, "PATCH", "/api/v3/inventories", json=set_on_hand(old + 1))
    try:
        if not 200 <= resp.status < 300:
            probe = call(admin, "PATCH", "/api/v3/inventories", json=set_on_hand(old + 1))
            admin_control(probe, "inventory.bulk_update")
            call(admin, "PATCH", "/api/v3/inventories", json=set_on_hand(old))
        check(
            request,
            scenario="PLSV-826:bulk_update",
            subject="InventoryEditAccess",
            action="inventory.bulk_update",
            expect=Expect.DENY,
            resp=resp,
        )
    finally:
        if 200 <= resp.status < 300:
            call(admin, "PATCH", "/api/v3/inventories", json=set_on_hand(old))


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
