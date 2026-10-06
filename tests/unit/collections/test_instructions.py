"""Unit tests for the InstructionsCollection sequence-move payload builder."""

import pytest

from albert.collections.instructions import InstructionsCollection
from albert.resources.instructions import SequencePosition


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
