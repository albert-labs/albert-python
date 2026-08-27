import json
from contextlib import suppress

import pandas as pd
import pytest

from albert import Albert
from albert.exceptions import AlbertException, BadRequestError, NotFoundError
from albert.resources.inventory import InventoryItem
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
from tests.utils.fake_session import FakeAlbertSession

pytestmark = pytest.mark.xdist_group("sheets")


def _formulation_column(sheet: Sheet, product: InventoryItem) -> Column:
    return sheet.get_column(inventory_id=product.id)


def _inventory_cells(column: Column) -> list[Cell]:
    return [
        cell
        for cell in column.cells
        if cell.type == CellType.INVENTORY and cell.row_type == CellType.INVENTORY
    ]


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
):
    """Patch cells on a private formulation column (seeded formulas lock on staging)."""
    column = seeded_sheet.add_formulation(
        formulation_name=f"{seed_prefix} - update cells",
        components=[
            Component(
                inventory_item=seeded_inventory[0], amount=20.0, min_value=10.0, max_value=40.0
            ),
            Component(
                inventory_item=seeded_inventory[1], amount=80.0, min_value=60.0, max_value=90.0
            ),
        ],
        enforce_order=True,
    )
    inventory_cells = _inventory_cells(column)
    assert len(inventory_cells) >= 2

    expected_values = {}
    updated_cells = []
    for idx, cell in enumerate(inventory_cells[:2]):
        base_value = float(cell.value)
        base_min = float(cell.min_value) if cell.min_value is not None else 0.0
        base_max = float(cell.max_value) if cell.max_value is not None else base_value

        new_value = round(base_value + 5 + idx, 3)
        # max must stay >= both the current and the new value; the API
        # applies max patches before value patches.
        new_max = round(max(base_max, base_value, new_value) + 2.5, 3)
        new_min = round(min(base_min + 1.5, new_value), 3)

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
    """Test clear-and-reuse of a private formulation column, then a no-clear duplicate."""
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

    duplicate = seeded_sheet.add_formulation(
        formulation_name=name, components=components_with_bounds, clear=False
    )
    assert duplicate.column_id != new_col.column_id


########################## COLUMNS ##########################


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


def test_add_parameter_group_row_requires_process_design():
    """Test that adding a PRG row fails when the sheet has no Process Design."""
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
    with pytest.raises(AlbertException, match="Process Design"):
        sheet.add_parameter_group_row(parameter_group_id="PRG1")


def test_add_parameter_group_row_empty_response_raises():
    """Test that an empty create response raises a clear AlbertException."""
    session = FakeAlbertSession()
    session.configure_response(
        "POST",
        "/api/v3/designs/DES4/rows",
        json.dumps([]).encode(),
    )
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[
            {"albertId": "DES1", "designType": "products", "state": {}},
            {"albertId": "DES2", "designType": "results", "state": {}},
            {"albertId": "DES3", "designType": "apps", "state": {}},
            {"albertId": "DES4", "designType": "process", "state": {}},
        ],
        projectId="PRJ1",
        session=session,
    )
    with pytest.raises(AlbertException, match="No rows returned"):
        sheet.add_parameter_group_row(parameter_group_id="PRG1", reference_id="ROW1")


def test_add_parameter_group_row_empty_process_design_omits_reference():
    """First PRG on an empty Process Design must not send referenceId/position."""
    session = FakeAlbertSession()
    session.configure_response(
        "POST",
        "/api/v3/designs/DES4/rows",
        json.dumps(
            [{"rowId": "ROW5", "id": "PRG1", "type": "PRG", "name": "Mix", "labelName": "Mix"}]
        ).encode(),
    )
    # Empty grid → process_design.rows is empty.
    session.configure_response(
        "GET",
        "/api/v3/designs/DES4/grid",
        json.dumps(
            {
                "total": 0,
                "designId": "DES4",
                "Items": [],
                "Formulas": [],
                "RowSequence": [],
            }
        ).encode(),
    )
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[
            {"albertId": "DES1", "designType": "products", "state": {}},
            {"albertId": "DES2", "designType": "results", "state": {}},
            {"albertId": "DES3", "designType": "apps", "state": {}},
            {"albertId": "DES4", "designType": "process", "state": {}},
        ],
        projectId="PRJ1",
        session=session,
    )
    # FakeAlbertSession is not always copied onto nested Designs by validators.
    for design in sheet.designs:
        design._session = session

    row = sheet.add_parameter_group_row(parameter_group_id="PRG1")

    assert row.row_id == "ROW5"
    assert row.type == CellType.PRG
    posted = [r for r in session.requests if r["method"] == "POST" and r["url"].endswith("/rows")]
    assert len(posted) == 1
    assert posted[0]["json"] == [{"type": "PRG", "id": "PRG1"}]


