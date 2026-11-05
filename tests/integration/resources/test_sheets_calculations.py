"""Calculated property rows and ingredient basis columns on a live sheet.

The module builds one private sheet with an ingredient basis and a calculated property.
Tenants without worksheet calculations skip the whole module.
"""

from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass

import pytest

from albert import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError, BadRequestError, NotFoundError
from albert.resources.attributes import (
    Attribute,
    AttributeCategory,
    ExpressionType,
    FormulaMetadata,
    ValidationItem,
)
from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import DataType
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.resources.locations import Location
from albert.resources.projects import Project
from albert.resources.sheets import (
    Cell,
    CellColor,
    CellType,
    Component,
    FormulationSpec,
    Sheet,
)
from tests.integration.seeding import (
    add_calculated_property_row,
    enable_sheet_calculations,
    save_calculated_property_value,
)

# Builds its own sheet (no seeded_* fixtures), so it gets its own worker.
pytestmark = pytest.mark.xdist_group("sheetcalculations")

_NOT_ENABLED = "worksheet calculations are not enabled on this tenant"
_CP_VALUE = 42.5


@dataclass
class CalculationsSheet:
    sheet: Sheet
    attribute: Attribute
    ib_name: str
    cp_name: str
    cpr_row_id: str
    formula_column_id: str
    """The formulation column holding the stored calculated property value."""
    formula_inventory_id: str
    ingredient_ids: list[str]


@pytest.fixture(scope="module")
def calculations_sheet(client: Albert, seed_prefix: str) -> Iterator[CalculationsSheet]:
    """A private sheet with two formulations, an ingredient basis and a calculated property."""
    location = project = None
    data_columns: list[DataColumn] = []
    attributes: list[Attribute] = []
    ingredients: list[InventoryItem] = []
    try:
        location = client.locations.create(
            location=Location(
                name=f"{seed_prefix} - calculations",
                latitude=40.7,
                longitude=-74.0,
                address="1 Calculations St, New York, NY",
            )
        )
        project = client.projects.create(
            project=Project(
                description=f"{seed_prefix} - calculations",
                locations=[EntityLink(id=location.id)],
            )
        )
        worksheet = client.worksheets.setup_worksheet(project_id=project.id, add_sheet=True)
        sheet = worksheet.sheets[0]
        try:
            client.session.get(f"/api/v3/worksheet/sheet/{sheet.id}/manageWorksheet")
        except AlbertHTTPError as e:
            pytest.skip(f"{_NOT_ENABLED}: {e}")

        ingredients = [
            client.inventory.create(
                inventory_item=InventoryItem(
                    name=f"{seed_prefix} - calculations ingredient {i}",
                    category=InventoryCategory.RAW_MATERIALS,
                    company="SDK Calculations Test Co",
                )
            )
            for i in range(2)
        ]
        data_columns = [
            client.data_columns.create(
                data_column=DataColumn(name=f"{seed_prefix} - calculations {i}")
            )
            for i in range(2)
        ]
        source = client.attributes.create(
            attribute=Attribute(
                datacolumn_id=data_columns[0].id,
                category=AttributeCategory.PROPERTY,
                validation=[ValidationItem(datatype=DataType.NUMBER)],
            )
        )
        attributes.append(source)
        ib_name = f"{seed_prefix} Solids Share"
        cp_name = f"{seed_prefix} Total Solids"
        attribute = client.attributes.create(
            attribute=Attribute(
                datacolumn_id=data_columns[1].id,
                category=AttributeCategory.PROPERTY,
                validation=[ValidationItem(datatype=DataType.NUMBER)],
                formula_metadata=[
                    FormulaMetadata(
                        display_name=ib_name,
                        expression=f"wt% / sum(wt%) * [{source.id}]",
                        expression_type=ExpressionType.INGREDIENT_BASIS,
                        request_inverse=False,
                    ),
                    FormulaMetadata(
                        display_name=cp_name,
                        expression="sum(ingredient_basis)",
                        expression_type=ExpressionType.CALCULATED_PROPERTY,
                        request_inverse=False,
                    ),
                ],
            )
        )
        attributes.append(attribute)

        formulas = sheet.add_formulations(
            formulations=[
                FormulationSpec(
                    name=f"{seed_prefix} - calculations F{n}",
                    components=[
                        Component(inventory_id=ingredients[0].id, amount=amount),
                        Component(inventory_id=ingredients[1].id, amount=100 - amount),
                    ],
                )
                for n, amount in ((1, 60), (2, 30))
            ]
        )
        try:
            enable_sheet_calculations(
                client.session,
                sheet_id=sheet.id,
                attribute=attribute,
                ingredient_basis_name=ib_name,
                calculated_property_name=cp_name,
            )
            cpr_row_id = add_calculated_property_row(
                client.session,
                design_id=sheet.product_design.id,
                name=cp_name,
                attribute_id=attribute.id,
            )
        except AlbertHTTPError as e:
            pytest.skip(f"{_NOT_ENABLED}: {e}")
        sheet.grid = None
        sheet.product_design.group_rows(name="Calculated Properties", child_row_ids=[cpr_row_id])

        # The worksheet stores a calculated property value after computing it in the
        # browser; store one for the first formulation the same way.
        save_calculated_property_value(
            client.session,
            design_id=sheet.product_design.id,
            row_id=cpr_row_id,
            column_id=formulas[0].column_id,
            inventory_id=formulas[0].inventory_id,
            attribute_id=attribute.id,
            value=_CP_VALUE,
        )
        sheet.grid = None

        yield CalculationsSheet(
            sheet=sheet,
            attribute=attribute,
            ib_name=ib_name,
            cp_name=cp_name,
            cpr_row_id=cpr_row_id,
            formula_column_id=formulas[0].column_id,
            formula_inventory_id=formulas[0].inventory_id,
            ingredient_ids=[item.id for item in ingredients],
        )
    finally:
        if project is not None:
            with suppress(NotFoundError, BadRequestError):
                client.projects.delete(id=project.id)
        # Items used in a formulation, and attributes with values, cannot be deleted.
        for item in ingredients:
            with suppress(NotFoundError, BadRequestError):
                client.inventory.delete(id=item.id)
        for created in reversed(attributes):
            with suppress(NotFoundError, BadRequestError):
                client.attributes.delete(id=created.id)
        for data_column in data_columns:
            with suppress(NotFoundError, BadRequestError):
                client.data_columns.delete(id=data_column.id)
        if location is not None:
            with suppress(NotFoundError, BadRequestError):
                client.locations.delete(id=location.id)


