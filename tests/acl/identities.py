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

import base64
import json
import os
from dataclasses import dataclass

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
    base_url: str

    @property
    def swappable(self) -> bool:
        return self.name in USER_ENV

    def client(self) -> Albert:
        """A fresh client, authenticated exactly as the dev permission tests do."""
        if self.name == "admin":
            return Albert.from_token(
                base_url=os.environ[BASE_URL_ENV],
                token=os.environ[ADMIN_TOKEN_ENV].strip(),
            )
        return Albert(auth_manager=self.credentials(), retries=0)

    def credentials(self) -> AlbertClientCredentials:
        client_id_env, client_secret_env = USER_ENV[self.name]
        creds = AlbertClientCredentials.from_env(
            base_url_env=BASE_URL_ENV,
            client_id_env=client_id_env,
            client_secret_env=client_secret_env,
        )
        if creds is None:
            raise AclSetupError(
                f"{BASE_URL_ENV}, {client_id_env}, {client_secret_env} must be set"
            )
        return creds


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
    required = [ADMIN_TOKEN_ENV] if name == "admin" else list(USER_ENV[name])
    missing = [env for env in required if not os.environ.get(env, "").strip()]
    if missing:
        raise AclSetupError(f"{', '.join(missing)} not set")
    return Identity(name, url)


def user_id(identity: Identity) -> str:
    """The ``USR...`` id from the claims of the identity's own access token.

    Claims are read without verification; the id is only used as an ACL principal.
    """
    token = identity.credentials().get_access_token()
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    for key in ("userId", "id", "albertId", "sub"):
        value = claims.get(key)
        if isinstance(value, str) and value.startswith("USR"):
            return value
    raise AclSetupError(f"no USR id in {identity.name}'s token claims {sorted(claims)}")


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
