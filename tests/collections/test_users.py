from collections.abc import Iterator

from albert import Albert
from albert.resources.base import Status
from albert.resources.users import User, UserFilterParams, UserSearchItem


def assert_user_items(
    list_iterator: Iterator[User | UserSearchItem],
    expected_type: type,
):
    """Assert all items are of expected types."""
    assert isinstance(list_iterator, Iterator), "Expected an Iterator"

    found = False
    for i, item in enumerate(list_iterator):
        if i == 30:
            break

        assert isinstance(item, expected_type)
        assert isinstance(item.name, str)
        assert isinstance(item.id, str)
        assert item.id.startswith("USR")
        found = True

    assert found, f"No {expected_type.__name__} items found in iterator"


def test_simple_users_get_all(client: Albert):
    simple_user_list = client.users.get_all()
    assert_user_items(simple_user_list, User)


def test_simple_users_search(client: Albert):
    simple_user_list = client.users.search()
    assert_user_items(simple_user_list, UserSearchItem)


def test_advanced_users_search(client: Albert, static_user: User):
    # Check something reasonable was found near the top
    faux_name = static_user.name.split(" ")[0]
    params = UserFilterParams(text=faux_name, status=[Status.ACTIVE], search_fields=["name"])
    adv_list = client.users.search(params=params)
    found = False
    for i, u in enumerate(adv_list):
        if i == 20:
            break
        if static_user.name.lower() == u.name.lower():
            found = True
            break
    assert found

    params = UserFilterParams(
        text="h78frg279fbg92ubue9b80fhXBGYF&*0hnvioh", search_fields=["name"]
    )
    adv_list_no_match = client.users.search(params=params)
    assert next(adv_list_no_match, None) is None

    params = UserFilterParams(limit=3)
    short_list = client.users.search(params=params)
    assert_user_items(short_list, UserSearchItem)


def test_user_get(client: Albert, static_user: User):
    params = UserFilterParams(text=static_user.name)
    first_hit = next(client.users.search(params=params), None)
    user_from_get = client.users.get_by_id(id=first_hit.id)
    assert user_from_get.id == first_hit.id
    assert isinstance(user_from_get, User)