def _row_id_for(sheet: Sheet, inventory_id: str) -> str:
    return next(
        row.row_id for row in sheet.product_design.rows if row.inventory_id == inventory_id
    )


def _cell_at(sheet: Sheet, *, column_id: str, row_id: str) -> Cell:
    cells = sheet.get_column(column_id=column_id).cells
    return next(c for c in cells if isinstance(c, Cell) and c.row_id == row_id)


def test_ingredient_basis_columns_have_no_inventory_id(calculations_sheet: CalculationsSheet):
    """Test that ingredient basis columns are listed, typed, and carry no inventory ID."""
    sheet = calculations_sheet.sheet
    sheet.grid = None

    formula_columns = [c for c in sheet.columns if c.type == CellType.INVENTORY]
    basis_columns = [c for c in sheet.columns if c.type == CellType.INGREDIENT_BASIS]

    assert len(basis_columns) == len(formula_columns)
    assert {c.name for c in basis_columns} == {calculations_sheet.ib_name}
    assert [c.inventory_id for c in basis_columns] == [None] * len(basis_columns)
    assert all(c.inventory_id.startswith("INV") for c in formula_columns)
    basis_cells = [c for column in basis_columns for c in column.cells if isinstance(c, Cell)]
    assert basis_cells
    assert {c.inventory_id for c in basis_cells} == {None}


def test_calculated_property_row_is_typed(calculations_sheet: CalculationsSheet):
    """Test that the calculated property row is recognised by type and display name."""
    sheet = calculations_sheet.sheet
    sheet.grid = None

    row = next(r for r in sheet.product_design.rows if r.row_id == calculations_sheet.cpr_row_id)

    assert row.type == CellType.CALCULATED_PROPERTY
    assert row.name == calculations_sheet.cp_name
    assert row.inventory_id is None


def test_formula_column_exposes_cp_reference_values(
    client: Albert, calculations_sheet: CalculationsSheet
):
    """Test that a formulation column carries the formula's calculated property values."""
    sheet = calculations_sheet.sheet
    grid = client.session.get(f"/api/v3/worksheet/{sheet.product_design.id}/products/grid").json()
    formula = next(
        f for f in grid["Formulas"] if f.get("colId") == calculations_sheet.formula_column_id
    )
    if "cpReferenceValues" not in formula:
        pytest.skip("calculated property reference values are not available on this tenant")
    sheet.grid = None

    column = sheet.get_column(column_id=calculations_sheet.formula_column_id)

    assert column.cp_reference_values == {calculations_sheet.attribute.id: str(_CP_VALUE)}


