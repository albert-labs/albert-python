"""Role matrix: each single-policy role x module action (in-module and out-of-module).

userA is given a role holding exactly one policy; every module action is then probed.
The expected outcome is the policy contract (``contract/policies.py``) — never the
policy's operation list. Admin runs each action first as the positive control.

Destructive actions (update/delete) target a throwaway record admin creates per check,
so a leak never damages shared seeds.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from albert import Albert
from tests.acl.checks import admin_control, check
from tests.acl.contract.model import Module, Verb
from tests.acl.contract.policies import POLICIES
from tests.acl.http import Response, call

M, V = Module, Verb


def _uid() -> str:
    return uuid.uuid4().hex[:10]


@dataclass(frozen=True)
class ModuleOps:
    """Raw-HTTP CRUD for one module. ``make`` returns the create body."""

    base: str
    make: Callable[[], dict | list]
    patch: Callable[[dict], dict | list]
    id_key: str = "albertId"
    list_params: dict | None = None

    def created_id(self, resp: Response) -> str | None:
        body = resp.body[0] if isinstance(resp.body, list) and resp.body else resp.body
        return body.get(self.id_key) if isinstance(body, dict) else None


def _op(attr: str, old, new) -> dict:
    return {"data": [{"operation": "update", "attribute": attr, "oldValue": old, "newValue": new}]}


MODULES: dict[Module, ModuleOps] = {
    M.CAS: ModuleOps(
        "/api/v3/cas",
        lambda: {"number": f"{uuid.uuid4().int % 10**7}-{_uid()[:2]}-0", "description": "acl"},
        lambda rec: _op("description", rec.get("description"), f"acl {_uid()}"),
    ),
    M.UNITS: ModuleOps(
        "/api/v3/units",
        lambda: {"name": f"acl-unit-{_uid()}", "symbol": _uid()[:4]},
        lambda rec: _op("symbol", rec.get("symbol"), _uid()[:4]),
    ),
    M.LOCATIONS: ModuleOps(
        "/api/v3/locations",
        lambda: {
            "name": f"acl-loc-{_uid()}",
            "latitude": 1.0,
            "longitude": 1.0,
            "address": "acl",
        },
        lambda rec: _op("address", rec.get("address"), f"acl {_uid()}"),
    ),
    M.LISTS: ModuleOps(
        "/api/v3/lists",
        lambda: {"name": f"acl-list-{_uid()}", "category": "userDefined", "listType": "acl"},
        lambda rec: _op("name", rec.get("name"), f"acl-list-{_uid()}"),
    ),
    M.TEAMS: ModuleOps(
        "/api/v3/teams",
        lambda: {"name": f"acl-team-{_uid()}"},
        lambda rec: _op("name", rec.get("name"), f"acl-team-{_uid()}"),
    ),
    M.PARAMETER_GROUPS: ModuleOps(
        "/api/v3/parametergroups",
        lambda: {"name": f"acl-pg-{_uid()}", "type": "general"},
        lambda rec: _op("name", rec.get("name"), f"acl-pg-{_uid()}"),
    ),
    M.DATA_TEMPLATES: ModuleOps(
        "/api/v3/datatemplates",
        lambda: {"name": f"acl-dt-{_uid()}"},
        lambda rec: _op("name", rec.get("name"), f"acl-dt-{_uid()}"),
    ),
    M.PROJECTS: ModuleOps(
        "/api/v3/projects",
        lambda: {"description": f"acl-proj-{_uid()}", "class": "shared"},
        lambda rec: _op("description", rec.get("description"), f"acl-proj-{_uid()}"),
    ),
    M.INVENTORY: ModuleOps(
        "/api/v3/inventories",
        lambda: {
            "name": f"acl-inv-{_uid()}",
            "category": "RawMaterials",
            "unitCategory": "mass",
            "class": "shared",
        },
        lambda rec: _op("description", rec.get("description"), f"acl {_uid()}"),
    ),
    M.TASKS: ModuleOps(
        "/api/v3/tasks",
        lambda: [{"name": f"acl-task-{_uid()}", "category": "General"}],
        lambda rec: [
            {
                "id": rec.get("albertId"),
                "data": [
                    {
                        "operation": "update",
                        "attribute": "name",
                        "oldValue": rec.get("name"),
                        "newValue": f"acl-task-{_uid()}",
                    }
                ],
            }
        ],
    ),
}


def _cases():
    for policy in POLICIES:
        if policy.optional:
            continue
        for module in MODULES:
            for verb in (V.READ, V.CREATE, V.UPDATE, V.DELETE):
                yield pytest.param(
                    policy, module, verb, id=f"{policy.id}-{module.value}-{verb.value}"
                )


def _create(client: Albert, ops: ModuleOps) -> Response:
    return call(client, "POST", ops.base, json=ops.make())


def _cleanup(admin: Albert, ops: ModuleOps, rid: str | None) -> None:
    if rid:
        call(admin, "DELETE", f"{ops.base}/{rid}")


@pytest.mark.parametrize(("policy", "module", "verb"), list(_cases()))
def test_role_matrix(request, admin: Albert, switcher, policy, module: Module, verb: Verb):
    """Test that a single-policy role is allowed exactly what its description grants."""
    ops = MODULES[module]
    expect = policy.expect(module, verb)
    user = switcher.use(policy.id, [policy.id])
    action = f"{module.value}.{verb.value}"

    if verb is V.READ:
        admin_control(call(admin, "GET", ops.base, params=ops.list_params or {"limit": 5}), action)
        resp = call(user, "GET", ops.base, params=ops.list_params or {"limit": 5})
        check(
            request,
            scenario="role_matrix",
            subject=policy.id,
            action=action,
            expect=expect,
            resp=resp,
        )
        return

    if verb is V.CREATE:
        resp = _create(user, ops)
        try:
            if not 200 <= resp.status < 300:
                probe = _create(admin, ops)
                admin_control(probe, action)
                _cleanup(admin, ops, ops.created_id(probe))
            check(
                request,
                scenario="role_matrix",
                subject=policy.id,
                action=action,
                expect=expect,
                resp=resp,
            )
        finally:
            _cleanup(admin, ops, ops.created_id(resp))
        return

    seed = _create(admin, ops)
    admin_control(seed, f"{module.value}.seed")
    rid = ops.created_id(seed)
    try:
        record = call(admin, "GET", f"{ops.base}/{rid}").body or {}
        path = f"{ops.base}/{rid}"
        if verb is V.UPDATE:
            resp = call(user, "PATCH", path, json=ops.patch(record))
            if not 200 <= resp.status < 300:
                admin_control(call(admin, "PATCH", path, json=ops.patch(record)), action)
        else:
            resp = call(user, "DELETE", path)
        check(
            request,
            scenario="role_matrix",
            subject=policy.id,
            action=action,
            expect=expect,
            resp=resp,
        )
    finally:
        _cleanup(admin, ops, rid)
