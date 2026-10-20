import pandas as pd
import pytest

from albert.exceptions import AlbertException
from albert.resources.inventory import InventoryItem
from albert.resources.sheets import (
    Cell,
    CellType,
    Column,
    Component,
    DesignType,
    Row,
    Sheet,
)

pytestmark = pytest.mark.xdist_group("sheets")


def _formulation_column(sheet: Sheet, product: InventoryItem) -> Column:
    return sheet.get_column(inventory_id=product.id)


def _inventory_cells(column: Column) -> list[Cell]:
    return [
        cell
        for cell in column.cells
        if cell.type == CellType.INVENTORY and cell.row_type == CellType.INVENTORY
    ]


def test_get_test_sheet(seeded_sheet: Sheet):
    assert isinstance(seeded_sheet, Sheet)
    seeded_sheet.rename(new_name="test renamed")
    assert seeded_sheet.name == "test renamed"
    seeded_sheet.rename(new_name="test")
    assert seeded_sheet.name == "test"
    assert isinstance(seeded_sheet.grid, pd.DataFrame)


def test_formulation_column_names_use_display_name(
    seeded_sheet: Sheet, seeded_products: list[InventoryItem]
):
    assert seeded_products, "Expected a seeded formulation on the sheet"
    mapping = {f.id: f.name for f in seeded_sheet.formulations}
    matched = False
    for col in seeded_sheet.columns:
        if col.inventory_id in mapping:
            matched = True
            assert col.name == mapping[col.inventory_id]
    assert matched, "No formulation columns found"


def test_add_formulation_lifecycle(
    seed_prefix: str,
    seeded_sheet: Sheet,
    seeded_inventory,
):
    """Test clear-and-reuse of a private formulation column, then patching its cells."""
    name = f"{seed_prefix} - formulation lifecycle"
    components_with_bounds = [
        Component(inventory_item=seeded_inventory[0], amount=33.1, min_value=0, max_value=50),
        Component(inventory_item=seeded_inventory[1], amount=66.9, min_value=50, max_value=100),
    ]

    new_col = seeded_sheet.add_formulation(
        formulation_name=name,
        components=components_with_bounds,
        enforce_order=True,
    )
    assert isinstance(new_col, Column)

    reused = seeded_sheet.add_formulation(
        formulation_name=name,
        components=components_with_bounds,
        enforce_order=True,
        clear=True,
    )
    assert reused.column_id == new_col.column_id

    component_map = {c.inventory_item.id: c for c in components_with_bounds}
    row_id_to_inv_id = {row.row_id: row.inventory_id for row in seeded_sheet.product_design.rows}

    found_cells = 0
    for cell in reused.cells:
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

    assert found_cells == len(components_with_bounds)

    expected_values = {}
    updated_cells = []
    for idx, cell in enumerate(_inventory_cells(reused)[:2]):
        base_value = float(cell.value)
        base_min = float(cell.min_value) if cell.min_value is not None else 0.0
        base_max = float(cell.max_value) if cell.max_value is not None else base_value
        new_value = round(base_value + 5 + idx, 3)
        # max must stay >= both the current and the new value; the API
        # applies max patches before value patches.
        new_max = round(max(base_max, base_value, new_value) + 2.5, 3)
        new_min = round(min(base_min + 1.5, new_value), 3)
        expected_values[cell.row_id] = (new_value, new_min, new_max)
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

    refreshed = {
        cell.row_id: cell
        for cell in _inventory_cells(seeded_sheet.get_column(column_id=reused.column_id))
        if cell.row_id in expected_values
    }
    assert set(refreshed) == set(expected_values)
    for row_id, (value, min_value, max_value) in expected_values.items():
        assert float(refreshed[row_id].value) == pytest.approx(value)
        assert float(refreshed[row_id].min_value) == pytest.approx(min_value)
        assert float(refreshed[row_id].max_value) == pytest.approx(max_value)


# Because you cannot delete Formulation Columns, We will need to mock this test.
# def test_crud_formulation_column(sheet):
#     new_col = sheet.add_formulation_columns(formulation_names=["my cool formulation"])[0]


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