def test_update_cells_never_writes_calculated_cells(calculations_sheet: CalculationsSheet):
    """Test that a mixed write saves ordinary cells and returns calculated ones unwritten."""
    sheet = calculations_sheet.sheet
    sheet.grid = None
    column_id = calculations_sheet.formula_column_id
    ingredient_row_id = _row_id_for(sheet, calculations_sheet.ingredient_ids[0])
    basis_column_id = next(
        c.column_id for c in sheet.columns if c.type == CellType.INGREDIENT_BASIS
    )
    amount = _cell_at(sheet, column_id=column_id, row_id=ingredient_row_id)
    cp = _cell_at(sheet, column_id=column_id, row_id=calculations_sheet.cpr_row_id)
    basis = _cell_at(sheet, column_id=basis_column_id, row_id=ingredient_row_id)

    with pytest.warns(UserWarning, match="retrying will not write them"):
        updated, failed = sheet.update_cells(
            cells=[
                amount.model_copy(update={"value": "55"}),
                cp.model_copy(update={"value": "99"}),
                basis.model_copy(update={"value": "99"}),
            ]
        )

    assert [(c.row_id, c.column_id) for c in updated] == [(ingredient_row_id, column_id)]
    assert [(c.row_id, c.column_id) for c in failed] == [
        (calculations_sheet.cpr_row_id, column_id),
        (ingredient_row_id, basis_column_id),
    ]
    sheet.grid = None
    assert _cell_at(sheet, column_id=column_id, row_id=ingredient_row_id).value == "55"
    assert _cell_at(sheet, column_id=column_id, row_id=cp.row_id).value == cp.value
    assert _cell_at(sheet, column_id=basis_column_id, row_id=basis.row_id).value == basis.value


def test_update_cells_never_writes_hand_built_calculated_cells(
    calculations_sheet: CalculationsSheet,
):
    """Test that calculated cells built without the sheet's types are still not written."""
    sheet = calculations_sheet.sheet
    sheet.grid = None
    design_id = sheet.product_design.id
    column_id = calculations_sheet.formula_column_id
    ingredient_row_id = _row_id_for(sheet, calculations_sheet.ingredient_ids[0])
    basis_column_id = next(
        c.column_id for c in sheet.columns if c.type == CellType.INGREDIENT_BASIS
    )
    stored_cp = _cell_at(sheet, column_id=column_id, row_id=calculations_sheet.cpr_row_id)
    stored_basis = _cell_at(sheet, column_id=basis_column_id, row_id=ingredient_row_id)
    cp = Cell(
        colId=column_id,
        rowId=calculations_sheet.cpr_row_id,
        type=CellType.INVENTORY,
        design_id=design_id,
        value="99",
    )
    basis = Cell(
        colId=basis_column_id,
        rowId=ingredient_row_id,
        type=CellType.INVENTORY,
        design_id=design_id,
        value="99",
    )

    with pytest.warns(UserWarning, match="retrying will not write them"):
        updated, failed = sheet.update_cells(cells=[cp, basis])

    assert (updated, failed) == ([], [cp, basis])
    sheet.grid = None
    assert _cell_at(sheet, column_id=column_id, row_id=cp.row_id).value == stored_cp.value
    assert (
        _cell_at(sheet, column_id=basis_column_id, row_id=basis.row_id).value == stored_basis.value
    )


def test_recolor_cells_colors_calculated_cells(calculations_sheet: CalculationsSheet):
    """Test that recoloring a calculated property row and an ingredient basis column colors them."""
    sheet = calculations_sheet.sheet
    sheet.grid = None
    cpr_row = next(r for r in sheet.rows if r.row_id == calculations_sheet.cpr_row_id)
    basis_column = next(c for c in sheet.columns if c.type == CellType.INGREDIENT_BASIS)
    ingredient_row_id = _row_id_for(sheet, calculations_sheet.ingredient_ids[0])

    _, row_failed = cpr_row.recolor_cells(CellColor.YELLOW)
    _, column_failed = basis_column.recolor_cells(CellColor.BLUE)

    assert row_failed == []
    assert column_failed == []
    sheet.grid = None
    cp = _cell_at(
        sheet, column_id=calculations_sheet.formula_column_id, row_id=calculations_sheet.cpr_row_id
    )
    basis = _cell_at(sheet, column_id=basis_column.column_id, row_id=ingredient_row_id)
    assert cp.format.get("bgColor") == CellColor.YELLOW.value
    assert basis.format.get("bgColor") == CellColor.BLUE.value


def test_reorder_columns_keeps_ingredient_basis_with_formulas(
    calculations_sheet: CalculationsSheet,
):
    """Test reordering formulation columns on a sheet with ingredient basis columns."""
    sheet = calculations_sheet.sheet
    sheet.grid = None
    columns = sheet.columns
    formula_ids = [c.column_id for c in columns if c.type == CellType.INVENTORY]
    basis_ids = [c.column_id for c in columns if c.type == CellType.INGREDIENT_BASIS]
    others = [
        c.column_id
        for c in columns
        if c.column_id not in formula_ids and c.column_id not in basis_ids
    ]
    requested = [*others, *reversed(formula_ids)]

    # Every column listed, ingredient basis columns at the end, as from sheet.columns.
    sheet.reorder_columns(column_ids=[*requested, *basis_ids])

    sheet.grid = None
    after = sheet.columns
    assert [c.column_id for c in after if c.type != CellType.INGREDIENT_BASIS] == requested
    assert sorted(c.column_id for c in after if c.type == CellType.INGREDIENT_BASIS) == sorted(
        basis_ids
    )
    # Each ingredient basis column still follows a formulation column.
    assert all(
        after[i - 1].type == CellType.INVENTORY
        for i, c in enumerate(after)
        if c.type == CellType.INGREDIENT_BASIS
    )
