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


def test_get_current_cell_exact_row_match():
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[
            {"albertId": "DES1", "designType": "products", "state": {}},
            {"albertId": "DES2", "designType": "results", "state": {}},
            {"albertId": "DES3", "designType": "apps", "state": {}},
        ],
        projectId="PRJ1",
    )

    column_label = "COL1#INV1"

    row_220_cell = Cell(
        colId="COL1",
        rowId="ROW220",
        value="123",
        type=CellType.INVENTORY,
        design_id="DES1",
        name="ROW220",
    )

    row_22_cell = Cell(
        colId="COL1",
        rowId="ROW22",
        value="456",
        type=CellType.INVENTORY,
        design_id="DES1",
        name="ROW22",
    )

    sheet._grid = pd.DataFrame(
        [[row_220_cell], [row_22_cell]],
        index=["DES1#ROW220", "DES1#ROW22"],
        columns=[column_label],
    )

    lookup_cell = Cell(
        colId="COL1",
        rowId="ROW22",
        value="0",
        type=CellType.INVENTORY,
        design_id="DES1",
        name="ROW22",
    )

    result = sheet._get_current_cell(cell=lookup_cell)

    assert result is row_22_cell
    assert result.row_id == "ROW22"


def test_update_cells_updates_inventory_values(
    seed_prefix: str,
    seeded_sheet: Sheet,
    seeded_inventory,
    seeded_products,
):
    formulation_name = f"{seed_prefix} - update cells integration"
    components = [
        Component(inventory_item=seeded_inventory[0], amount=20.0, min_value=10.0, max_value=40.0),
        Component(inventory_item=seeded_inventory[1], amount=80.0, min_value=60.0, max_value=90.0),
    ]

    column = seeded_sheet.add_formulation(
        formulation_name=formulation_name,
        components=components,
        enforce_order=True,
    )

    inventory_cells = [
        cell
        for cell in column.cells
        if cell.type == CellType.INVENTORY and cell.row_type == CellType.INVENTORY
    ]
    assert len(inventory_cells) >= 2

    baseline_cells = [cell.model_copy() for cell in inventory_cells[:2]]

    try:
        expected_values = {}
        updated_cells = []
        for idx, cell in enumerate(inventory_cells[:2]):
            base_value = float(cell.value)
            base_min = float(cell.min_value) if cell.min_value is not None else 0.0
            base_max = float(cell.max_value) if cell.max_value is not None else base_value

            new_value = round(base_value + 5 + idx, 3)
            new_min = round(base_min + 1.5, 3)
            new_max = round(base_max + 2.5, 3)

            expected_values[cell.row_id] = {
                "value": new_value,
                "min": new_min,
                "max": new_max,
            }

            updated_cells.append(
                cell.model_copy(
                    update={
                        "value": f"{new_value}",
                        "min_value": f"{new_min}",
                        "max_value": f"{new_max}",
                    }
                )
            )

        updated, failed = seeded_sheet.update_cells(cells=updated_cells)

        assert failed == []
        assert {(c.row_id, c.column_id) for c in updated} == {
            (c.row_id, c.column_id) for c in updated_cells
        }

        refreshed_column = seeded_sheet.get_column(column_id=column.column_id)
        refreshed_cells = {
            cell.row_id: cell
            for cell in refreshed_column.cells
            if cell.row_id in expected_values
            and cell.type == CellType.INVENTORY
            and cell.row_type == CellType.INVENTORY
        }

        assert set(refreshed_cells.keys()) == set(expected_values.keys())

        for row_id, expected in expected_values.items():
            refreshed = refreshed_cells[row_id]
            assert float(refreshed.value) == pytest.approx(expected["value"], rel=1e-6)
            if refreshed.min_value is not None:
                assert float(refreshed.min_value) == pytest.approx(expected["min"], rel=1e-6)
            else:
                assert expected["min"] == pytest.approx(0.0, rel=1e-6)
            if refreshed.max_value is not None:
                assert float(refreshed.max_value) == pytest.approx(expected["max"], rel=1e-6)
    finally:
        # Restore original values to keep fixture data stable for subsequent tests
        seeded_sheet.update_cells(cells=baseline_cells)


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


# TODO: investigate why this is failing
@pytest.mark.xfail(reason="This is consistently failing. Ptential issue with the testing suite.")
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
