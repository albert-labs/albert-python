import pytest

from albert import Albert
from albert.resources.instructions import (
    InstructionRowType,
    InstructionSequence,
    InventoryInstructions,
    SequencePosition,
)
from albert.resources.inventory import InventoryItem
from albert.resources.sheets import Sheet

pytestmark = pytest.mark.xdist_group("sheets")


def _sequence_positions(sequence: InstructionSequence, row_ids: list[str]) -> dict[str, int]:
    """Map each row ID to its index in the sequence."""
    positions = {}
    for idx, item in enumerate(sequence.sequence):
        if item.row_id in row_ids:
            positions[item.row_id] = idx
    return positions


def test_get_by_inventory_id(client: Albert, seeded_products: list[InventoryItem]):
    """Test the seeded formula's instructions come back with rows and a version."""
    formula = seeded_products[0]

    instructions = client.instructions.get_by_inventory_id(inventory_id=formula.id)

    assert isinstance(instructions, InventoryInstructions)
    assert instructions.inventory_id == formula.id
    assert instructions.version >= 1
    assert instructions.items
    assert instructions.total == len(instructions.items)
    ingredient_rows = [i for i in instructions.items if i.type == InstructionRowType.INVENTORY]
    assert ingredient_rows, "Expected at least one ingredient row in the instructions"


def test_get_sequence(client: Albert, seeded_products: list[InventoryItem]):
    """Test the seeded formula's sequence comes back ordered with a version."""
    formula = seeded_products[0]

    sequence = client.instructions.get_sequence(inventory_id=formula.id)

    assert isinstance(sequence, InstructionSequence)
    assert sequence.id == formula.id
    assert sequence.version >= 1
    assert sequence.sequence


def test_get_sequence_exclude_hidden(client: Albert, seeded_products: list[InventoryItem]):
    """Test exclude_hidden filters the sequence down to visible rows only."""
    sequence = client.instructions.get_sequence(
        inventory_id=seeded_products[0].id, exclude_hidden=True
    )

    assert all(item.is_hidden is False for item in sequence.sequence)


def test_update_sequence_moves_process_group_row(
    client: Albert,
    seeded_products: list[InventoryItem],
    seeded_sheet: Sheet,
    seeded_parameter_groups: list,
):
    """Test moving a process group row reorders the sequence and bumps the version."""
    if seeded_sheet.process_design is None:
        pytest.skip("Seeded sheet has no Process Design section")

    added_rows = []
    try:
        for pg in seeded_parameter_groups[:2]:
            added_rows.append(seeded_sheet.add_parameter_group_row(parameter_group_id=pg.id))

        formula_id = seeded_products[0].id
        design_id = seeded_sheet.process_design.id
        row_ids = [f"{design_id}#{row.row_id}" for row in added_rows]

        sequence = client.instructions.get_sequence(inventory_id=formula_id)
        positions = _sequence_positions(sequence, row_ids)
        assert set(positions) == set(row_ids), (
            "Expected the new process group rows in the sequence"
        )

        updated = client.instructions.update_sequence(
            inventory_id=formula_id,
            source_id=row_ids[1],
            reference_id=row_ids[0],
            position=SequencePosition.ABOVE,
            version=sequence.version,
        )

        assert updated.version > sequence.version
        updated_positions = _sequence_positions(updated, row_ids)
        assert updated_positions[row_ids[1]] == updated_positions[row_ids[0]] - 1

        restored = client.instructions.update_sequence(
            inventory_id=formula_id,
            source_id=row_ids[1],
            reference_id=row_ids[0],
            position=SequencePosition.BELOW,
            version=updated.version,
        )
        restored_positions = _sequence_positions(restored, row_ids)
        assert restored_positions[row_ids[1]] == restored_positions[row_ids[0]] + 1
    finally:
        for row in added_rows:
            client.session.delete(
                f"/api/v3/designs/{seeded_sheet.process_design.id}/rows",
                json=[{"rowId": row.row_id}],
            )
