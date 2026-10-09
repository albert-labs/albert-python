"""Record access: FGC level x record kind x verb, and class semantics with no grant.

userA holds a broad role (every Full policy for the record modules) so the policy layer
never masks the record layer; the FGC on the record is the only variable. Grants are
made on the project (or inventory item) only; children must inherit.
"""

import pytest

from albert import Albert
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
from tests.acl.http import call
from tests.acl.world import World, grant, revoke

BROAD_POLICIES = [
    "ProjectsFullAccess",
    "FormulaFullAccess",
    "TasksFullAccess",
    "InventoryFullAccess",
    "NotesFullAccess",
    "ReportsFullAccess",
    "PricingFullAccess",
]

READ_PATH = {
    Kind.PROJECT: "/api/v3/projects/{}",
    Kind.FORMULA: "/api/v3/inventories/{}",
    Kind.GENERAL_TASK: "/api/v3/tasks/{}",
    Kind.BATCH_TASK: "/api/v3/tasks/{}",
    Kind.LOT: "/api/v3/lots/{}",
    Kind.TASK_CHILD: "/api/v3/notes/{}",
    Kind.PROJECT_CHILD: "/api/v3/notebooks/{}",
    Kind.INVENTORY: "/api/v3/inventories/{}",
    Kind.INVENTORY_CHILD: "/api/v3/notes/{}",
}

UPDATE_BODY = {
    Kind.PROJECT: lambda: {
        "data": [{"operation": "update", "attribute": "description", "newValue": "acl-edit"}]
    },
    Kind.TASK_CHILD: lambda: {
        "data": [{"operation": "update", "attribute": "note", "newValue": "acl-edit"}]
    },
    Kind.INVENTORY: lambda: {
        "data": [{"operation": "update", "attribute": "description", "newValue": "acl-edit"}]
    },
    Kind.LOT: lambda: {
        "data": [{"operation": "update", "attribute": "notes", "newValue": "acl-edit"}]
    },
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
        for kind in UPDATE_BODY:
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
            resp = call(broad_user, "PATCH", path, json=UPDATE_BODY[kind]())
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
    """Test that an inventory FGC grant on a private item yields the contracted read."""
    tree = world.inventories[AccessClass.PRIVATE]
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
    "cls", [AccessClass.SHARED, AccessClass.PRIVATE, AccessClass.CONFIDENTIAL]
)
@pytest.mark.parametrize("kind", [Kind.PROJECT, Kind.INVENTORY])
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


@pytest.mark.parametrize("kind", [Kind.PROJECT, Kind.INVENTORY])
def test_share_requires_full_policy_and_owner(request, admin, switcher, user_ids, world, kind):
    """Test that Edit-level policy plus owner FGC cannot share (SDK-216 decision)."""
    tree = (world.projects if kind is Kind.PROJECT else world.inventories)[AccessClass.PRIVATE]
    rid = tree.ids[kind]
    owner = "ProjectOwner" if kind is Kind.PROJECT else "InventoryOwner"
    edit_policy = "ProjectsEditAccess" if kind is Kind.PROJECT else "InventoryEditAccess"
    user = switcher.use(edit_policy, [edit_policy])
    grant(admin, rid, user_ids["userA"], owner)
    try:
        resp = call(
            user,
            "PATCH",
            f"/api/v3/acl/{rid}",
            json={
                "data": [
                    {
                        "operation": "add",
                        "attribute": "ACL",
                        "newValue": [{"id": user_ids["userB"], "fgc": owner}],
                    }
                ]
            },
        )
        check(
            request,
            scenario="share",
            subject=f"{edit_policy}+{owner}",
            action=f"{kind.value}.share",
            expect=Expect.DENY,
            resp=resp,
        )
    finally:
        revoke(admin, rid, user_ids["userB"])
        revoke(admin, rid, user_ids["userA"])
