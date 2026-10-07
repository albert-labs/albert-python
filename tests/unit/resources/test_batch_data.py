"""Unit tests for the wire format of ``albert.resources.batch_data`` models."""

import pytest

from albert.resources.batch_data import (
    BatchDataLotUsage,
    BatchDataRowCreated,
    ReactionBatchData,
    ReactionLotPick,
    ReactionValueId,
    ReactionValuePatchDatum,
    ReactionValuePatchPayload,
)

REACTION_GRID_PAYLOAD = {
    "taskId": "TASLAB4410",
    "state": "In Progress",
    "locked": False,
    "Project": {"projectId": "PROMO137214", "projectName": "Molecule demo"},
    "Reactions": [
        {
            "id": "RXN1826",
            "name": "RXN1826",
            "Reagents": [
                {
                    "sttId": "STT1f13",
                    "name": "Ethanol",
                    "function": "solvent",
                    "isLimitingReagent": False,
                    "eq": "2.0",
                    "mw": 46.07,
                    "purity": 0.99,
                    "totalAmt": 5.0,
                    "unit": "g",
                    "totalUsed": 2.5,
                    "smiles": "CCO",
                    "imageUrl": "https://example.com/cco.png",
                    "Lot": {
                        "lotId": "LOT98231",
                        "albertId": "LOT98231",
                        "inventoryId": "INVMO137265-001",
                        "substanceId": "STT1f13",
                        "amt": 2.5,
                        "unit": "g",
                        "inventoryOnHand": 12.5,
                        "Location": {"id": "LOC1", "name": "Lab"},
                    },
                }
            ],
            "Products": [
                {
                    "sttId": "STT2a44",
                    "name": "Product A",
                    "subId": "sub-1",
                    "mw": 120.15,
                    "actual": 1.25,
                    "totalAmt": 2.0,
                    "unit": "g",
                    "smiles": "CC=O",
                    "imageUrl": None,
                }
            ],
        }
    ],
}


def test_reaction_batch_data_parses_grid_payload():
    """Test that a full reaction grid payload parses into nested models."""
    grid = ReactionBatchData.model_validate(REACTION_GRID_PAYLOAD)

    assert grid.task_id == "TASLAB4410"
    assert grid.state == "In Progress"
    assert grid.locked is False
    assert grid.project.project_id == "PROMO137214"
    assert grid.project.project_name == "Molecule demo"

    reaction = grid.reactions[0]
    assert reaction.id == "RXN1826"

    reagent = reaction.reagents[0]
    assert reagent.stt_id == "STT1f13"
    assert reagent.function == "solvent"
    assert reagent.is_limiting_reagent is False
    assert reagent.total_amt == pytest.approx(5.0)
    assert reagent.total_used == pytest.approx(2.5)

    lot = reagent.lot
    assert lot.lot_id == "LOT98231"
    assert lot.amt == pytest.approx(2.5)
    assert lot.inventory_on_hand == pytest.approx(12.5)

    product = reaction.products[0]
    assert product.sub_id == "sub-1"
    assert product.actual == pytest.approx(1.25)


def test_reaction_batch_data_tolerates_empty_snapshot():
    """Test that a task with no reaction snapshot parses with empty reactions."""
    grid = ReactionBatchData.model_validate(
        {"taskId": "TASLAB4410", "state": None, "locked": False, "Reactions": []}
    )

    assert grid.reactions == []
    assert grid.state is None
    assert grid.project is None


def test_reaction_reagent_without_lot_parses():
    """Test that an unpicked reagent parses with no lot."""
    grid = ReactionBatchData.model_validate(
        {
            "taskId": "TASLAB4410",
            "Reactions": [
                {
                    "id": "RXN1826",
                    "Reagents": [
                        {"sttId": "STT1f13", "name": "Ethanol", "totalUsed": 0, "unit": "g"}
                    ],
                    "Products": [],
                }
            ],
        }
    )

    assert grid.reactions[0].reagents[0].lot is None


def test_reaction_value_patch_payload_lot_pick_wire_format():
    """Test that a lot pick serializes to the nested camelCase wire shape."""
    patch = ReactionValuePatchPayload(
        id=ReactionValueId(reaction_id="RXN1826", stt_id="STT1f13"),
        data=[
            ReactionValuePatchDatum(
                operation="add",
                attribute="lot",
                new_value=ReactionLotPick(lot_id="LOT98231", amt=2.5, unit="g"),
            )
        ],
    )

    dumped = patch.model_dump(by_alias=True, mode="json", exclude_none=True)

    assert dumped == {
        "Id": {"reactionId": "RXN1826", "sttId": "STT1f13"},
        "data": [
            {
                "operation": "add",
                "attribute": "lot",
                "newValue": {"lotId": "LOT98231", "amt": 2.5, "unit": "g"},
            }
        ],
    }


@pytest.mark.parametrize(
    ("attribute", "new_value", "expected"),
    [
        pytest.param("amt", 3.0, 3.0, id="amt-number"),
        pytest.param("actual", 0.0, 0.0, id="actual-zero"),
        pytest.param("subId", "sub-1", "sub-1", id="subid-string"),
    ],
)
def test_reaction_value_patch_datum_update_wire_format(attribute, new_value, expected):
    """Test that update changes keep their scalar new value on the wire."""
    datum = ReactionValuePatchDatum(operation="update", attribute=attribute, new_value=new_value)

    dumped = datum.model_dump(by_alias=True, mode="json", exclude_none=True)

    assert dumped == {"operation": "update", "attribute": attribute, "newValue": expected}


def test_reaction_value_patch_datum_delete_omits_new_value():
    """Test that a delete change sends no new value."""
    datum = ReactionValuePatchDatum(operation="delete", attribute="lot")

    dumped = datum.model_dump(by_alias=True, mode="json", exclude_none=True)

    assert dumped == {"operation": "delete", "attribute": "lot"}


def test_batch_data_row_created_parses_added_row():
    """Test that an added design row parses, including the BTD task reference."""
    created = BatchDataRowCreated.model_validate(
        {
            "taskId": "BTD#TASLAB100",
            "Design": {"id": "DES100", "rowId": "ROW2", "colId": "COL4"},
            "rowId": "ROW101",
            "inventoryId": "INVMO101-002",
        }
    )

    assert created.task_id == "BTD#TASLAB100"
    assert created.design.id == "DES100"
    assert created.design.row_id == "ROW2"
    assert created.row_id == "ROW101"
    assert created.inventory_id == "INVMO101-002"


def test_batch_data_lot_usage_parses_item():
    """Test that a lot usage item parses its nested product."""
    usage = BatchDataLotUsage.model_validate(
        {"parentId": "TASLAB100", "Product": {"id": "INVMO101-001", "lotId": "LOT98231"}}
    )

    assert usage.task_id == "TASLAB100"
    assert usage.product.id == "INVMO101-001"
    assert usage.product.lot_id == "LOT98231"


def test_batch_data_lot_usage_tolerates_missing_lot_id():
    """Test that a product reference without a lot pick parses."""
    usage = BatchDataLotUsage.model_validate(
        {"parentId": "TASLAB100", "Product": {"id": "INVMO101-001"}}
    )

    assert usage.product.lot_id is None
