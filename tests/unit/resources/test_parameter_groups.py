import pytest
from pydantic import ValidationError

from albert.resources.parameter_groups import (
    ParameterGroup,
    ParameterGroupSearchItem,
    ParameterValue,
)
from albert.resources.parameters import Parameter, ParameterCategory


def test_parameter_value_requires_id_or_parameter():
    """Test that a ParameterValue must be given either an id or a parameter object."""
    with pytest.raises(ValidationError):
        ParameterValue(value="500")


def test_parameter_value_populates_fields_from_parameter():
    """Test that supplying a parameter object populates id, category, and name."""
    parameter = Parameter(name="Temperature", albertId="PRM123", category="Normal")
    value = ParameterValue(parameter=parameter, value="500")

    assert value.id == "PRM123"
    assert value.category == ParameterCategory.NORMAL
    assert value.name == "Temperature"
    # `parameter` itself is excluded from serialization
    assert "parameter" not in value.model_dump(by_alias=True, exclude_none=True)


def test_parameter_value_malformed_dict_value_coerced_to_none():
    """Test that a malformed dict value with no id is coerced to None (IN-10)."""
    value = ParameterValue(id="PRM123", value={"foo": "bar"})
    assert value.value is None


def test_parameter_value_valid_dict_value_passes_through():
    """Test that a dict value with an id is not coerced away."""
    value = ParameterValue.model_construct(id="PRM123", value={"id": "INV1"})
    assert value.value == {"id": "INV1"}


def test_parameter_group_search_item_sanitizes_owner_tags_acl_team_missing_id():
    """Test that entity-link list fields without an id are dropped from search items."""
    raw = {
        "albertId": "PRG23111",
        "name": "sdfgfdgd",
        "owner": [{}, {"id": "USR1", "name": "Alice"}],
        "tags": [{"id": "TAG1"}, {}],
        "acl": [{}],
        "team": [{"id": "USR2"}, {}],
    }
    item = ParameterGroupSearchItem(**raw)
    assert [o.id for o in item.owner] == ["USR1"]
    assert [t.id for t in item.tags] == ["TAG1"]
    assert item.acl == []
    assert [t.id for t in item.team] == ["USR2"]


def test_parameter_group_search_item_sanitize_entity_link_lists_passes_non_list_through():
    """Test that a non-list value for owner/tags/acl/team is left untouched."""
    item = ParameterGroupSearchItem(
        name="x", albertId="PRG1", owner=None, tags=None, acl=None, team=None
    )
    assert item.owner is None
    assert item.tags is None


def test_parameter_group_search_item_sanitizes_empty_entity_link_metadata():
    """Some tenants have parameter-group metadata whose entity-link fields were
    cleared server-side to `[{}]` instead of `[]`, which fails `MetadataItem`
    validation.
    """
    raw = {
        "albertId": "PRG23111",
        "name": "sdfgfdgd",
        "metadata": {
            "AdvCTDSTPT_1": [{}],
            "AdvPGLSPTINV_2": [{}],
            "ADVNUMPTPG_1": 23,
            "ADVNUMPTPG_2": 445,
        },
    }
    item = ParameterGroupSearchItem(**raw)
    assert item.metadata["AdvCTDSTPT_1"] == []
    assert item.metadata["AdvPGLSPTINV_2"] == []
    assert item.metadata["ADVNUMPTPG_1"] == 23
    assert item.metadata["ADVNUMPTPG_2"] == 445


def test_parameter_group_metadata_non_dict_value_is_left_to_type_validation():
    """Test that a non-dict metadata value bypasses sanitization and fails normal type checks."""
    with pytest.raises(ValidationError):
        ParameterGroup(name="x", metadata=[1, 2, 3])


def test_parameter_group_sanitizes_empty_entity_link_metadata():
    """Same defect as above but against the hydrated ParameterGroup model."""
    raw = {
        "albertId": "PRG23111",
        "name": "sdfgfdgd",
        "class": "shared",
        "Metadata": {
            "AdvCTDSTPT_1": [{}],
            "bareEmptyLink": {},
            "ADVNUMPTPG_1": 23,
        },
    }
    pg = ParameterGroup(**raw)
    assert pg.metadata["AdvCTDSTPT_1"] == []
    assert "bareEmptyLink" not in pg.metadata
    assert pg.metadata["ADVNUMPTPG_1"] == 23
