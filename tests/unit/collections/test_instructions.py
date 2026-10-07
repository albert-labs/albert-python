"""Unit tests for the instructions surface: pure helpers and collection wiring."""

import pytest

from albert.collections.instructions import InstructionsCollection, InventoryInstructionsMixin
from albert.collections.inventory import InventoryCollection
from albert.resources.instructions import InstructionOrder, SequencePosition

MIXIN_METHODS = (
    "get_batch_instructions",
    "add_instruction",
    "update_instruction",
    "delete_instruction",
    "reorder_instructions",
    "copy_instructions",
    "move_stage",
)

NESTED_METHODS = (
    "get_by_inventory_id",
    "get_all",
    "add",
    "update",
    "delete",
    "reorder",
    "copy",
    "move_stage",
)


def test_instruction_methods_available_on_inventory_collection() -> None:
    """Test the instruction actions are mixed into the inventory collection."""
    for name in MIXIN_METHODS:
        assert hasattr(InventoryCollection, name)


def test_short_names_available_on_nested_collection() -> None:
    """Test the nested instructions collection exposes short action names."""
    for name in NESTED_METHODS:
        assert hasattr(InstructionsCollection, name)


def test_build_stage_move_payload_wire_shape() -> None:
    """Test the move details carry the fixed operation and attribute with caller values."""
    payload = InventoryInstructionsMixin._build_stage_move_payload(
        stage_row_id="DES413129#ROW42",
        reference_row_id="DES413126#ROW15",
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
def test_build_stage_move_payload_serializes_position_value(
    position: SequencePosition,
) -> None:
    """Test that the position enum is sent as its wire value."""
    payload = InventoryInstructionsMixin._build_stage_move_payload(
        stage_row_id="DES413129#ROW42",
        reference_row_id="DES413126#ROW15",
        position=position,
        version=1,
    )

    assert payload["data"][0]["position"] == position.value


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"created_by": "USR1"}, {"createdBy": "USR1"}),
        ({"updated_by": "USR2"}, {"updatedBy": "USR2"}),
    ],
)
def test_resolve_list_params_accepts_exactly_one_filter(kwargs, expected) -> None:
    """Test each single list filter maps to its wire parameter."""
    params = InstructionsCollection._resolve_list_params(
        created_by=kwargs.get("created_by"),
        updated_by=kwargs.get("updated_by"),
    )

    assert params == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"created_by": "USR1", "updated_by": "USR2"},
    ],
)
def test_resolve_list_params_rejects_zero_or_multiple_filters(kwargs) -> None:
    """Test missing or competing list filters are rejected."""
    with pytest.raises(ValueError, match="Exactly one"):
        InstructionsCollection._resolve_list_params(
            created_by=kwargs.get("created_by"),
            updated_by=kwargs.get("updated_by"),
        )


def test_build_create_payload_links_formula_and_text() -> None:
    """Test a formula-level instruction carries the formula ID as parent and product."""
    payload = InventoryInstructionsMixin._build_create_payload(
        id="INV123", text="Take the pH", design_row_id=None
    )

    assert payload == {
        "name": "Take the pH",
        "parentId": "INV123",
        "Design": {"productId": "INV123"},
    }


def test_build_create_payload_pinned_includes_row_link() -> None:
    """Test a pinned instruction names its ingredient row."""
    payload = InventoryInstructionsMixin._build_create_payload(
        id="INV123", text="Take the pH", design_row_id="DES1#ROW2"
    )

    assert payload["Design"] == {"productId": "INV123", "designRowId": "DES1#ROW2"}


def test_build_create_payload_rejects_empty_text() -> None:
    """Test an instruction without text is rejected."""
    with pytest.raises(ValueError, match="text is required"):
        InventoryInstructionsMixin._build_create_payload(id="INV123", text="", design_row_id=None)


def test_build_instruction_order_payload_formula_level_bucket() -> None:
    """Test the formula-level reorder carries no row link."""
    payload = InventoryInstructionsMixin._build_instruction_order_payload(
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


def test_build_instruction_order_payload_row_bucket_includes_row_link() -> None:
    """Test a row reorder names its row on both sides of the change."""
    payload = InventoryInstructionsMixin._build_instruction_order_payload(
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


def test_build_instruction_order_payload_rejects_missing_bucket() -> None:
    """Test reordering a row the formula does not have is rejected."""
    with pytest.raises(ValueError, match="No instructions found"):
        InventoryInstructionsMixin._build_instruction_order_payload(
            sequence=[InstructionOrder(instruction_ids=["ABI1"])],
            design_row_id="DES1#ROW2",
            instruction_ids=["ABI1"],
        )


def test_build_instruction_order_payload_rejects_non_permutation() -> None:
    """Test the new order must be exactly the row's current instructions."""
    with pytest.raises(ValueError, match="exactly the IDs"):
        InventoryInstructionsMixin._build_instruction_order_payload(
            sequence=[InstructionOrder(instruction_ids=["ABI1", "ABI2"])],
            design_row_id=None,
            instruction_ids=["ABI1", "ABI3"],
        )


def test_build_update_patch_wire_shape() -> None:
    """Test a text update carries the current text as oldValue and the new text as newValue."""
    patch = InventoryInstructionsMixin._build_update_patch(
        instruction_id="ABI1",
        old_text="Take the pH",
        new_text="Take the pH twice",
    )

    assert patch == {
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


def test_build_update_patch_unchanged_is_noop() -> None:
    """Test an unchanged text produces no update."""
    assert (
        InventoryInstructionsMixin._build_update_patch(
            instruction_id="ABI1",
            old_text="Take the pH",
            new_text="Take the pH",
        )
        is None
    )
