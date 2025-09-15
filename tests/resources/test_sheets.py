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


def test_formulation_column_names_use_display_name(seeded_sheet: Sheet):
    mapping = {f.id: f.name for f in seeded_sheet.formulations}
    matched = False
    for col in seeded_sheet.columns:
        if col.inventory_id in mapping:
            matched = True
            assert col.name == mapping[col.inventory_id]
    assert matched, "No formulation columns found"


def test_add_formulation(seed_prefix: str, seeded_sheet: Sheet, seeded_inventory, seeded_products):
    components_updated = [
        Component(inventory_item=seeded_inventory[0], amount=33.1, min_value=0, max_value=50),
        Component(inventory_item=seeded_inventory[1], amount=66.9, min_value=50, max_value=100),
    ]

    new_col = seeded_sheet.add_formulation(
        formulation_name=f"{seed_prefix} - My cool formulation base",
        components=components_updated,
        enforce_order=True,
    )
    assert isinstance(new_col, Column)

    component_map = {c.inventory_item.id: c for c in components_updated}
    row_id_to_inv_id = {row.row_id: row.inventory_id for row in seeded_sheet.product_design.rows}

    found_cells = 0
    for cell in new_col.cells:
        if cell.type == "INV" and cell.row_type == "INV":
            inv_id = row_id_to_inv_id.get(cell.row_id)
            if not inv_id or inv_id not in component_map:
                continue

            component = component_map[inv_id]
            assert float(cell.value) == float(component.amount)
            assert float(cell.min_value) == float(component.min_value)
            assert float(cell.max_value) == float(component.max_value)
            found_cells += 1
        elif cell.row_type == "TOT":
            assert cell.value == "100"

    assert found_cells == len(components_updated)


def test_add_formulation_clear_updates_existing(
    seed_prefix: str, seeded_sheet: Sheet, seeded_inventory
):
    name = f"{seed_prefix} - Clear existing"
    initial = [
        Component(inventory_item=seeded_inventory[0], amount=60),
        Component(inventory_item=seeded_inventory[1], amount=40),
    ]
    updated = [
        Component(inventory_item=seeded_inventory[0], amount=20),
        Component(inventory_item=seeded_inventory[1], amount=80),
    ]

    col1 = seeded_sheet.add_formulation(formulation_name=name, components=initial)
    col2 = seeded_sheet.add_formulation(formulation_name=name, components=updated, clear=True)
    assert col1.column_id == col2.column_id
    values = [c.value for c in col2.cells if c.type == "INV" and c.row_type == "INV"]
    assert sorted(values) == ["20", "80"]


def test_add_formulation_no_clear_adds_new_column(
    seed_prefix: str, seeded_sheet: Sheet, seeded_inventory
):
    name = f"{seed_prefix} - No clear"
    components = [
        Component(inventory_item=seeded_inventory[0], amount=50),
        Component(inventory_item=seeded_inventory[1], amount=50),
    ]

    col1 = seeded_sheet.add_formulation(formulation_name=name, components=components)
    col2 = seeded_sheet.add_formulation(formulation_name=name, components=components, clear=False)
    assert col1.column_id != col2.column_id


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
    assert cell.min_value is None
    assert cell.max_value is None
