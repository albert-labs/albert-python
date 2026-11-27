"""Wire-shape tests for the instructions resource models."""

from albert.resources.instructions import (
    Instruction,
    InstructionCopyResult,
    InstructionDesignType,
    InstructionLayout,
    InstructionRowType,
    InstructionSequence,
    InstructionSet,
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
    instructions = InstructionLayout.model_validate(INVENTORY_INSTRUCTIONS_PAYLOAD)

    assert instructions.inventory_id == "INVMO135329-006"
    assert instructions.version == 2
    assert instructions.rows[0].row_unique_id == "DES413126#ROW12"
    assert instructions.rows[0].type == InstructionRowType.INVENTORY
    assert instructions.rows[0].values[1].min_value == "5"
    assert instructions.rows[1].label_name == "Mixing time"

    assert instructions.model_dump(by_alias=True, mode="json", exclude_none=True) == (
        INVENTORY_INSTRUCTIONS_PAYLOAD
    )


def test_instruction_sequence_wire_round_trip() -> None:
    """Test a sequence payload survives validation with aliases intact."""
    sequence = InstructionSequence.model_validate(INSTRUCTION_SEQUENCE_PAYLOAD)

    assert sequence.id == "INVMO135329-006"
    assert sequence.is_overridden is True
    assert sequence.rows[1].design_type == InstructionDesignType.PROCESS
    assert sequence.rows[0].is_hidden is True

    assert sequence.model_dump(by_alias=True, mode="json", exclude_none=True) == (
        INSTRUCTION_SEQUENCE_PAYLOAD
    )


INSTRUCTION_PAYLOAD = {
    "albertId": "ABI1234567",
    "name": "Take the pH of the batch",
    "parentId": "INVMO135329-006",
    "status": "active",
    "Design": {
        "productId": "INVMO135329-006",
        "designRowId": "DES413126#ROW12",
        "designInvId": "INVA202421",
    },
    "Created": {"by": "USR1", "byName": "Ada Lovelace", "at": "2026-01-01T00:00:00Z"},
    "Updated": {"by": "USR1", "byName": "Ada Lovelace", "at": "2026-01-02T00:00:00Z"},
}

INSTRUCTION_SET_PAYLOAD = {
    "id": "INVMO135329-006",
    "parentId": "INVMO135329-006",
    "data": [
        {
            "albertId": "ABI1234567",
            "name": "Take the pH of the batch",
            "parentId": "INVMO135329-006",
        }
    ],
    "sequence": [
        {"designRowId": None, "rowSequence": ["ABI1234567"]},
        {"designRowId": "DES413126#ROW12", "rowSequence": []},
    ],
}


def test_instruction_wire_round_trip() -> None:
    """Test an instruction payload survives validation with aliases intact."""
    instruction = Instruction.model_validate(INSTRUCTION_PAYLOAD)

    assert instruction.id == "ABI1234567"
    assert instruction.parent_id == "INVMO135329-006"
    assert instruction.design.design_row_id == "DES413126#ROW12"
    assert instruction.design.design_inv_id == "INVA202421"
    assert instruction.created.by_name == "Ada Lovelace"

    assert instruction.model_dump(by_alias=True, mode="json", exclude_none=True) == (
        INSTRUCTION_PAYLOAD
    )


def test_instruction_set_wire_round_trip() -> None:
    """Test a formula's instruction set survives validation with aliases intact."""
    instruction_set = InstructionSet.model_validate(INSTRUCTION_SET_PAYLOAD)

    assert instruction_set.id == "INVMO135329-006"
    assert instruction_set.instructions[0].id == "ABI1234567"
    assert instruction_set.sequence[0].instruction_ids == ["ABI1234567"]
    assert instruction_set.sequence[1].design_row_id == "DES413126#ROW12"

    dumped = instruction_set.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["data"][0]["albertId"] == "ABI1234567"
    assert dumped["sequence"][0]["rowSequence"] == ["ABI1234567"]
    assert dumped["sequence"][1]["designRowId"] == "DES413126#ROW12"


def test_instruction_copy_result_round_trip() -> None:
    """Test a copy outcome deserializes its counts."""
    result = InstructionCopyResult.model_validate({"copied": 2, "skipped": 1})

    assert result.copied == 2
    assert result.skipped == 1
