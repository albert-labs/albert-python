from collections.abc import Generator

from albert import Albert
from albert.resources.base import Status
from albert.resources.users import User


def _list_asserts(returned_list, limit=30):
    found = False
    for i, u in enumerate(returned_list):
        found = True
        if i == limit:
            break
        assert isinstance(u, User)
        assert isinstance(u.name, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("USR")
    assert found  # make sure at least one was returned


def test_simple_users_list(client: Albert, seeded_users: list[User]):
    simple_user_list = client.users.list()
    assert isinstance(simple_user_list, Generator)
    _list_asserts(simple_user_list)


def test_advanced_users_list(client: Albert, seeded_users: list[User]):
    # Check something reasonable was found near the top
    faux_name = seeded_users[1].name.split(" ")[0]
    adv_list = client.users.list(text=faux_name, status=Status.ACTIVE, search_fields=["name"])
    found = False
    for i, u in enumerate(adv_list):
        if i == 20:
            break
        if seeded_users[1].name.lower() == u.name.lower():
            found = True
            break
    assert found

    adv_list_no_match = client.users.list(
        text="h78frg279fbg92ubue9b80fhXBGYF&*0hnvioh", search_fields=["name"]
    )
    assert isinstance(adv_list_no_match, Generator)
    assert next(adv_list_no_match, None) is None

    short_list = client.users._list_generator(limit=3)
    _list_asserts(short_list, limit=5)


def test_user_get(client: Albert, seeded_users: list[User]):
    first_hit = next(client.users.list(text=seeded_users[1].name), None)
    user_from_get = client.users.get_by_id(user_id=first_hit.id)
    assert user_from_get.id == first_hit.id
    assert isinstance(user_from_get, User)
