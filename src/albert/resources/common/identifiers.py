from typing import Annotated

from pydantic import AfterValidator

_ALBERT_PREFIXES = {
    "BlockId": "BLK",
    "BTInsightId": "INS",
    "BTDatasetId": "DST",
    "BTModelId": "MDL",
    "BTModelSessionId": "MDS",
    "CustomFieldId": "CTF",
    "DataColumnId": "DAC",
    "DataTemplateId": "DAT",
    "EntityTypeId": "ETT",
    "InventoryId": "INV",
    "LinkId": "LNK",
    "LotId": "LOT",
    "NotebookId": "NTB",
    "ParameterGroupId": "PRG",
    "ParameterId": "PRM",
    "ProjectId": "PRO",
    "PropertyDataId": "PTD",
    "RowId": "ROW",
    "SynthesisId": "SYN",
    "TagId": "TAG",
    "TaskId": "TAS",
    "UnitId": "UNI",
    "UserId": "USR",
    "WorksheetId": "WKS",
    "WorkflowId": "WFL",
    # Search Specific Ids
    "SearchInventoryId": "INV",
    "SearchProjectId": "PRO",
}


def _validate_coded_id(id: str, id_type: str) -> str:
    """Common validation for all ID types."""
    if not id:
        raise ValueError(f"{id_type} cannot be empty")
    if id.isdigit():
        raise ValueError(
            f"{id_type} requires a type code e.g. 'A' for raw materials as in 'A1425'"
        )
    return id


def _is_valid_albert_prefix(id: str) -> bool:
    """Check if the id starts with a valid Albert prefix."""
    return any(id.upper().startswith(prefix) for prefix in _ALBERT_PREFIXES.values())


def _ensure_albert_id(id: str, id_type: str) -> str:
    """Generic function to ensure Albert IDs follow the correct pattern.

    Args:
        id: The ID to validate and format
        id_type: The type name for more helpful error messages
    """
    if not id:
        raise ValueError(f"{id_type} cannot be empty")

    prefix = _ALBERT_PREFIXES[id_type]

    # Check if already has correct prefix
    if id.upper().startswith(prefix):
        return id.upper()

    # Check if has different Albert prefix
    if _is_valid_albert_prefix(id):
        raise ValueError(f"{id_type} {id} has invalid prefix. Expected: {prefix}")

    return f"{prefix}{id.upper()}"


def ensure_block_id(id: str) -> str:
    return _ensure_albert_id(id, "BlockId")


BlockId = Annotated[str, AfterValidator(ensure_block_id)]


def ensure_btinsight_id(id: str) -> str:
    return _ensure_albert_id(id, "BTInsightId")


BTInsightId = Annotated[str, AfterValidator(ensure_btinsight_id)]


def ensure_btdataset_id(id: str) -> str:
    return _ensure_albert_id(id, "BTDatasetId")


BTDatasetId = Annotated[str, AfterValidator(ensure_btdataset_id)]


def ensure_btmodel_id(id: str) -> str:
    return _ensure_albert_id(id, "BTModelId")


BTModelId = Annotated[str, AfterValidator(ensure_btmodel_id)]


def ensure_btmodel_session_id(id: str) -> str:
    return _ensure_albert_id(id, "BTModelSessionId")


BTModelSessionId = Annotated[str, AfterValidator(ensure_btmodel_session_id)]


def ensure_inventory_id(id: str) -> str:
    id = _validate_coded_id(id, "InventoryId")
    return _ensure_albert_id(id, "InventoryId")


InventoryId = Annotated[str, AfterValidator(ensure_inventory_id)]


# NOTE: Search endpoints follow a different prefix requirement
# for certain fields. this one is for inventory IDs that are passed in
# as a filter.
def ensure_search_inventory_id(id: str) -> str:
    id = _validate_coded_id(id, "SearchInventoryId")
    if id.upper().startswith("INV"):
        id = id[3:]  # Remove INV prefix
    return id


SearchInventoryId = Annotated[str, AfterValidator(ensure_search_inventory_id)]


def ensure_interval_id(id: str) -> str:
    if not id:
        raise ValueError("IntervalId cannot be empty")

    # Check if it matches ROW# or ROW#XROW# pattern
    parts = id.upper().split("X")
    if len(parts) > 2:
        raise ValueError(f"IntervalId {id} is invalid. Must be in format ROW# or ROW#XROW#")

    for part in parts:
        if not part.startswith("ROW") or not part[3:].isdigit():
            raise ValueError(f"IntervalId {id} is invalid. Must be in format ROW# or ROW#XROW#")

    return id.upper()


