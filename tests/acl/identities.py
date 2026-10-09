"""Test identities and single-policy role swapping.

Env (``client_id:client_secret`` each; a raw token is accepted with ``token:<jwt>`` but
cannot be role-swapped):

- ``ALBERT_ACL_ADMIN_TEST``: tenant admin; seeds data, swaps roles, positive control.
- ``ALBERT_ACL_USERA_TEST``: standard user whose role is swapped per scenario.
- ``ALBERT_ACL_USERB_TEST``: standard user with a fixed baseline role (never swapped).
- ``ALBERT_BASE_URL``: shared base URL.

Roles named ``SDK-ACL-<label>`` are created once and reused; their policy sets are never
mutated after creation, so a cached role cannot carry stale grants.
"""

import os
from dataclasses import dataclass

from albert import Albert, AlbertClientCredentials
from tests.acl.http import call

ROLE_PREFIX = "SDK-ACL-"
PROD_MARKERS = ("app.albertinvent.com", "albertinvent.com/")
ENV = {
    "admin": "ALBERT_ACL_ADMIN_TEST",
    "userA": "ALBERT_ACL_USERA_TEST",
    "userB": "ALBERT_ACL_USERB_TEST",
}


class AclSetupError(RuntimeError):
    """The harness, not the backend, is wrong: never reported as a finding."""


@dataclass(frozen=True)
class Identity:
    name: str
    client_id: str | None
    secret: str | None
    token: str | None
    base_url: str

    @property
    def swappable(self) -> bool:
        return self.client_id is not None

    def client(self) -> Albert:
        if self.token:
            return Albert(token=self.token, base_url=self.base_url, retries=0)
        creds = AlbertClientCredentials(
            id=self.client_id, secret=self.secret, base_url=self.base_url
        )
        return Albert(auth_manager=creds, retries=0)


def base_url() -> str:
    url = os.environ.get("ALBERT_BASE_URL")
    if not url:
        raise AclSetupError("ALBERT_BASE_URL is not set")
    is_prod = any(m in url for m in PROD_MARKERS) and not any(
        env in url for env in ("dev", "staging", "qa", "sandbox")
    )
    if is_prod and os.environ.get("ALBERT_ACL_ALLOW_PROD") != "1":
        raise AclSetupError(
            f"refusing to run ACL suite against {url}; set ALBERT_ACL_ALLOW_PROD=1"
        )
    return url


def load_identity(name: str, url: str) -> Identity:
    raw = os.environ.get(ENV[name])
    if not raw:
        raise AclSetupError(f"{ENV[name]} is not set")
    if raw.startswith("token:"):
        return Identity(name, None, None, raw.removeprefix("token:"), url)
    client_id, sep, secret = raw.partition(":")
    if not sep or not client_id or not secret:
        raise AclSetupError(f"{ENV[name]} must be client_id:client_secret")
    return Identity(name, client_id, secret, None, url)


def whoami(client: Albert) -> dict:
    resp = call(client, "GET", "/api/v3/login/validatejwt", params={"includeUserDetails": "true"})
    if resp.status != 200 or not isinstance(resp.body, dict):
        raise AclSetupError(f"validatejwt failed: {resp.status}")
    return resp.body


def user_record(admin: Albert, user_id: str) -> dict:
    resp = call(admin, "GET", f"/api/v3/users/{user_id}")
    if resp.status != 200:
        raise AclSetupError(f"cannot read user {user_id}: {resp.status}")
    return resp.body


def current_role_id(admin: Albert, user_id: str) -> str | None:
    roles = user_record(admin, user_id).get("Roles") or []
    return roles[0].get("id") if roles else None


class RoleSwitcher:
    """Assign stable single-purpose roles to userA and restore the original at teardown."""

    def __init__(self, admin: Albert, identity: Identity, user_id: str):
        if not identity.swappable:
            raise AclSetupError(f"{identity.name} uses a raw token and cannot be role-swapped")
        self.admin = admin
        self.identity = identity
        self.user_id = user_id
        self.original_role = current_role_id(admin, user_id)
        self._current = self.original_role
        self._roles: dict[str, str] = {}

    def ensure_role(self, label: str, policy_ids: list[str]) -> str:
        name = f"{ROLE_PREFIX}{label}"
        if name in self._roles:
            return self._roles[name]
        listing = call(self.admin, "GET", "/api/v3/acl/roles")
        for role in listing.items():
            if role.get("name") == name:
                have = sorted(p.get("id") for p in role.get("Policies") or [])
                if have != sorted(policy_ids):
                    raise AclSetupError(
                        f"role {name} exists with policies {have}, expected {sorted(policy_ids)}"
                    )
                self._roles[name] = role["albertId"]
                return role["albertId"]
        created = call(
            self.admin,
            "POST",
            "/api/v3/acl/roles",
            json={
                "name": name,
                "description": f"SDK ACL test role: {label}",
                "Policies": [{"id": p} for p in policy_ids],
            },
        )
        if created.status not in (200, 201):
            raise AclSetupError(f"cannot create role {name}: {created.status} {created.body}")
        self._roles[name] = created.body["albertId"]
        return self._roles[name]

    def assign(self, role_id: str | None) -> Albert:
        """Give userA ``role_id`` and return a freshly authenticated client."""
        if role_id != self._current:
            if role_id is None:
                op = {"operation": "delete", "attribute": "role", "oldValue": self._current}
            elif self._current is None:
                op = {"operation": "add", "attribute": "role", "newValue": role_id}
            else:
                op = {
                    "operation": "update",
                    "attribute": "role",
                    "oldValue": self._current,
                    "newValue": role_id,
                }
            resp = call(self.admin, "PATCH", f"/api/v3/users/{self.user_id}", json={"data": [op]})
            if resp.status >= 300:
                raise AclSetupError(f"role assign failed: {resp.status} {resp.body}")
            self._current = role_id
        return self.identity.client()

    def use(self, label: str, policy_ids: list[str]) -> Albert:
        return self.assign(self.ensure_role(label, policy_ids))

    def restore(self) -> None:
        self.assign(self.original_role)
