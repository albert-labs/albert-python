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
        unlocked = seeded_sheet.lock_column(column_id=columns[0].column_id, locked=False)
        assert unlocked.column_id == columns[0].column_id
        assert unlocked.locked is False
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
            break


def test_property_reads(seeded_sheet: Sheet):
    for col in seeded_sheet.columns:
        if col.type == "Formula":
            break
    for c in col.cells:
        assert isinstance(c, Cell)

    assert isinstance(col.df_name, str)


def test_reorder_columns(seeded_sheet: Sheet, seed_prefix: str):
    """Test reordering columns, then reordering again with a left-pinned column."""
    cols = seeded_sheet.add_columns(names=[f"{seed_prefix} reorder {x}" for x in "ABC"])
    col_a, col_b, col_c = (c.column_id for c in cols)
    pinned = False
    try:
        original_order = _column_ids(seeded_sheet)
        assert original_order[-3:] == [col_a, col_b, col_c]

        desired = original_order[:-3] + [col_c, col_b, col_a]
        seeded_sheet.reorder_columns(column_ids=desired)
        assert _column_ids(seeded_sheet) == desired

        seeded_sheet.pin_columns(col_ids=[col_a], side="left")
        pinned = True
        desired = original_order[:-3] + [col_a, col_c, col_b]
        seeded_sheet.reorder_columns(column_ids=desired)
        assert _column_ids(seeded_sheet) == desired
    finally:
        if pinned:
            seeded_sheet.unpin_columns(col_ids=[col_a])
        seeded_sheet.delete_columns(column_ids=[col_a, col_b, col_c])
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
