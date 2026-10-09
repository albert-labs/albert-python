"""Test identities and single-policy role swapping.

Env (same names as the dev permission tests):

- ``ALBERT_BASE_URL_DEV``: shared base URL.
- ``ALBERT_ADMIN_CLIENT_SECRET_DEV``: admin bearer token (JWT). Seeds data, swaps roles,
  positive control.
- ``ALBERT_USER_A_CLIENT_ID_DEV`` / ``ALBERT_USER_A_CLIENT_SECRET_DEV``: standard user
  whose role is swapped per scenario.
- ``ALBERT_USER_B_CLIENT_ID_DEV`` / ``ALBERT_USER_B_CLIENT_SECRET_DEV``: standard user
  with a fixed baseline role (never swapped).

Roles named ``SDK-ACL-<label>`` are created once and reused; their policy sets are never
mutated after creation, so a cached role cannot carry stale grants.
"""

import os
from dataclasses import dataclass, field

from albert import Albert, AlbertClientCredentials
from tests.acl.http import call

ROLE_PREFIX = "SDK-ACL-"
PROD_MARKERS = ("app.albertinvent.com", "albertinvent.com/")
BASE_URL_ENV = "ALBERT_BASE_URL_DEV"
ADMIN_TOKEN_ENV = "ALBERT_ADMIN_CLIENT_SECRET_DEV"
USER_ENV = {
    "userA": ("ALBERT_USER_A_CLIENT_ID_DEV", "ALBERT_USER_A_CLIENT_SECRET_DEV"),
    "userB": ("ALBERT_USER_B_CLIENT_ID_DEV", "ALBERT_USER_B_CLIENT_SECRET_DEV"),
}


class AclSetupError(RuntimeError):
    """The harness, not the backend, is wrong: never reported as a finding."""


@dataclass(frozen=True)
class Identity:
    name: str
    client_id: str | None
    secret: str | None = field(repr=False)
    token: str | None = field(repr=False)
    base_url: str

    @property
    def swappable(self) -> bool:
        return self.client_id is not None

    def client(self) -> Albert:
        if self.token:
            return Albert.from_token(base_url=self.base_url, token=self.token)
        creds = AlbertClientCredentials(
            id=self.client_id, secret=self.secret, base_url=self.base_url
        )
        return Albert(auth_manager=creds, retries=0)


def base_url() -> str:
    url = os.environ.get(BASE_URL_ENV)
    if not url:
        raise AclSetupError(f"{BASE_URL_ENV} is not set")
    is_prod = any(m in url for m in PROD_MARKERS) and not any(
        env in url for env in ("dev", "staging", "qa", "sandbox")
    )
    if is_prod and os.environ.get("ALBERT_ACL_ALLOW_PROD") != "1":
        raise AclSetupError(
            f"refusing to run ACL suite against {url}; set ALBERT_ACL_ALLOW_PROD=1"
        )
    return url


def load_identity(name: str, url: str) -> Identity:
    if name == "admin":
        token = (os.environ.get(ADMIN_TOKEN_ENV) or "").strip()
        if not token:
            raise AclSetupError(f"{ADMIN_TOKEN_ENV} is not set")
        return Identity(name, None, None, token, url)
    id_env, secret_env = USER_ENV[name]
    client_id, secret = os.environ.get(id_env), os.environ.get(secret_env)
    if not client_id or not secret:
        raise AclSetupError(f"{id_env} and {secret_env} must be set")
    return Identity(name, client_id.strip(), secret.strip(), None, url)


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
