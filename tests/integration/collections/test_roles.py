from albert.client import Albert
from albert.resources.roles import Role


def assert_role_items(list_items: list[Role]):
    found = False
    for l in list_items:
        assert isinstance(l, Role)
        assert isinstance(l.name, str)
        assert isinstance(l.id, str)
        found = True
    assert found


def test_get_all_roles(client: Albert, static_roles: list[Role]):
    assert_role_items(client.roles.get_all())


def test_get_role(client: Albert, static_roles: list[Role]):
    role = client.roles.get_by_id(id=static_roles[0].id)
    assert isinstance(role, Role)
    assert role.id == static_roles[0].id
    assert role.name == static_roles[0].name
