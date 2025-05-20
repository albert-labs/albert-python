from collections.abc import Callable

import pytest
from pydantic import validate_call

from albert.resources.identifiers import (
    InventoryId,
    TagId,
    UserId,
    ensure_block_id,
    ensure_data_column_id,
    ensure_datatemplate_id,
    ensure_interval_id,
    ensure_inventory_id,
    ensure_lot_id,
    ensure_parameter_id,
    ensure_paramter_group_id,
    ensure_project_id,
    ensure_project_search_id,
    ensure_propertydata_id,
    ensure_row_id,
    ensure_search_inventory_id,
    ensure_tag_id,
    ensure_task_id,
    ensure_unit_id,
    ensure_workflow_id,
    ensure_worksheet_id,
)


@pytest.mark.parametrize(
    "ensure_func,prefix,entity_code,error_msg",
    [
        (ensure_inventory_id, "INV", "A", "InventoryId cannot be empty"),
        (ensure_tag_id, "TAG", "", "TagId cannot be empty"),
        (ensure_data_column_id, "DAC", "", "DataColumnId cannot be empty"),
        (ensure_datatemplate_id, "DAT", "", "DataTemplateId cannot be empty"),
        (ensure_propertydata_id, "PTD", "", "PropertyDataId cannot be empty"),
        (ensure_block_id, "BLK", "", "BlockId cannot be empty"),
        (ensure_row_id, "ROW", "", "RowId cannot be empty"),
        (ensure_task_id, "TAS", "", "TaskId cannot be empty"),
        (ensure_project_id, "PRO", "P", "ProjectId cannot be empty"),
        (ensure_lot_id, "LOT", "", "LotId cannot be empty"),
        (ensure_parameter_id, "PRM", "", "ParameterId cannot be empty"),
        (ensure_paramter_group_id, "PRG", "", "ParameterGroupId cannot be empty"),
        (ensure_unit_id, "UNI", "", "UnitId cannot be empty"),
        (ensure_workflow_id, "WFL", "", "WorkflowId cannot be empty"),
        (ensure_worksheet_id, "WKS", "", "WorksheetId cannot be empty"),
    ],
)
def test_ensure_id_functions(
    ensure_func: Callable[[str], str], prefix: str, entity_code: str, error_msg: str
):
    # Test with Simple ID
    assert ensure_func(f"{entity_code}123") == f"{prefix}{entity_code}123"

    # Test with prefixed ID (uppercase)
    assert ensure_func(f"{prefix}{entity_code}123") == f"{prefix}{entity_code}123"

    # Test with prefixed ID (lowercase)
    assert ensure_func(f"{prefix.lower()}{entity_code}123") == f"{prefix}{entity_code}123"

    # Test empty strings
    with pytest.raises(ValueError, match=error_msg):
        ensure_func("")
    with pytest.raises(ValueError, match=error_msg):
        ensure_func(None)


def test_ensure_interval_id():
    assert ensure_interval_id("ROW123") == "ROW123"
    assert ensure_interval_id("ROW123XROW456") == "ROW123XROW456"
    with pytest.raises(ValueError, match="IntervalId cannot be empty"):
        ensure_interval_id("")

    assert ensure_row_id("row123") == "ROW123"

    assert ensure_row_id("row123Xrow456") == "ROW123XROW456"

    with pytest.raises(ValueError, match="Must be in format ROW# or ROW#XROW#"):
        ensure_interval_id("ROW123XROW456XROW789")

    with pytest.raises(ValueError, match="Must be in format ROW# or ROW#XROW#"):
        ensure_interval_id("123")

    with pytest.raises(ValueError, match="Must be in format ROW# or ROW#XROW#"):
        ensure_interval_id("123X456")

    with pytest.raises(ValueError, match="Must be in format ROW# or ROW#XROW#"):
        ensure_interval_id("ROW123XROW456X")

    with pytest.raises(ValueError, match="Must be in format ROW# or ROW#XROW#"):
        ensure_interval_id("ROW123XROW456XROW789")


