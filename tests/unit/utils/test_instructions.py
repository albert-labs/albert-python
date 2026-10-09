"""Unit tests for the instruction payload and validation helpers."""

import pytest

from albert.resources.instructions import (
    Instruction,
    InstructionDesignLink,
    InstructionOrder,
    SequencePosition,
)
from albert.utils.instructions import (
    _build_instruction_create_payload,
    _build_instruction_name_patch,
    _build_instruction_row_sequence_payload,
    _build_instruction_sequence_move_payload,
    _resolve_instruction_list_params,
    _validate_instruction_for_create,
)


def test_build_instruction_sequence_move_payload_wire_shape() -> None:
    """Test the move payload carries the fixed operation and attribute with caller values."""
    payload = _build_instruction_sequence_move_payload(
        source_id="DES413129#ROW42",
        reference_id="DES413126#ROW15",
        position=SequencePosition.ABOVE,
        version=7,
    )

    assert payload == {
        "data": [
            {
                "operation": "update",
                "attribute": "sequence",
                "sourceId": "DES413129#ROW42",
                "referenceId": "DES413126#ROW15",
                "position": "above",
                "version": 7,
            }
        ]
    }


@pytest.mark.parametrize("position", [SequencePosition.ABOVE, SequencePosition.BELOW])
def test_build_instruction_sequence_move_payload_serializes_position_value(
    position: SequencePosition,
) -> None:
    """Test that the position enum is sent as its wire value."""
    payload = _build_instruction_sequence_move_payload(
        source_id="DES413129#ROW42",
        reference_id="DES413126#ROW15",
        position=position,
        version=1,
    )

    assert payload["data"][0]["position"] == position.value


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"parent_id": "INV123"}, {"parentId": "INV123"}),
        ({"created_by": "USR1"}, {"createdBy": "USR1"}),
        ({"updated_by": "USR2"}, {"updatedBy": "USR2"}),
    ],
)
def test_resolve_instruction_list_params_accepts_exactly_one_filter(kwargs, expected) -> None:
    """Test each single list filter maps to its wire parameter."""
    params = _resolve_instruction_list_params(
        parent_id=kwargs.get("parent_id"),
        created_by=kwargs.get("created_by"),
        updated_by=kwargs.get("updated_by"),
    )

    assert params == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"parent_id": "INV123", "created_by": "USR1"},
        {"parent_id": "INV123", "created_by": "USR1", "updated_by": "USR2"},
    ],
)
def test_resolve_instruction_list_params_rejects_zero_or_multiple_filters(kwargs) -> None:
    """Test missing or competing list filters are rejected."""
    with pytest.raises(ValueError, match="Exactly one"):
        _resolve_instruction_list_params(
            parent_id=kwargs.get("parent_id"),
            created_by=kwargs.get("created_by"),
            updated_by=kwargs.get("updated_by"),
        )


def test_build_instruction_create_payload_formula_level() -> None:
    """Test a formula-level create carries only the product link."""
    payload = _build_instruction_create_payload(
        instruction=Instruction(name="Take the pH", parent_id="INV123")
    )

    assert payload == {
        "name": "Take the pH",
        "parentId": "INV123",
        "Design": {"productId": "INV123"},
    }


def test_build_instruction_create_payload_pinned_includes_row_link() -> None:
    """Test a pinned create carries the row link inside the design."""
    payload = _build_instruction_create_payload(
        instruction=Instruction(
            name="Take the pH",
            parent_id="INV123",
            design=InstructionDesignLink(product_id="INV123", design_row_id="DES1#ROW2"),
        )
    )

    assert payload["Design"] == {"productId": "INV123", "designRowId": "DES1#ROW2"}


def test_build_instruction_row_sequence_payload_formula_level_bucket() -> None:
    """Test the formula-level reorder carries no row link."""
    payload = _build_instruction_row_sequence_payload(
        sequence=[InstructionOrder(instruction_ids=["ABI1", "ABI2"])],
        design_row_id=None,
        instruction_ids=["ABI2", "ABI1"],
    )

    assert payload == {
        "data": [
            {
                "operation": "update",
                "attribute": "sequence",
                "oldValue": [{"rowSequence": ["ABI1", "ABI2"]}],
                "newValue": [{"rowSequence": ["ABI2", "ABI1"]}],
            }
        ]
    }


