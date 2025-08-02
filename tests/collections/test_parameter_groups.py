import pytest

from albert.client import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import BadRequestError
from albert.resources.parameter_groups import (
    DataType,
    EnumValidationValue,
    ParameterGroup,
    ParameterGroupSearchItem,
    ValueValidation,
)
from albert.resources.tags import Tag
from albert.resources.units import Unit


def assert_valid_parameter_groups(
    items: list[ParameterGroupSearchItem | ParameterGroup],
    expected_type: type,
):
    """Assert that items are valid ParameterGroup or ParameterGroupSearchItem instances."""
    assert items, "Expected at least one item"
    for pg in items[:10]:
        assert isinstance(pg, expected_type)
        assert isinstance(pg.id, str) and pg.id
        assert isinstance(pg.name, str) and pg.name


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


def test_parameter_group_search_basic(
    client: Albert, seeded_parameter_groups: list[ParameterGroup]
):
    """Test basic search for Parameter Groups."""
    results = list(client.parameter_groups.search(max_items=10))
    assert_valid_parameter_groups(results, ParameterGroupSearchItem)


def test_parameter_group_get_all(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    """Test get_all for fully hydrated Parameter Groups."""
    results = list(client.parameter_groups.get_all(max_items=10))
    assert_valid_parameter_groups(results, ParameterGroup)


def test_parameter_group_search_with_filters(
    client: Albert, seeded_parameter_groups: list[ParameterGroup]
):
    """Test search with text and type filters."""
    pg = seeded_parameter_groups[0]
    results = list(client.parameter_groups.search(text=pg.name, types=[pg.type], max_items=10))
    assert_valid_parameter_groups(results, ParameterGroupSearchItem)


def test_hydrate_pg(client: Albert):
    pgs = list(client.parameter_groups.search(max_items=5))
    assert pgs, "Expected at least one pg in search results"

    for pg in pgs:
        hydrated = pg.hydrate()

        # identity checks
        assert hydrated.id == pg.id
        assert hydrated.name == pg.name


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
):
    pg = [x for x in seeded_parameter_groups if "metadata" in x.name.lower()][0]
    new_name = f"{seed_prefix}-new name"
    pg.name = new_name
    pg.description = f"{seed_prefix}-new description"

    updated_pg = client.parameter_groups.update(parameter_group=pg)

    assert updated_pg.name == new_name
    assert updated_pg.id == pg.id
    assert updated_pg.description == f"{seed_prefix}-new description"


def test_update_tags(
    client: Albert, seeded_parameter_groups: list[ParameterGroup], seeded_tags: list[Tag]
):
    pg = seeded_parameter_groups[0]
    original_tags = [x.id for x in pg.tags]

    new_tag = [x for x in seeded_tags if x.id not in original_tags][0]
    pg.tags.append(new_tag)
    updated_pg = client.parameter_groups.update(parameter_group=pg)
    assert updated_pg is not None
    assert new_tag.id in [x.id for x in updated_pg.tags]
    assert len(updated_pg.tags) == len(original_tags) + 1


def test_update_validations(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    pg = [x for x in seeded_parameter_groups if "Numbers Parameter Group" in x.name][0]
    pg = client.parameter_groups.get_by_id(id=pg.id)
    param = pg.parameters[0]  # Parameter with number validation

    assert param.validation[0].datatype == DataType.NUMBER
    assert param.validation[0].min == "0"
    assert param.validation[0].max == "100"

    # Update validation
    param.validation[0] = ValueValidation(datatype=DataType.STRING)
    param.value = "Updated Value"
    updated_pg = client.parameter_groups.update(parameter_group=pg)

    assert updated_pg is not None
    updated_param = updated_pg.parameters[0]
    assert updated_param.validation[0].datatype == DataType.STRING
    assert updated_param.value == "Updated Value"


def test_enum_validation_creation(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    pg = [x for x in seeded_parameter_groups if "Enums Parameter Group" in x.name][0]
    pg = client.parameter_groups.get_by_id(id=pg.id)
    param = pg.parameters[2]  # Parameter with enum validation

    assert param.validation[0].datatype == DataType.ENUM
    assert len(param.validation[0].value) == 2
    assert param.validation[0].value[0].text == "Option1"
    assert param.validation[0].value[1].text == "Option2"


def test_enum_validation_addition(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    pg = [x for x in seeded_parameter_groups if "Enums Parameter Group" in x.name][0]
    pg = client.parameter_groups.get_by_id(id=pg.id)
    param = pg.parameters[2]  # Parameter with enum validation
    initial_enum_count = len(param.validation[0].value)
    # Add a new enum value
    param.validation[0].value.append(EnumValidationValue(text="Option3"))
    updated_pg = client.parameter_groups.update(parameter_group=pg)

    assert updated_pg is not None
    updated_param = updated_pg.parameters[2]
    assert len(updated_param.validation[0].value) == initial_enum_count + 1
    # make sure it was added to the enum

    assert "Option3" in [x.text for x in updated_param.validation[0].value]
    for param in updated_pg.parameters:
        if (
            not param.validation
            or len(param.validation) == 0
            or param.validation[0].datatype != DataType.ENUM
        ):
            continue
        for v in param.validation[0].value:
            assert v.id is not None


def test_enum_validation_removal(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    pg = [x for x in seeded_parameter_groups if "Enums Parameter Group" in x.name][0]
    # get current state of the pg
    pg = client.parameter_groups.get_by_id(id=pg.id)
    param = pg.parameters[2]  # Parameter with enum validation

    initial_enum_count = len(param.validation[0].value)

    # Remove an enum value
    param.validation[0].value.pop(1)
    updated_pg = client.parameter_groups.update(parameter_group=pg)

    assert updated_pg is not None
    updated_param = updated_pg.parameters[2]
    assert len(updated_param.validation[0].value) == initial_enum_count - 1
    assert updated_param.validation[0].value[0].text == "Option1"


def test_enum_validation_update(client: Albert, seeded_parameter_groups: list[ParameterGroup]):
    pg = [x for x in seeded_parameter_groups if "Enums Parameter Group" in x.name][0]
    param = pg.parameters[2]  # Parameter with enum validation

    old_options = [x.text for x in param.validation[0].value]

    # Replace the entire enum validation
    param.validation[0].value = [
        EnumValidationValue(text="NewOption1"),
        EnumValidationValue(text="NewOption2"),
    ]
    updated_pg = client.parameter_groups.update(parameter_group=pg)

    assert updated_pg is not None
    updated_param = updated_pg.parameters[2]
    assert len(updated_param.validation[0].value) == 2
    new_options = [x.text for x in updated_param.validation[0].value]
    assert "NewOption1" in new_options
    assert "NewOption2" in new_options
    for old in old_options:
        assert old not in new_options


def test_update_units(
    client: Albert, seeded_parameter_groups: list[ParameterGroup], seeded_units: list[Unit]
):
    pg = [x for x in seeded_parameter_groups if "Numbers Parameter Group" in x.name][0]
    param = pg.parameters[0]  # Parameter with number validation and unit
    original_unit = param.unit

    # Update unit
    new_unit = seeded_units[2]
    param.unit = EntityLink(id=new_unit.id)
    updated_pg = client.parameter_groups.update(parameter_group=pg)

    assert updated_pg is not None
    updated_param = updated_pg.parameters[0]
    assert updated_param.unit.id == new_unit.id
    assert updated_param.unit.id != original_unit.id