@pytest.mark.parametrize(
    "ensure_func,prefix,optional_code,error_msg",
    [
        (ensure_search_inventory_id, "INV", "N", "SearchInventoryId cannot be empty"),
        (ensure_project_search_id, "PRO", "P", "ProjectSearchId cannot be empty"),
    ],
)
def test_ensure_search_inventory_id(ensure_func, prefix, optional_code, error_msg):
    # Test with Simple ID
    assert ensure_func(f"{optional_code}123") == f"{optional_code}123"

    # Test with prefixed ID (uppercase)
    assert ensure_func(f"{prefix}{optional_code}123") == f"{optional_code}123"

    # Test with prefixed ID (lowercase)
    assert ensure_func(f"{prefix.lower()}{optional_code}123") == f"{optional_code}123"

    # Test empty string
    with pytest.raises(ValueError, match=error_msg):
        ensure_func("")

    if not optional_code:
        assert ensure_func(123) == "123"


# Test functions with and without decorator
def test_validate_call_decorator():
    # Function with decorator
    @validate_call
    def decorated_func(inventory_id: InventoryId, tag_id: TagId):
        return inventory_id, tag_id

    # Function without decorator
    def undecorated_func(inventory_id: InventoryId, tag_id: TagId):
        return inventory_id, tag_id

    # Test decorated function
    inv_id, tag_id = decorated_func(inventory_id="A123", tag_id="456")
    assert inv_id == "INVA123"
    assert tag_id == "TAG456"

    # Test undecorated function - should not validate/transform
    inv_id, tag_id = undecorated_func(inventory_id="A123", tag_id="456")
    assert inv_id == "A123"
    assert tag_id == "456"


def test_validate_call_with_mixed_params():
    @validate_call
    def mixed_func(inventory_id: InventoryId, name: str, tag_id: TagId):
        return inventory_id, name, tag_id

    result = mixed_func(inventory_id="A123", name="test", tag_id="456")
    assert result == ("INVA123", "test", "TAG456")


def test_validate_call_with_empty_iterables():
    @validate_call
    def list_func(inventory_ids: list[InventoryId]):
        return inventory_ids

    result = list_func([])
    assert result == []


def test_validate_call_with_list_input():
    @validate_call
    def list_func(inventory_ids: list[InventoryId]):
        return inventory_ids

    result = list_func(["A123", "A456"])
    assert result == ["INVA123", "INVA456"]

    with pytest.raises(
        ValueError,
        match="InventoryId requires a type code e.g. 'A' for raw materials as in 'A1425'",
    ):
        list_func(["123", "456"])


def test_validate_call_with_union_list_and_type():
    @validate_call
    def union_list_func(inventory_ids: list[InventoryId] | InventoryId | None):
        return inventory_ids

    result = union_list_func(["A123", "A456"])
    assert result == ["INVA123", "INVA456"]

    result = union_list_func("A123")
    assert result == "INVA123"

    result = union_list_func(None)
    assert result is None


def test_validate_call_with_optional_parameter():
    @validate_call
    def optional_func(name: str, tag_id: TagId | None = None):
        return name, tag_id

    # Should work with None value for optional parameter
    assert optional_func("test") == ("test", None)
    assert optional_func("test", "123") == ("test", "TAG123")


def test_validate_call_with_optional_type():
    @validate_call
    def optional_func(inventory_id: InventoryId | None):
        return inventory_id

    assert optional_func(None) == None
    assert optional_func("A123") == "INVA123"


def test_validate_call_with_multiple_types():
    # TODO: Think about if there is a way to do this using
    # just pydantic...
    @validate_call
    def union_func(
        other_valid_id: TagId | None,
        multi_id_field: InventoryId | UserId | None,
    ):
        return multi_id_field, other_valid_id

    result = union_func(multi_id_field="A123", other_valid_id="456")
    assert result == ("INVA123", "TAG456")

    result = union_func(multi_id_field=None, other_valid_id="456")
    assert result == (None, "TAG456")

    result = union_func(multi_id_field="INVA123", other_valid_id=None)
    assert result == ("INVA123", None)

    # Note that this
    result = union_func(multi_id_field="USR111", other_valid_id=None)
    assert result == ("USR111", None)

    # Show that single type with optional None is still valid
    @validate_call
    def valid_func(tag_id: TagId | None):
        return tag_id

    assert valid_func(None) is None
    assert valid_func("TAG123") == "TAG123"
    assert valid_func("123") == "TAG123"


def test_validate_call_required_id():
    @validate_call
    def error_func(inventory_id: InventoryId):
        return inventory_id

    # Should handle None
    with pytest.raises(ValueError, match="should be a valid string"):
        error_func(inventory_id=None)


def test_validate_call_with_return_types():
    @validate_call
    def return_func(inventory_id: InventoryId) -> InventoryId:
        return inventory_id

    assert return_func("A123") == "INVA123"
