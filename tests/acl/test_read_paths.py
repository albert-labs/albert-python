"""Every read path tested separately: get_by_id, list, bulk ids, search GET/POST, suggest,
llmsearch. Document search runs on long-lived projects in ``test_document_search.py``.

For each record class and path, userB (no ACL entry, fixed baseline role) must see the
canary exactly when the class contract says so. Index-backed paths are polled until the
admin sees the canary, so index lag is never reported as a denial.
"""

import pytest

from tests.acl.actions import DIRECT, READ_PATHS
from tests.acl.checks import admin_control, check
from tests.acl.contract.fgc import AccessClass, Kind, ReadPath, class_expect
from tests.acl.contract.model import Expect, Verb
from tests.acl.http import Response, call, call_all_pages
from tests.acl.world import INVENTORY_CLASSES, PROJECT_CLASSES
from tests.utils.wait import poll_until


def _cases():
    for kind in (Kind.PROJECT, Kind.BATCH_TASK, Kind.INVENTORY):
        classes = INVENTORY_CLASSES if kind is Kind.INVENTORY else PROJECT_CLASSES
        for path in READ_PATHS[kind]:
            for cls in classes:
                yield pytest.param(kind, path, cls, id=f"{kind.value}-{path.value}-{cls.value}")


def _tree(world, kind, cls):
    return (world.inventories if kind is Kind.INVENTORY else world.projects)[cls]


def _check_visibility(request, admin, user, tree, kind, path, *, scenario, expect):
    rid, canary = tree.ids[kind], tree.canary
    method, url, kwargs = READ_PATHS[kind][path](rid, canary, tree.ids)
    token = rid if path in DIRECT else canary

    def fetch(client):
        if path is ReadPath.LIST:
            return call_all_pages(client, method, url, token=token, **kwargs)
        return call(client, method, url, **kwargs)

    def admin_sees():
        r = fetch(admin)
        return [r] if 200 <= r.status < 300 and r.contains(token) else []

    if not poll_until(admin_sees, timeout=60, interval=5):
        pytest.fail(
            f"harness error: admin never saw {token} via {path.value}; path may not index "
            "this field",
            pytrace=False,
        )
    check(
        request,
        scenario=scenario,
        subject=f"class={tree.access_class.value}",
        action=f"{kind.value}.{path.value}",
        expect=expect,
        resp=fetch(user),
        canary=token,
    )


@pytest.mark.parametrize(("kind", "path", "cls"), list(_cases()))
def test_read_path_visibility(request, admin, user_b, world, kind, path, cls):
    """Test that a read path exposes a record to a no-grant user only as the class allows."""
    _check_visibility(
        request,
        admin,
        user_b,
        _tree(world, kind, cls),
        kind,
        path,
        scenario="read_path",
        expect=class_expect(cls, Verb.READ, path),
    )


@pytest.mark.parametrize("path", list(READ_PATHS[Kind.FORMULA]), ids=lambda p: p.value)
@pytest.mark.parametrize(
    "cls", [AccessClass.PRIVATE, AccessClass.CONFIDENTIAL], ids=lambda c: c.value
)
def test_hidden_project_formula_on_inventory_paths(request, admin, user_b, world, cls, path):
    """Test that a no-grant user sees a hidden project's formula on inventory read paths only
    as the project's class allows: a private formula may be listed but not read by id, a
    confidential one never surfaces (PLSV-827; formulas inherit project ACL, PLSV-780 §4)."""
    _check_visibility(
        request,
        admin,
        user_b,
        world.projects[cls],
        Kind.FORMULA,
        path,
        scenario="PLSV-827:formula_inventory_paths",
        expect=class_expect(cls, Verb.READ, path),
    )


def test_bulk_ids_mixed_visibility(request, user_b, world):
    """Test that a bulk inventory id fetch mixing visible and confidential ids returns only
    the visible ones. Projects have no bulk-id read."""
    shared = world.inventories[AccessClass.SHARED].ids[Kind.INVENTORY]
    secret = world.inventories[AccessClass.CONFIDENTIAL].ids[Kind.INVENTORY]
    resp = call(user_b, "GET", "/api/v3/inventories/ids", params={"id": [shared, secret]})
    check(
        request,
        scenario="mixed_bulk",
        subject="class=confidential",
        action="inventory.bulk_mixed",
        expect=Expect.DENY,
        resp=resp,
        canary=secret,
    )


@pytest.mark.parametrize(
    "cls", [AccessClass.PRIVATE, AccessClass.CONFIDENTIAL], ids=lambda c: c.value
)
def test_worksheet_denied_without_grant(request, admin, user_b, world, cls):
    """Test that a no-grant user cannot read a hidden project's worksheet or expand its
    formula's ingredients (DE-2314)."""
    tree = world.projects[cls]
    pid, fid = tree.ids[Kind.PROJECT], tree.ids[Kind.FORMULA]
    destination = world.projects[AccessClass.SHARED].ids[Kind.PROJECT]
    admin_control(
        call(admin, "GET", "/api/v3/worksheet", params={"type": "project", "id": pid}),
        f"worksheet[{cls.value}].read",
    )
    check(
        request,
        scenario="DE-2314:worksheet",
        subject="no-grant",
        action=f"worksheet[{cls.value}].read",
        expect=Expect.DENY,
        resp=call(user_b, "GET", "/api/v3/worksheet", params={"type": "project", "id": pid}),
        canary=tree.canary,
    )
    admin_control(
        call(
            admin,
            "POST",
            f"/api/v3/worksheet/project/{pid}/formula/{fid}/expansion",
            params={"destination": destination},
            json={},
        ),
        f"worksheet[{cls.value}].expand",
    )
    check(
        request,
        scenario="DE-2314:worksheet",
        subject="no-grant",
        action=f"worksheet[{cls.value}].expand",
        expect=Expect.DENY,
        resp=call(
            user_b,
            "POST",
            f"/api/v3/worksheet/project/{pid}/formula/{fid}/expansion",
            params={"destination": destination},
            json={},
        ),
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
