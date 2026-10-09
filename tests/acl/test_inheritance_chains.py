"""Inheritance chains: grants at the top flow down; no grant means nothing flows down.

Chains (seeded in ``world.py``):

- Project -> GeneralTask -> Note / Attachment note / Notebook
- Project -> Notebook
- Project -> Formula -> Lot
- Project -> BatchTask
- Inventory (private) -> Lot / Pricing / Note

Patterns: top-only grant (children readable), no grant (every link denied, including
children reached by id), child-only grant under a private parent (child readable, parent
still denied), revoke at top (every child denied again).
"""

import pytest

from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import call
from tests.acl.world import grant, revoke

PROJECT_CHAIN = {
    "project": ("/api/v3/projects/{}", lambda t: t.ids[Kind.PROJECT]),
    "general_task": ("/api/v3/tasks/{}", lambda t: t.ids[Kind.GENERAL_TASK]),
    "task_note": ("/api/v3/notes/{}", lambda t: t.ids[Kind.TASK_CHILD]),
    "task_attachment_note": ("/api/v3/notes/{}", lambda t: t.extra["task_attachment_note"]),
    "task_notebook": ("/api/v3/notebooks/{}", lambda t: t.extra["task_notebook"]),
    "project_notebook": ("/api/v3/notebooks/{}", lambda t: t.ids[Kind.PROJECT_CHILD]),
    "formula": ("/api/v3/inventories/{}", lambda t: t.ids[Kind.FORMULA]),
    "formula_lot": ("/api/v3/lots/{}", lambda t: t.ids[Kind.LOT]),
    "batch_task": ("/api/v3/tasks/{}", lambda t: t.ids[Kind.BATCH_TASK]),
}

INVENTORY_CHAIN = {
    "inventory": ("/api/v3/inventories/{}", lambda t: t.ids[Kind.INVENTORY]),
    "lot": ("/api/v3/lots/{}", lambda t: t.ids[Kind.LOT]),
    "pricing": ("/api/v3/pricings/{}", lambda t: t.extra["pricing"]),
    "note": ("/api/v3/notes/{}", lambda t: t.ids[Kind.INVENTORY_CHILD]),
}

CHAIN_POLICIES = [
    "ProjectsFullAccess",
    "FormulaFullAccess",
    "TasksFullAccess",
    "InventoryFullAccess",
    "NotesFullAccess",
    "PricingFullAccess",
]


@pytest.fixture(scope="module")
def chain_user(switcher):
    return switcher.use("broad-chains", CHAIN_POLICIES)


def _probe(request, admin, user, pattern, link, path, expect):
    admin_control(call(admin, "GET", path), link)
    check(
        request,
        scenario=f"chain:{pattern}",
        subject="ProjectOwner" if pattern != "no_grant" else "no-grant",
        action=link,
        expect=expect,
        resp=call(user, "GET", path),
    )


@pytest.mark.parametrize("link", list(PROJECT_CHAIN))
@pytest.mark.parametrize("cls", [AccessClass.PRIVATE, AccessClass.CONFIDENTIAL])
def test_project_chain_no_grant(request, admin, chain_user, world, cls, link):
    """Test that without a project grant no link of a private/confidential chain is readable."""
    tree = world.projects[cls]
    tmpl, rid = PROJECT_CHAIN[link]
    _probe(request, admin, chain_user, "no_grant", link, tmpl.format(rid(tree)), Expect.DENY)


@pytest.mark.parametrize("link", list(PROJECT_CHAIN))
def test_project_chain_top_grant(request, admin, chain_user, user_ids, world, link):
    """Test that a ProjectOwner grant on the project alone makes every descendant readable."""
    tree = world.projects[AccessClass.PRIVATE]
    tmpl, rid = PROJECT_CHAIN[link]
    pid = tree.ids[Kind.PROJECT]
    grant(admin, pid, user_ids["userA"], "ProjectOwner")
    try:
        _probe(request, admin, chain_user, "top_grant", link, tmpl.format(rid(tree)), Expect.ALLOW)
    finally:
        revoke(admin, pid, user_ids["userA"])


@pytest.mark.parametrize("link", [k for k in PROJECT_CHAIN if k != "project"])
def test_project_chain_revoke(request, admin, chain_user, user_ids, world, link):
    """Test that revoking the project grant removes access to every descendant."""
    tree = world.projects[AccessClass.PRIVATE]
    tmpl, rid = PROJECT_CHAIN[link]
    pid = tree.ids[Kind.PROJECT]
    grant(admin, pid, user_ids["userA"], "ProjectOwner")
    revoke(admin, pid, user_ids["userA"])
    _probe(request, admin, chain_user, "revoked", link, tmpl.format(rid(tree)), Expect.DENY)


@pytest.mark.parametrize("link", list(INVENTORY_CHAIN))
def test_inventory_chain_no_grant(request, admin, chain_user, world, link):
    """Test that without a grant no child of a confidential inventory item is readable."""
    tree = world.inventories[AccessClass.CONFIDENTIAL]
    tmpl, rid = INVENTORY_CHAIN[link]
    _probe(request, admin, chain_user, "no_grant", link, tmpl.format(rid(tree)), Expect.DENY)


@pytest.mark.parametrize("link", list(INVENTORY_CHAIN))
def test_inventory_chain_top_grant(request, admin, chain_user, user_ids, world, link):
    """Test that an InventoryOwner grant on the item makes its lots, pricing and notes readable."""
    tree = world.inventories[AccessClass.CONFIDENTIAL]
    tmpl, rid = INVENTORY_CHAIN[link]
    inv = tree.ids[Kind.INVENTORY]
    grant(admin, inv, user_ids["userA"], "InventoryOwner")
    try:
        _probe(request, admin, chain_user, "top_grant", link, tmpl.format(rid(tree)), Expect.ALLOW)
    finally:
        revoke(admin, inv, user_ids["userA"])


def test_child_only_grant_does_not_expose_parent(request, admin, chain_user, user_ids, world):
    """Test that a grant on a task inside a private project does not expose the project."""
    tree = world.projects[AccessClass.PRIVATE]
    tid = tree.ids[Kind.GENERAL_TASK]
    grant(admin, tid, user_ids["userA"], "ProjectOwner")
    try:
        path = f"/api/v3/projects/{tree.ids[Kind.PROJECT]}"
        _probe(request, admin, chain_user, "child_only", "project", path, Expect.DENY)
    finally:
        revoke(admin, tid, user_ids["userA"])


def test_wrong_parent_id_does_not_unlock_child(request, admin, chain_user, user_ids, world):
    """Test that passing a parentId the user can see does not unlock another project's child."""
    visible = world.projects[AccessClass.SHARED].ids[Kind.PROJECT]
    hidden = world.projects[AccessClass.CONFIDENTIAL]
    resp = call(
        chain_user,
        "GET",
        f"/api/v3/notebooks/{hidden.ids[Kind.PROJECT_CHILD]}",
        params={"parentId": visible},
    )
    check(
        request,
        scenario="chain:wrong_parent",
        subject="no-grant",
        action="project_notebook",
        expect=Expect.DENY,
        resp=resp,
    )
