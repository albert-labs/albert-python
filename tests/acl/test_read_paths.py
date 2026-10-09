"""Every read path tested separately: get_by_id, list, bulk ids, search GET/POST, suggest,
document search, llmsearch.

For each record class and path, userB (no ACL entry, fixed baseline role) must see the
canary exactly when the class contract says so. Index-backed paths are polled until the
admin sees the canary, so index lag is never reported as a denial.
"""

import pytest

from tests.acl.actions import DIRECT, READ_PATHS
from tests.acl.checks import check
from tests.acl.contract.fgc import PRIVATE_LIST_UNDECIDED, AccessClass, Kind, class_expect
from tests.acl.contract.model import Expect, Verb
from tests.acl.http import Response, call
from tests.utils.wait import poll_until

CLASSES = [AccessClass.SHARED, AccessClass.PRIVATE, AccessClass.CONFIDENTIAL]


def _cases():
    for kind in (Kind.PROJECT, Kind.GENERAL_TASK, Kind.INVENTORY):
        for path in READ_PATHS[kind]:
            for cls in CLASSES:
                yield pytest.param(kind, path, cls, id=f"{kind.value}-{path.value}-{cls.value}")


def _tree(world, kind, cls):
    return (world.inventories if kind is Kind.INVENTORY else world.projects)[cls]


@pytest.mark.parametrize(("kind", "path", "cls"), list(_cases()))
def test_read_path_visibility(request, admin, user_b, world, kind, path, cls):
    """Test that a read path exposes a record to a no-grant user only as the class allows."""
    tree = _tree(world, kind, cls)
    rid, canary = tree.ids[kind], tree.canary
    method, url, kwargs = READ_PATHS[kind][path](rid, canary)
    token = rid if path in DIRECT else canary

    def admin_sees():
        r = call(admin, method, url, **kwargs)
        return [r] if 200 <= r.status < 300 and r.contains(token) else []

    if not poll_until(admin_sees, timeout=60, interval=3):
        pytest.fail(
            f"harness error: admin never saw {token} via {path.value}; path may not index "
            "this field",
            pytrace=False,
        )
    expect = class_expect(cls, Verb.READ, path)
    check(
        request,
        scenario="read_path",
        subject=f"class={cls.value}",
        action=f"{kind.value}.{path.value}",
        expect=expect,
        resp=call(user_b, method, url, **kwargs),
        canary=token,
        detail=PRIVATE_LIST_UNDECIDED if expect is Expect.UNDECIDED else "",
    )


@pytest.mark.parametrize("kind", [Kind.PROJECT, Kind.INVENTORY])
def test_bulk_ids_mixed_visibility(request, admin, user_b, world, kind):
    """Test that a bulk id fetch mixing visible and confidential ids returns only visible ones."""
    shared = _tree(world, kind, AccessClass.SHARED).ids[kind]
    secret_tree = _tree(world, kind, AccessClass.CONFIDENTIAL)
    secret = secret_tree.ids[kind]
    if kind is Kind.PROJECT:
        url, params = "/api/v3/projects", {"projectId": [shared, secret]}
    else:
        url, params = "/api/v3/inventories/ids", {"id": [shared, secret]}
    resp = call(user_b, "GET", url, params=params)
    check(
        request,
        scenario="mixed_bulk",
        subject="class=confidential",
        action=f"{kind.value}.bulk_mixed",
        expect=Expect.DENY,
        resp=resp,
        canary=secret,
    )


def test_list_total_excludes_hidden(request, user_b, world):
    """Test that a search total for a confidential-only canary is zero for a no-grant user."""
    tree = world.projects[AccessClass.CONFIDENTIAL]
    resp = call(user_b, "GET", "/api/v3/projects/search", params={"text": tree.canary})
    body = resp.body if isinstance(resp.body, dict) else {}
    total = int(body.get("total") or body.get("Total") or 0)
    check(
        request,
        scenario="pagination_total",
        subject="class=confidential",
        action="project.search_total",
        expect=Expect.DENY,
        resp=Response(resp.status, {"total": total, "canary": tree.canary if total else None}),
        canary=tree.canary,
    )
