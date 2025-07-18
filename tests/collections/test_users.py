from collections.abc import Iterator

from albert import Albert
from albert.core.shared.enums import Status
from albert.resources.users import User, UserSearchItem


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


def test_simple_users_search(client: Albert):
    user_list = list(client.users.search(max_items=10))
    assert_user_items(user_list, UserSearchItem)


def test_advanced_users_search(client: Albert, static_user: User):
    faux_name = static_user.name.split(" ")[0]
    adv_list = client.users.search(
        text=faux_name,
        status=[Status.ACTIVE],
        search_fields=["name"],
        max_items=20,
    )
    found = any(static_user.name.lower() == u.name.lower() for u in adv_list)
    assert found

    adv_list_no_match = client.users.search(
        text="h78frg279fbg92ubue9b80fhXBGYF&*0hnvioh",
        search_fields=["name"],
        max_items=10,
    )
    assert next(adv_list_no_match, None) is None

    short_list = client.users.search(max_items=3)
    assert_user_items(short_list, UserSearchItem)


def test_user_get(client: Albert, static_user: User):
    first_hit = next(client.users.search(text=static_user.name, max_items=1), None)
    user_from_get = client.users.get_by_id(id=first_hit.id)
    assert user_from_get.id == first_hit.id
    assert isinstance(user_from_get, User)


def test_hydrate_user(client: Albert):
    users = list(client.users.search(max_items=5))
    assert users, "Expected at least one user in search results"

    for user in users:
        hydrated = user.hydrate()

        # identity checks
        assert hydrated.id == user.id
        assert hydrated.name == user.name
        assert hydrated.email == user.email

        # location check
        if user.location_id and hydrated.location:
            assert hydrated.location.id == user.location_id
        if user.location and hydrated.location:
            assert hydrated.location.name == user.location

        # role consistency
        if user.roles and hydrated.roles:
            for search_role, full_role in zip(user.roles, hydrated.roles, strict=False):
                assert search_role.roleId == full_role.id
                assert search_role.roleName == full_role.name
