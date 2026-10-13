"""Record access: FGC level x record kind x verb, and class semantics with no grant.

userA holds a broad role (every Full policy for the record modules) so the policy layer
never masks the record layer; the FGC on the record is the only variable. Grants are
made on the project (or inventory item) only; children must inherit.
"""

import pytest

from albert import Albert
from albert.exceptions import AlbertHTTPError
from albert.resources.acls import ACL
from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import (
    INVENTORY_LEVELS,
    PROJECT_LEVELS,
    AccessClass,
    Kind,
    ReadPath,
    class_expect,
)
from tests.acl.contract.model import Expect, Verb
from tests.acl.http import Response, call
from tests.acl.world import INVENTORY_CLASSES, PROJECT_CLASSES, World, grant, revoke
from tests.utils.wait import poll_until

BROAD_POLICIES = [
    "ProjectsFullAccess",
    "FormulaFullAccess",
    "TasksFullAccess",
    "InventoryFullAccess",
    "ReportsFullAccess",
    "PricingFullAccess",
]

READ_PATH = {
    Kind.PROJECT: "/api/v3/projects/{}",
    Kind.FORMULA: "/api/v3/inventories/{}",
    Kind.BATCH_TASK: "/api/v3/tasks/{}",
    Kind.LOT: "/api/v3/lots/{}",
    Kind.TASK_CHILD: "/api/v3/notes/{}",
    Kind.PROJECT_CHILD: "/api/v3/notebooks/{}",
    Kind.INVENTORY: "/api/v3/inventories/{}",
    Kind.INVENTORY_CHILD: "/api/v3/notes/{}",
}

# (attribute, new value from old). Edits append so the seeded canary stays searchable.
UPDATE_ATTR = {
    Kind.PROJECT: ("description", lambda old: f"{old} e"),
    Kind.TASK_CHILD: ("note", lambda old: f"{old} e"),
    Kind.INVENTORY: ("description", lambda old: f"{old} e"),
    Kind.LOT: ("inventoryOnHand", lambda old: float(old or 0) + 1),
}


def update_body(admin: Albert, kind: Kind, path: str) -> dict:
    current = call(admin, "GET", path)
    admin_control(current, f"{kind.value}.read")
    attribute, new = UPDATE_ATTR[kind]
    old = current.body.get(attribute)
    return {
        "data": [
            {"operation": "update", "attribute": attribute, "oldValue": old, "newValue": new(old)}
        ]
    }


@pytest.fixture(scope="module")
def broad_user(switcher) -> Albert:
    return switcher.use("broad-records", BROAD_POLICIES)


def _project_cases():
    for level in PROJECT_LEVELS.values():
        for kind in READ_PATH:
            if kind in (Kind.INVENTORY, Kind.INVENTORY_CHILD):
                continue
            yield pytest.param(level, kind, Verb.READ, id=f"{level.level}-{kind.value}-read")
        for kind in UPDATE_ATTR:
            if kind in (Kind.INVENTORY,):
                continue
            yield pytest.param(level, kind, Verb.UPDATE, id=f"{level.level}-{kind.value}-update")


@pytest.mark.parametrize(("level", "kind", "verb"), list(_project_cases()))
def test_project_fgc(request, admin, broad_user, user_ids, world: World, level, kind, verb):
    """Test that a project-level FGC grant yields exactly the contracted child access."""
    tree = world.projects[AccessClass.PRIVATE]
    rid = tree.ids[kind]
    pid = tree.ids[Kind.PROJECT]
    path = READ_PATH[kind].format(rid)
    grant(admin, pid, user_ids["userA"], level.level)
    try:
        if verb is Verb.READ:
            admin_control(call(admin, "GET", path), f"{kind.value}.read")
            resp = call(broad_user, "GET", path)
        else:
            resp = call(broad_user, "PATCH", path, json=update_body(admin, kind, path))
        check(
            request,
            scenario="record_fgc",
            subject=level.level,
            action=f"{kind.value}.{verb.value}",
            expect=level.expect(kind, verb),
            resp=resp,
        )
    finally:
        revoke(admin, pid, user_ids["userA"])