def test_add_blank_row_rejects_process_design():
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[
            {"albertId": "DES1", "designType": "products", "state": {}},
            {"albertId": "DES2", "designType": "results", "state": {}},
            {"albertId": "DES3", "designType": "apps", "state": {}},
            {"albertId": "DES4", "designType": "process", "state": {}},
        ],
        projectId="PRJ1",
    )
    with pytest.raises(AlbertException, match="add_parameter_group_row"):
        sheet.add_blank_row(row_name="Blank", design=DesignType.PROCESS)


def test_add_parameter_group_row(
    seeded_sheet: Sheet,
    seeded_parameter_groups: list,
):
    """Test adding a parameter group row to Process Design when the sheet has one."""
    if seeded_sheet.process_design is None:
        pytest.skip("Seeded sheet has no Process Design section")

    pd_rows = seeded_sheet.process_design.rows
    if not pd_rows:
        pytest.skip("Seeded Process Design has no rows to reference")

    pg = seeded_parameter_groups[0]
    # Default reference_id resolves to the first Process Design row; pass it
    # explicitly so the assertion documents the contract.
    row = seeded_sheet.add_parameter_group_row(
        parameter_group_id=pg.id,
        reference_id=pd_rows[0].row_id,
    )
    assert isinstance(row, Row)
    assert row.type == CellType.PRG
    assert row.row_id.startswith("ROW")
    # Process Design row deletes use the design-engine path.
    seeded_sheet.session.delete(
        f"/api/v3/designs/{seeded_sheet.process_design.id}/rows",
        json=[{"rowId": row.row_id}],
    )


def test_add_task_row(
    client: Albert,
    seed_prefix: str,
    seeded_locations,
    seeded_inventory,
    seeded_data_templates,
    seeded_workflows,
):
    """Test linking a property task into a sheet's Results section as a TAS row."""
    from albert.core.shared.models.base import EntityLink
    from albert.resources.projects import Project
    from albert.resources.tasks import (
        Block,
        PropertyTask,
        TaskCategory,
        TaskInventoryInformation,
    )

    # Isolated project: TAS rows cannot be removed from a sheet, so the shared
    # seeded sheet must not be used.
    project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - add_task_row",
            locations=[EntityLink(id=seeded_locations[0].id)],
        )
    )
    task = None
    try:
        worksheet = client.worksheets.setup_worksheet(project_id=project.id, add_sheet=True)
        sheet = worksheet.sheets[0]

        column = sheet.add_formulation(
            formulation_name=f"{seed_prefix} - add_task_row formula",
            components=[Component(inventory_id=seeded_inventory[0].id, amount=100.0)],
        )

        task = client.tasks.create(
            task=PropertyTask(
                name=f"{seed_prefix} - add_task_row task",
                category=TaskCategory.PROPERTY,
                inventory_information=[TaskInventoryInformation(inventory_id=column.inventory_id)],
                parent_id=project.id,
                location=seeded_locations[0],
                blocks=[
                    Block(
                        workflow=[seeded_workflows[0]],
                        data_template=[seeded_data_templates[0]],
                    )
                ],
            )
        )

        row = sheet.add_task_row(task_id=task.id)
        assert isinstance(row, Row)
        assert row.type == CellType.TAS
        assert row.row_id.startswith("ROW")
        assert row.inventory_id == task.id

        sheet.grid = None
        result_row_ids = {r.row_id for r in sheet.result_design.rows}
        assert row.row_id in result_row_ids
    finally:
        if task is not None:
            with suppress(NotFoundError, BadRequestError):
                client.tasks.delete(id=task.id)
        with suppress(NotFoundError, BadRequestError):
            client.projects.delete(id=project.id)


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
