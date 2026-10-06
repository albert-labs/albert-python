"""Wire-shape tests for the instructions resource models."""

from albert.resources.instructions import (
    InstructionDesignType,
    InstructionRowType,
    InstructionSequence,
    InventoryInstructions,
)

INVENTORY_INSTRUCTIONS_PAYLOAD = {
    "total": 1,
    "inventoryId": "INVMO135329-006",
    "version": 2,
    "items": [
        {
            "id": "INVA202421",
            "rowId": "ROW12",
            "rowUniqueId": "DES413126#ROW12",
            "type": "INV",
            "name": "ZR-0405T1/8 30494-89B",
            "values": [
                {"colId": "COL2", "type": "DEF", "name": "Name", "value": "ZR-0405T1/8 30494-89B"},
                {
                    "id": "INVMO135329-006",
                    "colId": "COL6",
                    "type": "INV",
                    "name": "Chocolate Cake",
                    "value": "10",
                    "minValue": "5",
                    "maxValue": "15",
                },
            ],
        },
        {
            "id": "PRM9999999",
            "rowId": "ROW7",
            "rowUniqueId": "DES413129#ROW7",
            "type": "PRM",
            "name": "Mixing time",
            "labelName": "Mixing time",
            "unitId": "UNI123",
            "unitName": "minutes",
            "category": "CAT1",
            "categoryName": "Mixing",
            "rowHierarchy": ["process", "DES413129#ROW3"],
            "values": [],
        },
    ],
}

INSTRUCTION_SEQUENCE_PAYLOAD = {
    "id": "INVMO135329-006",
    "version": 2,
    "isOverridden": True,
    "sequence": [
        {"designType": "products", "rowId": "DES413126#ROW20", "isHidden": True},
        {"designType": "process", "rowId": "DES413129#ROW42", "isHidden": False},
    ],
}


def test_inventory_instructions_wire_round_trip() -> None:
    """Test an instructions payload survives validation with aliases intact."""
    instructions = InventoryInstructions.model_validate(INVENTORY_INSTRUCTIONS_PAYLOAD)

    assert instructions.inventory_id == "INVMO135329-006"
    assert instructions.version == 2
    assert instructions.items[0].row_unique_id == "DES413126#ROW12"
    assert instructions.items[0].type == InstructionRowType.INVENTORY
    assert instructions.items[0].values[1].min_value == "5"
    assert instructions.items[1].label_name == "Mixing time"

    assert instructions.model_dump(by_alias=True, mode="json", exclude_none=True) == (
        INVENTORY_INSTRUCTIONS_PAYLOAD
    )


def test_instruction_sequence_wire_round_trip() -> None:
    """Test a sequence payload survives validation with aliases intact."""
    sequence = InstructionSequence.model_validate(INSTRUCTION_SEQUENCE_PAYLOAD)

    assert sequence.id == "INVMO135329-006"
    assert sequence.is_overridden is True
    assert sequence.sequence[1].design_type == InstructionDesignType.PROCESS
    assert sequence.sequence[0].is_hidden is True

    assert sequence.model_dump(by_alias=True, mode="json", exclude_none=True) == (
        INSTRUCTION_SEQUENCE_PAYLOAD
    )
