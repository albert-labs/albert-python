import pytest

from albert.albert import Albert
from albert.exceptions import BadRequestError
from albert.resources.parameter_groups import ParameterGroup


def _list_asserts(returned_list):
    found = False
    for i, u in enumerate(returned_list):
        if i == 50:
            break
        assert isinstance(u, ParameterGroup)
        found = True
    assert found


def test_basics(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    list_response = client.parameter_groups.list()
    _list_asserts(list_response)


def test_advanced_list(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    list_response = client.parameter_groups.list(
        text=[seeded_parameter_groups[0].name], types=[seeded_parameter_groups[0].type]
    )
    _list_asserts(list_response)


def test_dupe_raises_error(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    pg = seeded_parameter_groups[0].model_copy(update={"id": None})
    # reset audit fields
    pg._created = None
    pg._updated = None
    pg.parameters = []
    with pytest.raises(BadRequestError):
        client.parameter_groups.create(parameter_group=pg)
