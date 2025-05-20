from albert.albert import Albert
from albert.resources.roles import Role


def _list_asserts(list_items: list[Role]):
    found = False
    for l in list_items:
        assert isinstance(l, Role)
        assert isinstance(l.name, str)
        assert isinstance(l.id, str)
        found = True
    assert found


def test_list_roles(client: Albert, static_roles: list[Role]):
    _list_asserts(client.roles.list())