IntervalId = Annotated[str, AfterValidator(ensure_interval_id)]


def ensure_parameter_id(id: str) -> str:
    return _ensure_albert_id(id, "ParameterId")


ParameterId = Annotated[str, AfterValidator(ensure_parameter_id)]


def ensure_paramter_group_id(id: str) -> str:
    return _ensure_albert_id(id, "ParameterGroupId")


ParameterGroupId = Annotated[str, AfterValidator(ensure_paramter_group_id)]


def ensure_custom_field_id(id: str) -> str:
    return _ensure_albert_id(id, "CustomFieldId")


CustomFieldId = Annotated[str, AfterValidator(ensure_custom_field_id)]


def ensure_entity_type_id(id: str) -> str:
    return _ensure_albert_id(id, "EntityTypeId")


EntityTypeId = Annotated[str, AfterValidator(ensure_entity_type_id)]


def ensure_data_column_id(id: str) -> str:
    return _ensure_albert_id(id, "DataColumnId")


DataColumnId = Annotated[str, AfterValidator(ensure_data_column_id)]


def ensure_datatemplate_id(id: str) -> str:
    if id and id.upper().startswith("DT"):
        id = f"DAT{id[2:]}"  # Replace DT with DAT
    return _ensure_albert_id(id, "DataTemplateId")


DataTemplateId = Annotated[str, AfterValidator(ensure_datatemplate_id)]


def ensure_propertydata_id(id: str) -> str:
    return _ensure_albert_id(id, "PropertyDataId")


PropertyDataId = Annotated[str, AfterValidator(ensure_propertydata_id)]


def ensure_task_id(id: str) -> str:
    return _ensure_albert_id(id, "TaskId")


TaskId = Annotated[str, AfterValidator(ensure_task_id)]


def ensure_project_id(id: str) -> str:
    return _ensure_albert_id(id, "ProjectId")


ProjectId = Annotated[str, AfterValidator(ensure_project_id)]


def ensure_project_search_id(id: str) -> str:
    id = _validate_coded_id(id, "ProjectSearchId")
    if id.upper().startswith("PRO"):
        id = id[3:]  # Remove PRO prefix
    return id


SearchProjectId = Annotated[str, AfterValidator(ensure_project_search_id)]


def ensure_link_id(id: str) -> str:
    return _ensure_albert_id(id, "LinkId")


LinkId = Annotated[str, AfterValidator(ensure_link_id)]


def ensure_lot_id(id: str) -> str:
    return _ensure_albert_id(id, "LotId")


LotId = Annotated[str, AfterValidator(ensure_lot_id)]


def ensure_notebook_id(id: str) -> str:
    return _ensure_albert_id(id, "NotebookId")


NotebookId = Annotated[str, AfterValidator(ensure_notebook_id)]


def ensure_synthesis_id(id: str) -> str:
    return _ensure_albert_id(id, "SynthesisId")


SynthesisId = Annotated[str, AfterValidator(ensure_synthesis_id)]


def ensure_tag_id(id: str) -> str:
    return _ensure_albert_id(id, "TagId")


TagId = Annotated[str, AfterValidator(ensure_tag_id)]


def ensure_worksheet_id(id: str) -> str:
    return _ensure_albert_id(id, "WorksheetId")


WorksheetId = Annotated[str, AfterValidator(ensure_worksheet_id)]


def ensure_user_id(id: str) -> str:
    return _ensure_albert_id(id, "UserId")


UserId = Annotated[str, AfterValidator(ensure_user_id)]


def ensure_unit_id(id: str) -> str:
    return _ensure_albert_id(id, "UnitId")


UnitId = Annotated[str, AfterValidator(ensure_unit_id)]


def ensure_workflow_id(id: str) -> str:
    return _ensure_albert_id(id, "WorkflowId")


WorkflowId = Annotated[str, AfterValidator(ensure_workflow_id)]


def ensure_row_id(id: str) -> str:
    return _ensure_albert_id(id, "RowId")


RowId = Annotated[str, AfterValidator(ensure_row_id)]
