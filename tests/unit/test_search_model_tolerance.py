"""Offline model-parsing tests for search-tolerance and tenant-enum fixes.

Pins the wire shapes observed in the wild (eval-log dropped rows, citation
hydration failures) so the tolerance fixes cannot regress. No client or network
required — pure model validation.
"""

import pytest

from albert.resources.data_templates import DataTemplate, DataTemplateSearchItem
from albert.resources.parameter_groups import ParameterGroupSearchItem
from albert.resources.projects import Project, State
from albert.resources.property_data import PropertyDataSearchItem
from albert.resources.sheets import Design, DesignType


def _property_data_row(**overrides):
    row = {
        "id": "PTD9999999",
        "category": "task",
        "workflow": [],
        "result": {"value": "1", "name": "r", "id": "PR9999999"},
        "dataTemplateId": "DAT9999999",
        "parentId": "INVA9999999",
        "dataTemplateName": "x",
        "createdBy": "u",
        "inventoryId": "INVA9999999",
        "workflowId": "WFL1",
    }
    row.update(overrides)
    return row


def test_property_data_search_item_without_project_id() -> None:
    item = PropertyDataSearchItem.model_validate(_property_data_row())
    assert item.project_id is None


def test_property_data_search_item_with_project_id() -> None:
    item = PropertyDataSearchItem.model_validate(_property_data_row(projectId="PROP9999999"))
    assert item.project_id == "PROP9999999"


def test_data_template_search_item_column_without_id_or_localized_names() -> None:
    item = DataTemplateSearchItem.model_validate(
        {"albertId": "DAT9999999", "name": "x", "dataColumns": [{"name": "col only"}]}
    )
    assert item.data_columns is not None
    assert item.data_columns[0].id is None
    assert item.data_columns[0].localized_names is None


def test_parameter_group_search_item_nested_list_metadata() -> None:
    """Observed: metadata.<custom-field> arrives wrapped in one extra list level."""
    item = ParameterGroupSearchItem.model_validate(
        {"name": "x", "metadata": {"entitycusfield": [[{"name": "n", "id": "CF1"}]]}}
    )
    assert item.metadata is not None
    entries = item.metadata["entitycusfield"]
    assert len(entries) == 1
    assert getattr(entries[0], "id", None) == "CF1"


def test_parameter_group_search_item_drops_id_less_metadata_and_links() -> None:
    item = ParameterGroupSearchItem.model_validate(
        {
            "name": "x",
            "metadata": {"cleared": {}},
            "owner": [{}],
            "tags": [{}, {"id": "TAG1", "name": "a"}],
        }
    )
    assert item.metadata is not None and "cleared" not in item.metadata
    assert item.owner == []
    assert item.tags is not None and len(item.tags) == 1


def test_parameter_group_search_item_parameter_without_id() -> None:
    item = ParameterGroupSearchItem.model_validate(
        {"name": "x", "parameters": [{"name": "id-less"}]}
    )
    assert item.parameters[0].id is None


@pytest.mark.parametrize(
    ("raw", "expected_type"),
    [
        ("Active", State),
        ("Just Started", State),
        ("In Progress", State),
        ("Totally Custom", str),
    ],
)
def test_project_state_enum_for_known_str_for_unknown(raw: str, expected_type: type) -> None:
    state = Project(name="x", description="x", state=raw).state
    assert isinstance(state, expected_type)
    if expected_type is State:
        assert isinstance(state, State)


@pytest.mark.parametrize(
    ("raw", "expected_type"),
    [
        ("products", DesignType),
        ("reagents", DesignType),
        ("legacy-weird", str),
    ],
)
def test_design_type_enum_for_known_str_for_unknown(raw: str, expected_type: type) -> None:
    design_type = Design(albertId="WKD9999999", designType=raw).design_type
    assert isinstance(design_type, expected_type)


def test_convert_tags_id_only_dict_raises_clear_error() -> None:
    with pytest.raises(Exception, match="name alongside its id"):
        DataTemplate(name="x", Tags=[{"id": "TAG9999999"}])


def test_convert_tags_accepts_id_and_name() -> None:
    template = DataTemplate(name="x", Tags=[{"id": "TAG9999999", "name": "AAMA"}])
    assert template.tags is not None
    assert template.tags[0].id == "TAG9999999"
