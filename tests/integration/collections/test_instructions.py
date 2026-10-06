import pytest

from albert import Albert
from albert.resources.instructions import (
    Instruction,
    InstructionRowType,
    InstructionSequence,
    InventoryInstructions,
    SequencePosition,
)
from albert.resources.inventory import InventoryItem
from albert.resources.sheets import Component, Sheet

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

    instructions = client.inventory.instructions.get_by_inventory_id(inventory_id=formula.id)

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

    sequence = client.inventory.instructions.get_sequence(inventory_id=formula.id)

    assert isinstance(sequence, InstructionSequence)
    assert sequence.id == formula.id
    assert sequence.version >= 1
    assert sequence.sequence


def test_get_sequence_exclude_hidden(client: Albert, seeded_products: list[InventoryItem]):
    """Test exclude_hidden filters the sequence down to visible rows only."""
    sequence = client.inventory.instructions.get_sequence(
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

        sequence = client.inventory.instructions.get_sequence(inventory_id=formula_id)
        positions = _sequence_positions(sequence, row_ids)
        assert set(positions) == set(row_ids), (
            "Expected the new process group rows in the sequence"
        )

        updated = client.inventory.instructions.update_sequence(
            inventory_id=formula_id,
            source_id=row_ids[1],
            reference_id=row_ids[0],
            position=SequencePosition.ABOVE,
            version=sequence.version,
        )

        assert updated.version > sequence.version
        updated_positions = _sequence_positions(updated, row_ids)
        assert updated_positions[row_ids[1]] == updated_positions[row_ids[0]] - 1

        restored = client.inventory.instructions.update_sequence(
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


def test_get_by_parent_ids(client: Albert, seeded_products: list[InventoryItem]):
    """Test a formula's instructions come back as a set keyed by the formula."""
    formula = seeded_products[0]

    sets = client.inventory.instructions.get_by_parent_ids(parent_ids=[formula.id])

    assert len(sets) == 1
    assert sets[0].id == formula.id
    assert isinstance(sets[0].instructions, list)


def test_instruction_crud(client: Albert, seeded_products: list[InventoryItem]):
    """Test creating, reading, renaming, reordering, and deleting instructions."""
    formula = seeded_products[0]
    instructions = client.inventory.instructions
    created_first = None
    created_second = None
    try:
        created_first = instructions.create(
            instruction=Instruction(name="Take the pH of the batch", parent_id=formula.id)
        )
        created_second = instructions.create(
            instruction=Instruction(name="Mix for 5 minutes", parent_id=formula.id)
        )
        assert created_first.id
        assert created_second.id

        fetched = instructions.get_by_id(parent_id=formula.id, id=created_first.id)
        assert fetched.name == "Take the pH of the batch"

        listed = [i.id for i in instructions.get_all(parent_id=formula.id)]
        assert created_first.id in listed
        assert created_second.id in listed

        fetched.name = "Take the pH of the batch twice"
        updated = instructions.update(instruction=fetched)
        assert updated.name == "Take the pH of the batch twice"

        reordered = instructions.update_row_sequence(
            parent_id=formula.id,
            instruction_ids=[created_second.id, created_first.id],
        )
        flat_ids = [i.id for i in reordered.instructions]
        assert flat_ids.index(created_second.id) < flat_ids.index(created_first.id)
    finally:
        for created in (created_first, created_second):
            if created and created.id:
                instructions.delete(parent_id=formula.id, id=created.id)

        remaining = instructions.get_by_parent_ids(parent_ids=[formula.id])[0]
        assert created_first is None or created_first.id not in [
            i.id for i in remaining.instructions
        ]


def test_copy_instructions(
    client: Albert,
    seed_prefix: str,
    seeded_products: list[InventoryItem],
    seeded_sheet: Sheet,
    seeded_inventory: list[InventoryItem],
):
    """Test a formula's instructions copy onto a fresh formula."""
    source = seeded_products[0]
    instructions = client.inventory.instructions
    target_column = seeded_sheet.add_formulation(
        formulation_name=f"{seed_prefix} - instructions copy target",
        components=[Component(inventory_item=seeded_inventory[0], amount=100)],
    )
    target_id = target_column.inventory_id
    created = None
    try:
        created = instructions.create(
            instruction=Instruction(name="Take the pH of the batch", parent_id=source.id)
        )

        result = instructions.copy(source_id=source.id, target_ids=[target_id])

        assert result.copied + result.skipped == 1
        if result.copied == 1:
            copied_set = instructions.get_by_parent_ids(parent_ids=[target_id])[0]
            assert [i.name for i in copied_set.instructions] == ["Take the pH of the batch"]
            for instruction in copied_set.instructions:
                instructions.delete(parent_id=target_id, id=instruction.id)
    finally:
        if created and created.id:
            instructions.delete(parent_id=source.id, id=created.id)