def test_build_instruction_row_sequence_payload_row_bucket_includes_row_link() -> None:
    """Test a row reorder names its row on both sides of the change."""
    payload = _build_instruction_row_sequence_payload(
        sequence=[
            InstructionOrder(instruction_ids=["ABI9"]),
            InstructionOrder(design_row_id="DES1#ROW2", instruction_ids=["ABI1", "ABI2"]),
        ],
        design_row_id="DES1#ROW2",
        instruction_ids=["ABI2", "ABI1"],
    )

    change = payload["data"][0]
    assert change["oldValue"] == [{"designRowId": "DES1#ROW2", "rowSequence": ["ABI1", "ABI2"]}]
    assert change["newValue"] == [{"designRowId": "DES1#ROW2", "rowSequence": ["ABI2", "ABI1"]}]


def test_build_instruction_row_sequence_payload_rejects_missing_bucket() -> None:
    """Test reordering a row the formula does not have is rejected."""
    with pytest.raises(ValueError, match="No instructions found"):
        _build_instruction_row_sequence_payload(
            sequence=[InstructionOrder(instruction_ids=["ABI1"])],
            design_row_id="DES1#ROW2",
            instruction_ids=["ABI1"],
        )


def test_build_instruction_row_sequence_payload_rejects_non_permutation() -> None:
    """Test the new order must be exactly the row's current instructions."""
    with pytest.raises(ValueError, match="exactly the IDs"):
        _build_instruction_row_sequence_payload(
            sequence=[InstructionOrder(instruction_ids=["ABI1", "ABI2"])],
            design_row_id=None,
            instruction_ids=["ABI1", "ABI3"],
        )


def test_validate_instruction_for_create_accepts_matching_pin() -> None:
    """Test a pinned instruction whose product matches its parent passes."""
    _validate_instruction_for_create(
        Instruction(
            name="Take the pH",
            parent_id="INV123",
            design=InstructionDesignLink(product_id="INV123", design_row_id="DES1#ROW2"),
        )
    )


@pytest.mark.parametrize(
    "instruction",
    [
        Instruction(parent_id="INV123"),
        Instruction(name="Take the pH"),
        Instruction(
            name="Take the pH",
            parent_id="INV123",
            design=InstructionDesignLink(product_id="INV999", design_row_id="DES1#ROW2"),
        ),
    ],
)
def test_validate_instruction_for_create_rejects_invalid(instruction) -> None:
    """Test missing name, missing parent, or a mismatched pin product is rejected."""
    with pytest.raises(ValueError):
        _validate_instruction_for_create(instruction)


def test_build_instruction_name_patch_wire_shape() -> None:
    """Test a rename carries the current text as oldValue and the new text as newValue."""
    payload = _build_instruction_name_patch(
        existing=Instruction(id="ABI1", parent_id="INV123", name="Take the pH"),
        updated=Instruction(id="ABI1", parent_id="INV123", name="Take the pH twice"),
    )

    assert payload == {
        "id": "ABI1",
        "data": [
            {
                "operation": "update",
                "attribute": "name",
                "oldValue": "Take the pH",
                "newValue": "Take the pH twice",
            }
        ],
    }


def test_build_instruction_name_patch_unchanged_is_noop() -> None:
    """Test an unchanged name produces no patch."""
    assert (
        _build_instruction_name_patch(
            existing=Instruction(id="ABI1", parent_id="INV123", name="Take the pH"),
            updated=Instruction(id="ABI1", parent_id="INV123", name="Take the pH"),
        )
        is None
    )


def test_build_instruction_name_patch_unset_name_is_noop() -> None:
    """Test an instruction without an assigned name is not cleared by update."""
    assert (
        _build_instruction_name_patch(
            existing=Instruction(id="ABI1", parent_id="INV123", name="Take the pH"),
            updated=Instruction(id="ABI1", parent_id="INV123"),
        )
        is None
    )
