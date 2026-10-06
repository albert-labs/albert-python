"""Unit tests for the InstructionsCollection pure payload and validation helpers."""

import pytest

from albert.collections.instructions import InstructionsCollection
from albert.resources.instructions import InstructionRowSequence, SequencePosition


def test_build_sequence_move_payload_wire_shape() -> None:
    """Test the move payload carries the fixed operation and attribute with caller values."""
    payload = InstructionsCollection._build_sequence_move_payload(
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
def test_build_sequence_move_payload_serializes_position_value(
    position: SequencePosition,
) -> None:
    """Test that the position enum is sent as its wire value."""
    payload = InstructionsCollection._build_sequence_move_payload(
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
def test_resolve_list_params_accepts_exactly_one_filter(kwargs, expected) -> None:
    """Test each single list filter maps to its wire parameter."""
    params = InstructionsCollection._resolve_list_params(
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
def test_resolve_list_params_rejects_zero_or_multiple_filters(kwargs) -> None:
    """Test missing or competing list filters are rejected."""
    with pytest.raises(ValueError, match="Exactly one"):
        InstructionsCollection._resolve_list_params(
            parent_id=kwargs.get("parent_id"),
            created_by=kwargs.get("created_by"),
            updated_by=kwargs.get("updated_by"),
        )


def test_build_row_sequence_payload_formula_level_bucket() -> None:
    """Test the formula-level reorder carries no row link."""
    payload = InstructionsCollection._build_row_sequence_payload(
        sequence=[InstructionRowSequence(instruction_ids=["ABI1", "ABI2"])],
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


def test_build_row_sequence_payload_row_bucket_includes_row_link() -> None:
    """Test a row reorder names its row on both sides of the change."""
    payload = InstructionsCollection._build_row_sequence_payload(
        sequence=[
            InstructionRowSequence(instruction_ids=["ABI9"]),
            InstructionRowSequence(design_row_id="DES1#ROW2", instruction_ids=["ABI1", "ABI2"]),
        ],
        design_row_id="DES1#ROW2",
        instruction_ids=["ABI2", "ABI1"],
    )

    change = payload["data"][0]
    assert change["oldValue"] == [{"designRowId": "DES1#ROW2", "rowSequence": ["ABI1", "ABI2"]}]
    assert change["newValue"] == [{"designRowId": "DES1#ROW2", "rowSequence": ["ABI2", "ABI1"]}]


def test_build_row_sequence_payload_rejects_missing_bucket() -> None:
    """Test reordering a row the formula does not have is rejected."""
    with pytest.raises(ValueError, match="No instructions found"):
        InstructionsCollection._build_row_sequence_payload(
            sequence=[InstructionRowSequence(instruction_ids=["ABI1"])],
            design_row_id="DES1#ROW2",
            instruction_ids=["ABI1"],
        )


def test_build_row_sequence_payload_rejects_non_permutation() -> None:
    """Test the new order must be exactly the row's current instructions."""
    with pytest.raises(ValueError, match="exactly the IDs"):
        InstructionsCollection._build_row_sequence_payload(
            sequence=[InstructionRowSequence(instruction_ids=["ABI1", "ABI2"])],
            design_row_id=None,
            instruction_ids=["ABI1", "ABI3"],
        )
