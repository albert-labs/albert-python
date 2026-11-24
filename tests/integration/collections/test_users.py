from collections.abc import Iterator

import pytest

from albert import Albert
from albert.core.shared.enums import Status
from albert.exceptions import NotFoundError
from albert.resources.users import User, UserSearchItem
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("users")


def assert_user_items(
    users: Iterator[User | UserSearchItem],
    expected_type: type,
):
    """Assert all items are of expected types."""
    for item in users:
        assert isinstance(item, expected_type)
        assert isinstance(item.name, str)
        assert isinstance(item.id, str)
        assert item.id.startswith("USR")


def test_simple_users_get_all(client: Albert):
    user_list = list(client.users.get_all(max_items=10))
    assert_user_items(user_list, User)


def test_advanced_users_search(client: Albert, static_user: User):
    faux_name = static_user.name.split(" ")[0]
    adv_list = poll_until(
        lambda: [
            user
            for user in client.users.search(
                text=faux_name,
                status=[Status.ACTIVE],
                user_id=[static_user.id],
                search_fields=["name"],
                max_items=20,
            )
            if user.id == static_user.id
        ]
    )
    found = any(static_user.name.lower() == u.name.lower() for u in adv_list)
    assert found

    adv_list_no_match = client.users.search(
        text="h78frg279fbg92ubue9b80fhXBGYF0hnvioh",
        search_fields=["name"],
        max_items=10,
    )
    assert next(adv_list_no_match, None) is None

    short_list = client.users.search(user_id=[static_user.id], max_items=3)
    assert_user_items(short_list, UserSearchItem)


def test_user_get(client: Albert, static_user: User):
    hits = poll_until(
        lambda: [
            user
            for user in client.users.search(
                text=static_user.name,
                user_id=[static_user.id],
                max_items=1,
            )
            if user.id == static_user.id
        ]
    )
    user_from_get = client.users.get_by_id(id=hits[0].id)
    assert user_from_get.id == static_user.id
    assert isinstance(user_from_get, User)


def test_hydrate_user(client: Albert, static_user: User):
    users = poll_until(
        lambda: [
            user
            for user in client.users.search(user_id=[static_user.id], max_items=1)
            if user.id == static_user.id
        ]
    )
    user = users[0]
    hydrated = user.hydrate()

    assert hydrated.id == user.id
    assert hydrated.name == user.name
    assert hydrated.email == user.email

    if user.location_id and hydrated.location:
        assert hydrated.location.id == user.location_id
    if user.location and hydrated.location:
        assert hydrated.location.name == user.location

    if user.roles and hydrated.roles:
        hydrated_roles = {role.id: role.name for role in hydrated.roles}
        for search_role in user.roles:
            assert search_role.roleId in hydrated_roles
            assert search_role.roleName == hydrated_roles[search_role.roleId]


def test_user_update_no_changes(client: Albert, static_user: User):
    """Test that updating a user without changes returns the current user."""
    updated = client.users.update(user=static_user)
    assert updated.id == static_user.id
    assert updated.name == static_user.name


def test_user_delete_non_existent(client: Albert):
    """Test deleting a non-existent user raises NotFoundError."""
    with pytest.raises(NotFoundError):
        client.users.delete(id="USR999999999")


def test_user_delete_invalid_id(client: Albert):
    """Test deleting with invalid ID format raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        client.users.delete(id="INVALID_ID")
