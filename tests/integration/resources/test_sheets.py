from contextlib import suppress

import pandas as pd
import pytest

from albert import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertException, BadRequestError, NotFoundError
from albert.resources.inventory import InventoryItem
from albert.resources.locations import Location
from albert.resources.projects import Project
from albert.resources.sheets import (
    Cell,
    CellType,
    Column,
    Component,
    DesignType,
    FormulationSpec,
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
        if isinstance(cell, Cell)
        and cell.type == CellType.INVENTORY
        and cell.row_type == CellType.INVENTORY
        and cell.value not in (None, "")
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
            if cell.value in (None, ""):
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


def test_add_formulations_builds_columns_with_shared_rows(
    seed_prefix: str,
    seeded_sheet: Sheet,
    seeded_inventory: list[InventoryItem],
):
    """Test building several formulations at once, sharing ingredient rows."""
    name_a = f"{seed_prefix} - bulk formulation A"
    name_b = f"{seed_prefix} - bulk formulation B"
    shared = seeded_inventory[0]
    only_a = seeded_inventory[1]
    only_b = seeded_inventory[2]

    columns = seeded_sheet.add_formulations(
        formulations=[
            FormulationSpec(
                name=name_a,
                components=[
                    Component(inventory_item=shared, amount=70.0),
                    Component(inventory_item=only_a, amount=30.0),
                ],
            ),
            FormulationSpec(
                name=name_b,
                components=[
                    Component(inventory_item=shared, amount=55.0),
                    Component(inventory_item=only_b, amount=45.0),
                ],
            ),
        ]
    )

    assert [column.name for column in columns] == [name_a, name_b]
    assert all(isinstance(column, Column) for column in columns)

    # Read back fresh from the server rather than the in-memory cache.
    seeded_sheet.grid = None
    columns = [seeded_sheet.get_column(column_id=column.column_id) for column in columns]

    row_id_to_inv_id = {row.row_id: row.inventory_id for row in seeded_sheet.product_design.rows}
    amounts_by_column = []
    for column in columns:
        amounts = {}
        for cell in column.cells:
            if not isinstance(cell, Cell):
                continue
            if cell.type == CellType.INVENTORY and cell.row_type == CellType.INVENTORY:
                if cell.value in (None, ""):
                    continue
                amounts[row_id_to_inv_id[cell.row_id]] = float(cell.value)
            elif cell.row_type == CellType.TOTAL:
                assert float(cell.value) == pytest.approx(100.0)
        amounts_by_column.append(amounts)

    assert amounts_by_column[0] == {shared.id: 70.0, only_a.id: 30.0}
    assert amounts_by_column[1] == {shared.id: 55.0, only_b.id: 45.0}

    # The shared ingredient occupies the same single row in both formulations.
    rows_a = {cell.row_id for cell in _inventory_cells(columns[0])}
    rows_b = {cell.row_id for cell in _inventory_cells(columns[1])}
    assert len(rows_a & rows_b) == 1


def test_add_formulations_enforce_order_follows_component_order(
    seed_prefix: str,
    seeded_sheet: Sheet,
    seeded_inventory: list[InventoryItem],
):
    """Test that ordered bulk builds arrange ingredient rows in component order."""
    first = seeded_inventory[1]
    second = seeded_inventory[0]

    columns = seeded_sheet.add_formulations(
        enforce_order=True,
        formulations=[
            FormulationSpec(
                name=f"{seed_prefix} - bulk ordered",
                components=[
                    Component(inventory_item=first, amount=60.0),
                    Component(inventory_item=second, amount=40.0),
                ],
            )
        ],
    )
    assert len(columns) == 1

    # Read back fresh from the server rather than the in-memory cache.
    seeded_sheet.grid = None
    column = seeded_sheet.get_column(column_id=columns[0].column_id)

    row_id_to_inv_id = {row.row_id: row.inventory_id for row in seeded_sheet.product_design.rows}
    row_order = [row.row_id for row in seeded_sheet.product_design.rows]
    ordered_inventory = [
        row_id_to_inv_id[cell.row_id]
        for cell in sorted(_inventory_cells(column), key=lambda cell: row_order.index(cell.row_id))
    ]
    assert ordered_inventory == [first.id, second.id]
    assert {float(cell.value) for cell in _inventory_cells(column)} == {60.0, 40.0}


def test_add_formulations_clear_rebuilds_existing_columns(
    seed_prefix: str,
    seeded_sheet: Sheet,
    seeded_inventory: list[InventoryItem],
):
    """Test that a repeated bulk build updates the same columns in place."""
    name = f"{seed_prefix} - bulk rebuildable"
    kept = seeded_inventory[0]
    dropped = seeded_inventory[1]

    first = seeded_sheet.add_formulations(
        formulations=[
            FormulationSpec(
                name=name,
                components=[
                    Component(inventory_item=kept, amount=10.0),
                    Component(inventory_item=dropped, amount=30.0),
                ],
            )
        ]
    )[0]

    second = seeded_sheet.add_formulations(
        formulations=[
            FormulationSpec(
                name=name,
                components=[Component(inventory_item=kept, amount=25.0)],
            )
        ]
    )[0]

    # The same name was updated in place rather than duplicated.
    assert second.column_id == first.column_id
    matching = [c for c in seeded_sheet.columns if c.name == name]
    assert len(matching) == 1

    # Read back fresh from the server rather than the in-memory cache: the
    # rebuilt column holds only the new amounts, the dropped ingredient is blank.
    seeded_sheet.grid = None
    column = seeded_sheet.get_column(column_id=first.column_id)
    row_id_to_inv_id = {row.row_id: row.inventory_id for row in seeded_sheet.product_design.rows}
    amounts = {
        row_id_to_inv_id[cell.row_id]: float(cell.value)
        for cell in _inventory_cells(column)
        if cell.value not in (None, "")
    }
    assert amounts == {kept.id: 25.0}


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


def test_rename_row_group(client: Albert, seed_prefix: str):
    """Test renaming a row group's header row persists the new name."""
    location = client.locations.create(
        location=Location(
            name=f"{seed_prefix} - rename row group",
            latitude=40.7,
            longitude=-74.0,
            address="1 Main St",
            country="US",
        )
    )
    project = None
    try:
        project = client.projects.create(
            project=Project(
                description=f"{seed_prefix} - rename row group",
                locations=[EntityLink(id=location.id)],
            )
        )
        worksheet = client.worksheets.setup_worksheet(project_id=project.id, add_sheet=True)
        sheet = worksheet.sheets[0]
        design = sheet.product_design

        children = sheet.add_blank_rows(
            row_names=[f"{seed_prefix} - group child A", f"{seed_prefix} - group child B"]
        )
        group = design.group_rows(
            name=f"{seed_prefix} - original group",
            child_row_ids=[r.row_id for r in children],
        )
        assert group.name == f"{seed_prefix} - original group"

        header = next(r for r in design.rows if r.row_id == group.row_id)
        renamed = f"{seed_prefix} - renamed group"
        assert header.rename(new_name=renamed) is header
        assert header.name == renamed

        groups = design.get_groups(refresh=True)
        assert next(g for g in groups if g.row_id == group.row_id).name == renamed
    finally:
        if project is not None:
            with suppress(NotFoundError, BadRequestError):
                client.projects.delete(id=project.id)
        with suppress(NotFoundError, BadRequestError):
            client.locations.delete(id=location.id)


########################## CELLS ##########################
