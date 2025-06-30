import json

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


def test_create_role_fake(fake_client: Albert):
    """Test role creation using fake session."""
    # Arrange
    mock_response = {
        "albertId": "new-role-id",
        "name": "New Role",
        "policies": [],
        "tenant": "test-tenant",
    }
    fake_client.session.configure_response(
        "POST", "/api/v3/acl/roles", json.dumps(mock_response).encode()
    )
    original_requests_length = len(fake_client.session.requests)
    role = Role(name="New Role", tenant="test-tenant", policies=[])
    created_role = fake_client.roles.create(role=role)

    # Assert
    assert len(fake_client.session.requests) == original_requests_length + 1
    # check the latest request added to the list matches the mock response
    request = fake_client.session.requests[-1]
    assert request["method"] == "POST"
    assert request["url"] == "/api/v3/acl/roles"
    assert request["json"]["name"] == "New Role"

    assert isinstance(created_role, Role)
    assert created_role.name == "New Role"
    assert created_role.id == "new-role-id"
