import uuid
from collections.abc import Generator

from albert.albert import Albert
from albert.resources.parameters import Parameter


def _list_asserts(returned_list):
    found = False
    for i, u in enumerate(returned_list):
        if i == 50:
            break
        assert isinstance(u, Parameter)
        found = True
    assert found


def test_basics(client: Albert, seeded_parameters: list[Parameter]):
    list_response = client.parameters.list()
    assert isinstance(list_response, Generator)
    _list_asserts(list_response)


def test_advanced_list(client: Albert, seeded_parameters: list[Parameter]):
    list_response = client.parameters.list(names=[seeded_parameters[0].name])
    assert isinstance(list_response, Generator)
    _list_asserts(list_response)


def test_get(client: Albert, seeded_parameters: list[Parameter]):
    p = client.parameters.get_by_id(id=seeded_parameters[0].id)
    assert p.id == seeded_parameters[0].id
    assert p.name == seeded_parameters[0].name


def test_returns_dupe(caplog, client: Albert, seeded_parameters: list[Parameter]):
    p = seeded_parameters[0].model_copy(update={"id": None})
    returned = client.parameters.create(parameter=p)
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
    updated = client.parameters.update(updated_parameter=p)
    assert updated.name == updated_name
