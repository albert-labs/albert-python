import pytest
from pydantic import ValidationError

from albert.resources.property_data import (
    PropertyDataSearchItem,
    TaskData,
    TaskDataColumn,
    TaskDataColumnValue,
    TaskPropertyCreate,
    TaskPropertyData,
    TaskPropertyValue,
)


def test_task_data_column_value_coerces_string_to_task_property_value():
    """Test that a bare string value is wrapped in a TaskPropertyValue."""
    column_value = TaskDataColumnValue(id="DAC1", value="42")
    assert isinstance(column_value.value, TaskPropertyValue)
    assert column_value.value.value == "42"


def test_task_data_column_value_accepts_task_property_value_instance():
    """Test that an existing TaskPropertyValue is passed through unchanged."""
    wrapped = TaskPropertyValue(value="42")
    column_value = TaskDataColumnValue(id="DAC1", value=wrapped)
    assert column_value.value is wrapped


def test_task_property_create_rejects_boolean_value():
    """Test that a boolean value is rejected for TaskPropertyCreate.value."""
    with pytest.raises(ValidationError, match="Boolean values are not supported"):
        TaskPropertyCreate(data_column=TaskDataColumn(id="DAC1"), value=True)


@pytest.mark.parametrize("raw_value", [42, 3.14])
def test_task_property_create_coerces_numeric_value_to_string(raw_value):
    """Test that numeric values are coerced to strings before storage."""
    prop = TaskPropertyCreate(data_column=TaskDataColumn(id="DAC1"), value=raw_value)
    assert prop.value == str(raw_value)


def test_task_property_create_string_value_passes_through():
    """Test that a string value is left unchanged."""
    prop = TaskPropertyCreate(data_column=TaskDataColumn(id="DAC1"), value="already-a-string")
    assert prop.value == "already-a-string"


def test_task_property_create_visible_trial_number_defaults_to_trial_number():
    """Test that visible_trial_number falls back to trial_number when unset."""
    prop = TaskPropertyCreate(data_column=TaskDataColumn(id="DAC1"), trialNo=3)
    assert prop.visible_trial_number == 3


def test_task_property_create_visible_trial_number_defaults_to_one():
    """Test that visible_trial_number defaults to 1 when neither it nor trial_number is set."""
    prop = TaskPropertyCreate(data_column=TaskDataColumn(id="DAC1"))
    assert prop.visible_trial_number == 1


def test_task_property_create_visible_trial_number_explicit_value_kept():
    """Test that an explicitly provided visible_trial_number is not overwritten."""
    prop = TaskPropertyCreate(data_column=TaskDataColumn(id="DAC1"), trialNo=3, visibleTrialNo=9)
    assert prop.visible_trial_number == 9


# --- PropertyDataSearchItem ---


@pytest.mark.parametrize("parameter_group_id", ["PRG123", "DAT123", "123456"])
def test_property_data_search_item_accepts_parameter_group_id_forms(parameter_group_id):
    """Test that workflow parameterGroupId accepts PRG, DAT, and bare-numeric forms."""
    item = PropertyDataSearchItem.model_validate(
        {
            "id": "PTD1",
            "category": "task",
            "workflow": [
                {"name": "Temperature", "id": "PRM1", "parameterGroupId": parameter_group_id}
            ],
            "result": {"name": "Result", "id": "DAC1"},
            "dataTemplateId": "DAT1",
            "workflowId": "WFL1",
            "parentId": "TAS1",
            "dataTemplateName": "Template",
            "createdBy": "someone",
            "inventoryId": "INV1",
        }
    )
    assert item.workflow[0].parameter_group_id == parameter_group_id


def test_property_data_search_item_parameter_group_id_defaults_to_none():
    """Test that workflow parameterGroupId is None when absent from the result."""
    item = PropertyDataSearchItem.model_validate(
        {
            "id": "PTD1",
            "category": "task",
            "workflow": [{"name": "Temperature", "id": "PRM1"}],
            "result": {"name": "Result", "id": "DAC1"},
            "dataTemplateId": "DAT1",
            "workflowId": "WFL1",
            "parentId": "TAS1",
            "dataTemplateName": "Template",
            "createdBy": "someone",
            "inventoryId": "INV1",
        }
    )
    assert item.workflow[0].parameter_group_id is None


@pytest.mark.parametrize(
    "model",
    [
        TaskData.model_construct(final_workflow="WFL1"),
        TaskPropertyData.model_construct(parent_id="TAS1", final_workflow="WFL1"),
    ],
    ids=["TaskData", "TaskPropertyData"],
)
def test_finial_workflow_warns_once_and_aliases_final_workflow(model):
    """Test the deprecated finial_workflow alias warns exactly once and returns final_workflow."""
    with pytest.warns(DeprecationWarning, match="finial_workflow") as record:
        value = model.finial_workflow

    assert len(record) == 1
    assert value == model.final_workflow
