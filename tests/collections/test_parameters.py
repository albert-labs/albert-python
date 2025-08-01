import uuid

from albert.client import Albert
from albert.resources.parameters import Parameter


def assert_valid_parameter_items(returned_list: list[Parameter]):
    """Assert that returned items are valid Parameter objects."""
    assert returned_list, "Expected at least one Parameter"
    for u in returned_list[:10]:
        assert isinstance(u, Parameter)


def test_parameter_get_all_basic(client: Albert, seeded_parameters: list[Parameter]):
    """Test basic retrieval of parameters."""
    response = list(client.parameters.get_all(max_items=10))
    assert_valid_parameter_items(response)


def test_parameter_get_all_with_name(client: Albert, seeded_parameters: list[Parameter]):
    """Test get_all with name filtering."""
    response = list(
        client.parameters.get_all(names=seeded_parameters[0].name, exact_match=True, max_items=10)
    )
    assert_valid_parameter_items(response)


def test_parameter_get_all_by_ids(client: Albert, seeded_parameters: list[Parameter]):
    """Test get_all with a list of parameter IDs."""
    ids = [x.id for x in seeded_parameters]
    results = list(client.parameters.get_all(ids=ids, max_items=10))
    assert results, "Expected at least one result"
    assert len(results) == len(ids)
    assert {x.id for x in results} == set(ids)


def test_get(client: Albert, seeded_parameters: list[Parameter]):
    p = client.parameters.get_by_id(id=seeded_parameters[0].id)
    assert p.id == seeded_parameters[0].id
    assert p.name == seeded_parameters[0].name


def test_get_or_create_parameters(caplog, client: Albert, seeded_parameters: list[Parameter]):
    p = seeded_parameters[0].model_copy(update={"id": None})
    returned = client.parameters.get_or_create(parameter=p)
    assert (
        f"Parameter with name {p.name} already exists. Returning existing parameter."
        in caplog.text
    )
    assert returned.id == seeded_parameters[0].id
    assert returned.name == seeded_parameters[0].name


def test_update(client: Albert, seeded_parameters: list[Parameter]):
    p = seeded_parameters[0].model_copy(deep=True)
    updated_name = f"TEST - {uuid.uuid4()}"
    p.name = updated_name
    updated = client.parameters.update(parameter=p)
    assert updated.name == updated_name
