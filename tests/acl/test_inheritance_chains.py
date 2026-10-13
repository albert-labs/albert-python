"""Inheritance chains: grants at the top flow down; no grant means nothing flows down.

Chains (seeded in ``world.py``):

- Project -> BatchTask -> Note / Attachment note / Notebook
- Project -> Notebook
- Project -> Formula -> Lot

General and property tasks are not in the chain: they follow the caller's Tasks policies,
not project access.
- Inventory (confidential) -> Lot / Pricing / Note

Patterns: top-only grant (children readable), no grant (every link denied, including
children reached by id), child-only grant under a private parent (child readable, parent
still denied), revoke at top (every child denied again).
"""

import pytest

from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import Response, call
from tests.acl.world import grant, revoke
from tests.utils.wait import poll_until

PROPAGATION_S = 90.0

PROJECT_CHAIN = {
    "project": ("/api/v3/projects/{}", lambda t: t.ids[Kind.PROJECT]),
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
    "PricingFullAccess",
]


@pytest.fixture(scope="module")
def chain_user(switcher):
    return switcher.use("broad-chains", CHAIN_POLICIES)


def _probe(request, admin, user, pattern, link, path, expect, owner="ProjectOwner", resp=None):
    admin_control(call(admin, "GET", path), link)
    check(
        request,
        scenario=f"chain:{pattern}",
        subject=owner if pattern != "no_grant" else "no-grant",
        action=link,
        expect=expect,
        resp=resp or call(user, "GET", path),
    )


def _wait_status(user, path, want_ok: bool) -> Response:
    return poll_until(
        lambda: [call(user, "GET", path)],
        predicate=lambda r: (200 <= r[0].status < 300) == want_ok,
        timeout=PROPAGATION_S,
        interval=3,
    )[0]


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
        path = tmpl.format(rid(tree))
        resp = _wait_status(chain_user, path, want_ok=True)
        _probe(request, admin, chain_user, "top_grant", link, path, Expect.ALLOW, resp=resp)
    finally:
        revoke(admin, pid, user_ids["userA"])


@pytest.mark.parametrize("link", [k for k in PROJECT_CHAIN if k != "project"])
def test_project_chain_revoke(request, admin, chain_user, user_ids, world, link):
    """Test that revoking the project grant removes access to every descendant."""
    tree = world.projects[AccessClass.PRIVATE]
    tmpl, rid = PROJECT_CHAIN[link]
    pid = tree.ids[Kind.PROJECT]
    path = tmpl.format(rid(tree))
    _probe(request, admin, chain_user, "revoked", f"{link}.before_grant", path, Expect.DENY)
    grant(admin, pid, user_ids["userA"], "ProjectOwner")
    try:
        _wait_status(chain_user, path, want_ok=True)
    finally:
        revoke(admin, pid, user_ids["userA"])
    resp = _wait_status(chain_user, path, want_ok=False)
    _probe(request, admin, chain_user, "revoked", link, path, Expect.DENY, resp=resp)


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
        path = tmpl.format(rid(tree))
        resp = _wait_status(chain_user, path, want_ok=True)
        _probe(
            request,
            admin,
            chain_user,
            "top_grant",
            link,
            path,
            Expect.ALLOW,
            owner="InventoryOwner",
            resp=resp,
        )
    finally:
        revoke(admin, inv, user_ids["userA"])


def test_child_only_grant_does_not_expose_parent(request, admin, chain_user, user_ids, world):
    """Test that a grant on a batch task inside a private project does not expose the project."""
    tree = world.projects[AccessClass.PRIVATE]
    tid = tree.ids[Kind.BATCH_TASK]
    grant(admin, tid, user_ids["userA"], "ProjectOwner")
    try:
        path = f"/api/v3/projects/{tree.ids[Kind.PROJECT]}"
        _probe(request, admin, chain_user, "child_only", "project", path, Expect.DENY)
    finally:
        revoke(admin, tid, user_ids["userA"])
