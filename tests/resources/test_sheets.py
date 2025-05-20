import pandas as pd
import pytest

from albert.exceptions import AlbertException
from albert.resources.sheets import (
    Cell,
    CellColor,
    CellType,
    Column,
    Component,
    DesignType,
    Row,
    Sheet,
)


def test_get_test_sheet(seeded_sheet: Sheet):
    assert isinstance(seeded_sheet, Sheet)
    seeded_sheet.rename(new_name="test renamed")
    assert seeded_sheet.name == "test renamed"
    seeded_sheet.rename(new_name="test")
    assert seeded_sheet.name == "test"
    assert isinstance(seeded_sheet.grid, pd.DataFrame)


def test_crud_empty_column(seeded_sheet: Sheet):
    new_col = seeded_sheet.add_blank_column(name="my cool new column")
    assert isinstance(new_col, Column)
    assert new_col.column_id.startswith("COL")

    renamed_column = new_col.rename(new_name="My renamed column")
    assert new_col.column_id == renamed_column.column_id
    assert renamed_column.name == "My renamed column"

    seeded_sheet.delete_column(column_id=new_col.column_id)


def test_add_formulation(seed_prefix: str, seeded_sheet: Sheet, seeded_inventory, seeded_products):
    components_updated = [
        Component(inventory_item=seeded_inventory[0], amount=33),
        Component(inventory_item=seeded_inventory[1], amount=67),
    ]

    new_col = seeded_sheet.add_formulation(
        formulation_name=f"{seed_prefix} - My cool formulation base",
        components=components_updated,
        enforce_order=True,
    )
    assert isinstance(new_col, Column)

    for cell in new_col.cells:
        if cell.type == "INV":
            assert cell.value in ["33", "67"]
        elif cell.type == "TOT":
            assert cell.value == "100"


########################## COLUMNS ##########################


def test_recolor_column(seeded_sheet: Sheet):
    for col in seeded_sheet.columns:
        if col.type == CellType.LKP:
            col.recolor_cells(color=CellColor.RED)
            for c in col.cells:
                assert c.color == CellColor.RED


def test_property_reads(seeded_sheet: Sheet):
    for col in seeded_sheet.columns:
        if col.type == "Formula":
            break
    for c in col.cells:
        assert isinstance(c, Cell)

    assert isinstance(col.df_name, str)


# Because you cannot delete Formulation Columns, We will need to mock this test.
# def test_crud_formulation_column(sheet):
#     new_col = sheet.add_formulation_columns(formulation_names=["my cool formulation"])[0]


def test_recolor_rows(seeded_sheet: Sheet):
    for row in seeded_sheet.rows:
        if row.type == CellType.BLANK:
            row.recolor_cells(color=CellColor.RED)
            for c in row.cells:
                assert c.color == CellColor.RED


def test_add_and_remove_blank_rows(seeded_sheet: Sheet):
    new_row = seeded_sheet.add_blank_row(row_name="TEST app Design", design=DesignType.APPS)
    assert isinstance(new_row, Row)
    seeded_sheet.delete_row(row_id=new_row.row_id, design_id=seeded_sheet.app_design.id)

    new_row = seeded_sheet.add_blank_row(
        row_name="TEST products Design", design=DesignType.PRODUCTS
    )
    assert isinstance(new_row, Row)
    seeded_sheet.delete_row(row_id=new_row.row_id, design_id=seeded_sheet.product_design.id)

    # You cannot add a blank row to results design
    with pytest.raises(AlbertException):
        new_row = seeded_sheet.add_blank_row(
            row_name="TEST results Design", design=DesignType.RESULTS
        )


########################## CELLS ##########################


def test_get_cell_value():
    cell = Cell(
        column_id="TEST_COL1",
        row_id="TEST_ROW1",
        type=CellType.BLANK,
        design_id="TEST_DESIGN1",
        value="test",
    )
    assert cell.raw_value == "test"
    assert cell.color is None