@pytest.mark.parametrize("level", list(INVENTORY_LEVELS.values()), ids=lambda lv: lv.level)
@pytest.mark.parametrize("kind", [Kind.INVENTORY, Kind.LOT, Kind.INVENTORY_CHILD])
def test_inventory_fgc_read(request, admin, broad_user, user_ids, world: World, level, kind):
    """Test that an inventory FGC grant on a confidential item yields the contracted read."""
    tree = world.inventories[AccessClass.CONFIDENTIAL]
    inv = tree.ids[Kind.INVENTORY]
    path = READ_PATH[kind].format(tree.ids[kind])
    grant(admin, inv, user_ids["userA"], level.level)
    try:
        admin_control(call(admin, "GET", path), f"{kind.value}.read")
        check(
            request,
            scenario="record_fgc",
            subject=level.level,
            action=f"{kind.value}.read",
            expect=level.expect(kind, Verb.READ),
            resp=call(broad_user, "GET", path),
        )
    finally:
        revoke(admin, inv, user_ids["userA"])


@pytest.mark.parametrize(
    ("kind", "cls"),
    [(Kind.PROJECT, cls) for cls in PROJECT_CLASSES]
    + [(Kind.INVENTORY, cls) for cls in INVENTORY_CLASSES],
    ids=lambda v: v.value,
)
def test_class_without_grant(request, admin, user_b, world: World, cls, kind):
    """Test that a standard user with no ACL entry gets the class-default direct read."""
    tree = (world.projects if kind is Kind.PROJECT else world.inventories)[cls]
    path = READ_PATH[kind].format(tree.ids[kind])
    admin_control(call(admin, "GET", path), f"{kind.value}.read")
    check(
        request,
        scenario="record_class",
        subject=f"class={cls.value}",
        action=f"{kind.value}.get_by_id",
        expect=class_expect(cls, Verb.READ, ReadPath.GET_BY_ID),
        resp=call(user_b, "GET", path),
    )


def _sdk_share(user: Albert, kind: Kind, rid: str, entry: ACL) -> Response:
    """Share through the SDK: add an ACL entry and update the record as ``user``."""
    try:
        if kind is Kind.PROJECT:
            project = user.projects.get_by_id(id=rid)
            project.acl = [*(project.acl or []), entry]
            user.projects.update(project=project)
        else:
            item = user.inventory.get_by_id(id=rid)
            item.acls = [*item.acls, entry]
            user.inventory.update(inventory_item=item)
    except AlbertHTTPError as err:
        if err.response is None:
            raise
        return Response(status=err.response.status_code, body=err.response.text)
    return Response(status=204, body=None)


@pytest.mark.parametrize("kind", [Kind.PROJECT, Kind.INVENTORY])
def test_share_with_edit_policy_and_owner(request, admin, switcher, user_ids, world, kind):
    """Test sharing with an Edit-level policy plus an owner FGC: a ProjectOwner may share a
    project; an inventory share still needs Inventory Full Access (SDK-216)."""
    if kind is Kind.PROJECT:
        tree = world.projects[AccessClass.PRIVATE]
    else:
        tree = world.inventories[AccessClass.CONFIDENTIAL]
    rid = tree.ids[kind]
    owner = "ProjectOwner" if kind is Kind.PROJECT else "InventoryOwner"
    edit_policy = "ProjectsEditAccess" if kind is Kind.PROJECT else "InventoryEditAccess"
    user = switcher.use(edit_policy, [edit_policy])
    grant(admin, rid, user_ids["userA"], owner)
    try:
        poll_until(
            lambda: [call(user, "GET", READ_PATH[kind].format(rid))],
            predicate=lambda r: 200 <= r[0].status < 300,
            timeout=90,
            interval=3,
        )
        resp = _sdk_share(user, kind, rid, ACL(id=user_ids["userB"], fgc=owner))
        check(
            request,
            scenario="share",
            subject=f"{edit_policy}+{owner}",
            action=f"{kind.value}.share",
            expect=Expect.ALLOW if kind is Kind.PROJECT else Expect.DENY,
            resp=resp,
        )
    finally:
        revoke(admin, rid, user_ids["userB"])
        revoke(admin, rid, user_ids["userA"])
