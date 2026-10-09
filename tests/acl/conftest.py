"""Fixtures for the live ACL suite. See ``tests/acl/TESTING.md``.

All tests run in one xdist group: role swaps on userA are global state.
"""

from collections.abc import Iterator

import pytest

from albert import Albert
from tests.acl.identities import (
    AclSetupError,
    Identity,
    RoleSwitcher,
    base_url,
    load_identity,
    user_record,
    whoami,
)
from tests.acl.world import World, build_world, teardown


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        item.add_marker(pytest.mark.xdist_group("acl"))


@pytest.fixture(scope="session")
def acl_url() -> str:
    return base_url()


@pytest.fixture(scope="session")
def identities(acl_url: str) -> dict[str, Identity]:
    return {name: load_identity(name, acl_url) for name in ("admin", "userA", "userB")}


@pytest.fixture(scope="session")
def admin(identities: dict[str, Identity]) -> Albert:
    return identities["admin"].client()


@pytest.fixture(scope="session")
def user_ids(identities: dict[str, Identity], admin: Albert) -> dict[str, str]:
    """Preflight: resolve ids and confirm admin/standard user classes."""
    ids = {}
    for name, ident in identities.items():
        info = whoami(ident.client() if name != "admin" else admin)
        uid = info.get("userId") or info.get("albertId")
        if not uid:
            raise AclSetupError(f"{name}: validatejwt returned no userId")
        ids[name] = uid
    if len(set(ids.values())) != 3:
        raise AclSetupError(f"identities must be three distinct users, got {ids}")
    for name, want in (("admin", "admin"), ("userA", "standard"), ("userB", "standard")):
        got = (user_record(admin, ids[name]).get("userClass") or "").lower()
        if got != want:
            raise AclSetupError(f"{name} must have userClass={want}, has {got!r}")
    return ids


@pytest.fixture(scope="session")
def switcher(
    identities: dict[str, Identity], admin: Albert, user_ids: dict[str, str]
) -> Iterator[RoleSwitcher]:
    sw = RoleSwitcher(admin, identities["userA"], user_ids["userA"])
    yield sw
    sw.restore()


@pytest.fixture(scope="session")
def user_b(identities: dict[str, Identity], user_ids: dict[str, str]) -> Albert:
    return identities["userB"].client()


@pytest.fixture(scope="session")
def world(admin: Albert, user_ids: dict[str, str]) -> Iterator[World]:
    w = build_world(admin)
    yield w
    teardown(admin, w)
