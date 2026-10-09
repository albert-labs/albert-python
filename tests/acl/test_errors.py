"""Denials are clean, always-on actions stay on, and nothing answers with a 5xx.

- A role with zero policies must still perform every always-on action.
- Actions that are not always-on must be denied to a zero-policy role.
- Denials must be 403/404 (never 5xx), including unregistered operations and unknown
  categories.
"""

import pytest

from tests.acl.checks import admin_control, check
from tests.acl.contract.always_on import ALWAYS_ON, NOT_ALWAYS_ON
from tests.acl.contract.fgc import AccessClass, Kind
from tests.acl.contract.model import Expect
from tests.acl.http import call
from tests.acl.report import Row, record

UNREGISTERED = [
    ("GET", "/api/v3/static/standardorganizations"),
    ("GET", "/api/v3/static/hazardsymbols"),
    ("GET", "/api/v3/static/systemsettings"),
    ("GET", "/api/v3/static/languages"),
]


@pytest.fixture(scope="module")
def empty_user(switcher):
    return switcher.use("no-policies", [])


@pytest.mark.parametrize("probe", ALWAYS_ON, ids=lambda p: p.name)
def test_always_on(request, admin, empty_user, probe):
    """Test that a zero-policy role can perform an always-on action."""
    kwargs = {"params": probe.params} if probe.params else {}
    admin_control(call(admin, probe.method, probe.path, **kwargs), probe.name)
    check(
        request,
        scenario="always_on",
        subject="no-policies",
        action=probe.name,
        expect=Expect.ALLOW,
        resp=call(empty_user, probe.method, probe.path, **kwargs),
    )


@pytest.mark.parametrize("probe", NOT_ALWAYS_ON, ids=lambda p: p.name)
def test_not_always_on(request, admin, empty_user, probe):
    """Test that a zero-policy role is denied an action that needs a policy."""
    kwargs = {"params": probe.params} if probe.params else {}
    admin_control(call(admin, probe.method, probe.path, **kwargs), probe.name)
    check(
        request,
        scenario="not_always_on",
        subject="no-policies",
        action=probe.name,
        expect=Expect.DENY,
        resp=call(empty_user, probe.method, probe.path, **kwargs),
    )


@pytest.mark.parametrize(("method", "path"), UNREGISTERED, ids=lambda v: str(v))
def test_unregistered_operation_never_5xx(request, empty_user, method, path):
    """Test that an operation missing from the registry answers cleanly, never 5xx."""
    resp = call(empty_user, method, path)
    record(
        request,
        Row(
            "errors",
            "no-policies",
            f"{method} {path}",
            "no-5xx",
            resp.status,
            "server_error" if resp.status >= 500 else "pass",
        ),
    )
    assert resp.status < 500, f"{method} {path} returned {resp.status}"


def test_unknown_category_is_clean(empty_user):
    """Test that an unknown task category is a clean 4xx, never 5xx."""
    resp = call(empty_user, "GET", "/api/v3/tasks", params={"category": "NotARealCategory"})
    assert resp.status < 500, f"unknown category returned {resp.status}"


@pytest.mark.parametrize("kind", [Kind.PROJECT, Kind.GENERAL_TASK, Kind.INVENTORY])
def test_denial_is_clean(request, user_b, world, kind):
    """Test that reading a confidential record without a grant is 403/404, never 5xx."""
    tree = (world.inventories if kind is Kind.INVENTORY else world.projects)[
        AccessClass.CONFIDENTIAL
    ]
    base = {Kind.PROJECT: "projects", Kind.GENERAL_TASK: "tasks", Kind.INVENTORY: "inventories"}
    resp = call(user_b, "GET", f"/api/v3/{base[kind]}/{tree.ids[kind]}")
    check(
        request,
        scenario="errors",
        subject="no-grant",
        action=f"{kind.value}.denial_shape",
        expect=Expect.DENY,
        resp=resp,
    )
