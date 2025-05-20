import pytest

from albert.albert import Albert
from albert.exceptions import BadRequestError
from albert.resources.parameter_groups import ParameterGroup
from tests.utils.test_patches import change_metadata, make_metadata_update_assertions


def _list_asserts(returned_list):
    found = False
    for i, u in enumerate(returned_list):
        if i == 50:
            break
        assert isinstance(u, ParameterGroup)
        found = True
    assert found


def test_get_by_id(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    pg = client.parameter_groups.get_by_id(id=seeded_parameter_groups[0].id)
    assert isinstance(pg, ParameterGroup)
    assert pg.id == seeded_parameter_groups[0].id
    assert pg.name == seeded_parameter_groups[0].name


def test_get_by_ids(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    ids = [x.id for x in seeded_parameter_groups]
    pg = client.parameter_groups.get_by_ids(ids=ids)
    assert isinstance(pg, list)
    assert len(pg) == len(seeded_parameter_groups)
    for i, u in enumerate(pg):
        assert isinstance(u, ParameterGroup)
        assert u.id == seeded_parameter_groups[i].id
        assert u.name == seeded_parameter_groups[i].name


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


def test_update(
    client: Albert,
    seeded_parameter_groups: list[ParameterGroup],
    seed_prefix: str,
    static_lists: list[str],
):
    pg = [x for x in seeded_parameter_groups if "metadata" in x.name.lower()][0]
    new_name = f"{seed_prefix}-new name"
    pg.name = new_name
    new_metadata = change_metadata(
        existing_metadata=pg.metadata, static_lists=static_lists, seed_prefix=seed_prefix
    )

    pg.metadata = new_metadata
    updated_pg = client.parameter_groups.update(parameter_group=pg)

    assert updated_pg.name == new_name
    assert updated_pg.id == pg.id

    # check metadata updates
    make_metadata_update_assertions(new_metadata, updated_pg)
