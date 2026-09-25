import pytest

from albert.exceptions import AlbertException
from albert.resources.sheets import Cell, CellColor, CellType, Column, Sheet

pytestmark = pytest.mark.xdist_group("sheetcolumns")


def _column_ids(sheet: Sheet) -> list[str]:
    return [col.column_id for col in sheet.columns]


def test_crud_empty_column(seeded_sheet: Sheet):
    new_col = seeded_sheet.add_blank_column(name="my cool new column")
    assert isinstance(new_col, Column)
    assert new_col.column_id.startswith("COL")

    renamed_column = new_col.rename(new_name="My renamed column")
    assert new_col.column_id == renamed_column.column_id
    assert renamed_column.name == "My renamed column"

    seeded_sheet.delete_column(column_id=new_col.column_id)


def test_bulk_column_and_row_operations(seeded_sheet: Sheet, seed_prefix: str):
    """Test bulk add/rename/hide/show/lock/delete columns and add/delete rows."""
    col_names = [f"{seed_prefix} bulk col 1", f"{seed_prefix} bulk col 2"]
    columns = seeded_sheet.add_columns(names=col_names)
    assert len(columns) == 2
    # Verify returned columns match requested order
    assert [c.name for c in columns] == col_names

    # Verify sheet columns are in left-to-right order on the sheet
    sheet_col_ids = [c.column_id for c in seeded_sheet.columns]
    idx1 = sheet_col_ids.index(columns[0].column_id)
    idx2 = sheet_col_ids.index(columns[1].column_id)
    assert idx1 < idx2, "Expected columns to be positioned in requested left-to-right order"

    try:
        columns[0].name = f"{seed_prefix} bulk col 1 renamed"
        columns[1].name = f"{seed_prefix} bulk col 2 renamed"
        seeded_sheet.rename_columns(columns=columns)
        renamed = [seeded_sheet.get_column(column_id=c.column_id).name for c in columns]
        assert renamed == [c.name for c in columns]

        seeded_sheet.hide_columns(column_ids=[c.column_id for c in columns])
        seeded_sheet.show_columns(column_ids=[c.column_id for c in columns])
        seeded_sheet.lock_columns(column_ids=[c.column_id for c in columns])
        seeded_sheet.lock_columns(column_ids=[c.column_id for c in columns], locked=False)

        rows = seeded_sheet.add_blank_rows(
            row_names=[f"{seed_prefix} bulk row 1", f"{seed_prefix} bulk row 2"]
        )
        assert len(rows) == 2
        seeded_sheet.delete_rows(
            row_ids=[r.row_id for r in rows], design_id=seeded_sheet.product_design.id
        )
    finally:
        seeded_sheet.delete_columns(column_ids=[c.column_id for c in columns])


def test_recolor_column(seeded_sheet: Sheet):
    product_design_id = seeded_sheet.product_design.id
    for col in seeded_sheet.columns:
        if col.type == CellType.LKP:
            col.recolor_cells(color=CellColor.RED)
            product_cells = [c for c in col.cells if c.design_id == product_design_id]
            assert product_cells
            for c in product_cells:
                assert c.color == CellColor.RED


def test_property_reads(seeded_sheet: Sheet):
    for col in seeded_sheet.columns:
        if col.type == "Formula":
            break
    for c in col.cells:
        assert isinstance(c, Cell)

    assert isinstance(col.df_name, str)


def test_lock_column(seeded_sheet: Sheet):
    for col in seeded_sheet.columns:
        if col.type == CellType.INVENTORY:
            curr_state = bool(col.locked)
            toggle_col = seeded_sheet.lock_column(locked=not curr_state, column_id=col.column_id)

            assert toggle_col.locked is not curr_state
            assert toggle_col.column_id == col.column_id

            # Restore to original state
            seeded_sheet.lock_column(locked=curr_state, column_id=col.column_id)
            break


def test_reorder_columns_basic(seeded_sheet: Sheet):
    """Test reordering newly added blank columns and restoring the original order."""
    seeded_sheet.grid = None
    col_a = seeded_sheet.add_blank_column(name="reorder test A")
    col_b = seeded_sheet.add_blank_column(name="reorder test B")
    col_c = seeded_sheet.add_blank_column(name="reorder test C")
    original_order = _column_ids(seeded_sheet)
    try:
        assert original_order[-3:] == [col_a.column_id, col_b.column_id, col_c.column_id]
        desired = original_order[:-3] + [
            col_c.column_id,
            col_b.column_id,
            col_a.column_id,
        ]
        seeded_sheet.reorder_columns(column_ids=desired)
        assert _column_ids(seeded_sheet) == desired

        seeded_sheet.reorder_columns(column_ids=original_order)
        assert _column_ids(seeded_sheet) == original_order
    finally:
        for col in (col_a, col_b, col_c):
            seeded_sheet.delete_column(column_id=col.column_id)
        seeded_sheet.grid = None


def test_reorder_columns_noop(seeded_sheet: Sheet):
    """Test that passing the current order is a no-op."""
    seeded_sheet.grid = None
    current = _column_ids(seeded_sheet)
    seeded_sheet.reorder_columns(column_ids=current)
    assert _column_ids(seeded_sheet) == current


def test_reorder_columns_validation(seeded_sheet: Sheet):
    """Test reorder_columns rejects invalid column ID lists."""
    seeded_sheet.grid = None
    current = _column_ids(seeded_sheet)

    with pytest.raises(AlbertException, match="must not contain duplicates"):
        seeded_sheet.reorder_columns(column_ids=[current[0], current[0]])

    with pytest.raises(AlbertException, match="Unknown column ID"):
        seeded_sheet.reorder_columns(column_ids=[*current, "COL999999999"])

    with pytest.raises(AlbertException, match="must include every column"):
        seeded_sheet.reorder_columns(column_ids=current[:-1])

    with pytest.raises(AlbertException, match="must include at least one"):
        seeded_sheet.reorder_columns(column_ids=[])


def test_reorder_columns_with_pinned_column(seeded_sheet: Sheet):
    """Test reordering column sequence when a left-pinned column is present."""
    seeded_sheet.grid = None
    col_a = seeded_sheet.add_blank_column(name="reorder pin A")
    col_b = seeded_sheet.add_blank_column(name="reorder pin B")
    col_c = seeded_sheet.add_blank_column(name="reorder pin C")
    original_order = _column_ids(seeded_sheet)
    try:
        seeded_sheet.pin_columns(col_ids=[col_a.column_id], side="left")
        seeded_sheet.grid = None

        desired = original_order[:-3] + [
            col_a.column_id,
            col_c.column_id,
            col_b.column_id,
        ]
        seeded_sheet.reorder_columns(column_ids=desired)
        assert _column_ids(seeded_sheet) == desired
    finally:
        seeded_sheet.reorder_columns(column_ids=original_order)
        seeded_sheet.unpin_columns(col_ids=[col_a.column_id])
        for col in (col_a, col_b, col_c):
            seeded_sheet.delete_column(column_id=col.column_id)
        seeded_sheet.grid = None
