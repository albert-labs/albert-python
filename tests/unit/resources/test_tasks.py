"""Offline tests for task resource wire shapes."""

import pytest
from pydantic import ValidationError

from albert.resources.tasks import (
    BatchTask,
    GeneralTask,
    PropertyTask,
    ReactionBatchTask,
    ReactionUnitOverride,
    TaskAdapter,
    TaskCategory,
)

# Mirrors GET /api/v3/tasks/multi/{id} for a reaction batch task (api-task
# getMultiTaskById.js: reaction fields, hydrated output-lot inventory rows).
REACTION_BATCH_TASK_PAYLOAD = {
    "albertId": "TASREA123",
    "name": "Reaction batch task",
    "category": "ReactionBatch",
    "parentId": "PROMO136511",
    "Metadata": {},
    "state": "Unclaimed",
    "class": "private",
    "priority": "Low",
    "reactionId": "RXN1826",
    "reactionName": "Suzuki coupling",
    "worksheetId": "WKS123456",
    "reagentsDesignId": "DES44101",
    "productsDesignId": "DES44102",
    "inventoryId": "INVMO137265-003",
    "defaultUnit": "kg",
    "Units": [{"sttId": "STT1f13", "unit": "g"}],
    "Inventories": [
        {
            "id": "INVMO137265-003",
            "lotId": "LOT116285",
            "lotNumber": "12323-23232",
            "batchSize": 0.5,
            "inventoryOnHand": 1.5,
            "parentUnit": "mass",
            "Location": {"id": "LOC1", "name": "Warehouse"},
        }
    ],
    "Project": {"id": "PROMO136511"},
    "Location": {"id": "LOC1"},
    "Tags": [],
}


def test_task_adapter_parses_reaction_batch_task():
    """Test a ReactionBatch task payload parses into ReactionBatchTask with reaction fields."""
    task = TaskAdapter.validate_python(REACTION_BATCH_TASK_PAYLOAD)

    assert isinstance(task, ReactionBatchTask)
    assert task.category == TaskCategory.REACTION_BATCH
    assert task.reaction_id == "RXN1826"
    assert task.reaction_name == "Suzuki coupling"
    assert task.worksheet_id == "WKS123456"
    assert task.reagents_design_id == "DES44101"
    assert task.products_design_id == "DES44102"
    assert task.inventory_id == "INVMO137265-003"
    assert task.default_unit == "kg"
    assert task.units == [ReactionUnitOverride(stt_id="STT1f13", unit="g")]


def test_reaction_batch_task_output_lot_fields_parse():
    """Test hydrated output-lot fields on the inventory rows are kept."""
    task = TaskAdapter.validate_python(REACTION_BATCH_TASK_PAYLOAD)

    row = task.inventory_information[0]
    assert row.inventory_on_hand == 1.5
    assert row.parent_unit == "mass"
    assert row.location.id == "LOC1"
    assert row.location.name == "Warehouse"


def test_reaction_batch_task_sparse_payload_parses():
    """Test a reaction batch task with only required fields parses."""
    task = TaskAdapter.validate_python(
        {"albertId": "TASREA124", "name": "Minimal", "category": "ReactionBatch"}
    )

    assert isinstance(task, ReactionBatchTask)
    assert task.reaction_id is None
    assert task.units is None
    assert task.inventory_information is None


def test_reaction_batch_task_is_a_batch_task():
    """Test ReactionBatchTask stays a BatchTask for isinstance checks by callers."""
    task = TaskAdapter.validate_python(REACTION_BATCH_TASK_PAYLOAD)

    assert isinstance(task, BatchTask)


def test_existing_task_categories_still_parse():
    """Test the existing union members are unaffected by the new category."""
    assert isinstance(
        TaskAdapter.validate_python({"name": "p", "category": "Property"}), PropertyTask
    )
    assert isinstance(TaskAdapter.validate_python({"name": "b", "category": "Batch"}), BatchTask)
    assert not isinstance(
        TaskAdapter.validate_python({"name": "b", "category": "Batch"}), ReactionBatchTask
    )
    assert isinstance(
        TaskAdapter.validate_python({"name": "g", "category": "General"}), GeneralTask
    )


def test_unknown_task_category_still_rejected():
    """Test an unrecognized category fails validation instead of guessing a type."""
    with pytest.raises(ValidationError):
        TaskAdapter.validate_python({"name": "x", "category": "NotARealCategory"})


def test_reaction_read_only_fields_excluded_from_dump():
    """Test reaction and output-lot fields never serialize into create or patch payloads."""
    task = TaskAdapter.validate_python(REACTION_BATCH_TASK_PAYLOAD)

    dumped = task.model_dump(mode="json", by_alias=True, exclude_none=True)
    for key in (
        "reactionId",
        "reactionName",
        "worksheetId",
        "reagentsDesignId",
        "productsDesignId",
        "inventoryId",
        "defaultUnit",
        "Units",
    ):
        assert key not in dumped
    row_dump = task.inventory_information[0].model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    assert "inventoryOnHand" not in row_dump
    assert "parentUnit" not in row_dump
    assert "Location" not in row_dump
