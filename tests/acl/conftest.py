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
    """Preflight: resolve userA/userB ids and confirm they are distinct standard users.

    The admin token is trusted as-is: dev tokens and API keys do not resolve to a user.
    """
    ids = {}
    for name in ("userA", "userB"):
        info = whoami(identities[name].client())
        uid = info.get("userId") or info.get("albertId")
        if not uid:
            raise AclSetupError(f"{name}: validatejwt returned no userId")
        ids[name] = uid
    if ids["userA"] == ids["userB"]:
        raise AclSetupError(f"userA and userB must be different users, both are {ids['userA']}")
    for name in ("userA", "userB"):
        got = (user_record(admin, ids[name]).get("userClass") or "").lower()
        if got != "standard":
            raise AclSetupError(f"{name} must have userClass=standard, has {got!r}")
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
