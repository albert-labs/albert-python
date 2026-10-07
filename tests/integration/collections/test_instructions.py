import pytest

from albert import Albert
from albert.resources.instructions import (
    BatchInstructions,
    InstructionRowType,
    InstructionSequence,
    SequencePosition,
)
from albert.resources.inventory import InventoryItem
from albert.resources.sheets import Component, Sheet
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("sheets")


def _sequence_positions(sequence: InstructionSequence, row_ids: list[str]) -> dict[str, int]:
    """Map each row ID to its index in the sequence."""
    positions = {}
    for idx, item in enumerate(sequence.rows):
        if item.row_id in row_ids:
            positions[item.row_id] = idx
    return positions


def test_get_batch_instructions(client: Albert, seeded_products: list[InventoryItem]):
    """Test the seeded formula's batching instructions come back in one read."""
    formula = seeded_products[0]

    batch = client.inventory.get_batch_instructions(id=formula.id)

    assert isinstance(batch, BatchInstructions)
    assert batch.id == formula.id
    assert batch.version >= 1
    assert batch.rows
    ingredient_rows = [row for row in batch.rows if row.type == InstructionRowType.INVENTORY]
    assert ingredient_rows, "Expected at least one ingredient row in the batching instructions"
    assert isinstance(batch.instructions, list)
    assert isinstance(batch.instruction_order, list)


def test_get_by_inventory_id_matches_nested_surface(
    client: Albert, seeded_products: list[InventoryItem]
):
    """Test the nested collection read returns the same composite batching instructions."""
    formula = seeded_products[0]

    batch = client.inventory.instructions.get_by_inventory_id(inventory_id=formula.id)

    assert isinstance(batch, BatchInstructions)
    assert batch.id == formula.id
    assert batch.version >= 1
    assert batch.rows


def test_move_stage(
    client: Albert,
    seeded_products: list[InventoryItem],
    seeded_sheet: Sheet,
    seeded_parameter_groups: list,
):
    """Test moving a procedure stage reorders the row order and bumps the version."""
    if seeded_sheet.process_design is None:
        pytest.skip("Seeded sheet has no Process Design section")

    added_rows = []
    row_ids = []
    formula_id = seeded_products[0].id
    moved = False
    try:
        for pg in seeded_parameter_groups[:2]:
            added_rows.append(seeded_sheet.add_parameter_group_row(parameter_group_id=pg.id))

        design_id = seeded_sheet.process_design.id
        row_ids = [f"{design_id}#{row.row_id}" for row in added_rows]

        version = client.inventory.get_batch_instructions(id=formula_id).version

        updated = client.inventory.move_stage(
            id=formula_id,
            stage_row_id=row_ids[1],
            reference_row_id=row_ids[0],
            position=SequencePosition.ABOVE,
            version=version,
        )
        moved = True

        assert updated.version > version
        updated_positions = _sequence_positions(updated, row_ids)
        assert set(updated_positions) == set(row_ids), (
            "Expected the new stage rows in the row order"
        )
        assert updated_positions[row_ids[1]] == updated_positions[row_ids[0]] - 1
    finally:
        if moved:
            client.inventory.move_stage(
                id=formula_id,
                stage_row_id=row_ids[1],
                reference_row_id=row_ids[0],
                position=SequencePosition.BELOW,
                version=updated.version,
            )
        for row in added_rows:
            client.session.delete(
                f"/api/v3/designs/{seeded_sheet.process_design.id}/rows",
                json=[{"rowId": row.row_id}],
            )


def test_instruction_lifecycle(client: Albert, seeded_products: list[InventoryItem]):
    """Test adding, reading, updating, reordering, and deleting instructions."""
    formula = seeded_products[0]
    instructions = client.inventory.instructions
    created_first = None
    created_second = None
    try:
        created_first = instructions.add(id=formula.id, text="Take the pH of the batch")
        created_second = instructions.add(id=formula.id, text="Mix for 5 minutes")
        assert created_first.id
        assert created_second.id

        listed = poll_until(
            lambda: [
                i.id
                for i in instructions.get_by_inventory_id(inventory_id=formula.id).instructions
            ],
            predicate=lambda ids: created_first.id in ids and created_second.id in ids,
        )
        assert created_first.id in listed
        assert created_second.id in listed

        updated = instructions.update(
            id=formula.id,
            instruction_id=created_first.id,
            text="Take the pH of the batch twice",
        )
        assert updated.name == "Take the pH of the batch twice"

        reordered = instructions.reorder(
            id=formula.id,
            instruction_ids=[created_second.id, created_first.id],
        )
        flat_ids = [i.id for i in reordered.instructions]
        assert flat_ids.index(created_second.id) < flat_ids.index(created_first.id)
    finally:
        created_ids = [c.id for c in (created_first, created_second) if c and c.id]
        for instruction_id in created_ids:
            instructions.delete(id=formula.id, instruction_id=instruction_id)

        if created_ids:
            remaining = poll_until(
                lambda: [
                    i.id
                    for i in instructions.get_by_inventory_id(inventory_id=formula.id).instructions
                ],
                predicate=lambda ids: all(i not in ids for i in created_ids),
            )
            assert all(i not in remaining for i in created_ids)


def test_get_all_by_author(client: Albert, seeded_products: list[InventoryItem]):
    """Test instructions are listed by their author's user ID."""
    formula = seeded_products[0]
    instructions = client.inventory.instructions
    created = None
    try:
        created = instructions.add(id=formula.id, text="Take the pH of the batch")
        author_id = created.created.by

        listed = poll_until(
            lambda: [i.id for i in instructions.get_all(created_by=author_id, max_items=1000)],
            predicate=lambda ids: created.id in ids,
        )
        assert created.id in listed
    finally:
        if created and created.id:
            instructions.delete(id=formula.id, instruction_id=created.id)


def test_copy_instructions(
    client: Albert,
    seed_prefix: str,
    seeded_products: list[InventoryItem],
    seeded_sheet: Sheet,
    seeded_inventory: list[InventoryItem],
):
    """Test a formula's instructions copy onto a fresh formula."""
    source = seeded_products[0]
    inventory = client.inventory
    target_column = seeded_sheet.add_formulation(
        formulation_name=f"{seed_prefix} - instructions copy target",
        components=[Component(inventory_item=seeded_inventory[0], amount=100)],
    )
    target_id = target_column.inventory_id
    created = None
    try:
        created = inventory.add_instruction(id=source.id, text="Take the pH of the batch")

        result = inventory.copy_instructions(id=source.id, target_ids=[target_id])

        assert result.copied + result.skipped == 1
        if result.copied == 1:
            copied = inventory.get_batch_instructions(id=target_id)
            assert [i.name for i in copied.instructions] == ["Take the pH of the batch"]
            for instruction in copied.instructions:
                inventory.delete_instruction(id=target_id, instruction_id=instruction.id)
    finally:
        if created and created.id:
            inventory.delete_instruction(id=source.id, instruction_id=created.id)
