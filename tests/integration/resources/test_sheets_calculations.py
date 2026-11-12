"""Calculated property rows and ingredient basis columns on a live sheet.

The module builds one private sheet with an ingredient basis and a calculated property.
Tenants without worksheet calculations skip the whole module.
"""

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass

import pytest

from albert import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertException, AlbertHTTPError, BadRequestError, NotFoundError
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
    Column,
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
class PrivateSheet:
    sheet: Sheet
    source: Attribute
    """A numeric attribute the ingredient basis references."""
    attribute: Attribute
    """The attribute holding the ingredient basis and calculated properties."""
    ib_name: str
    cp_name: str
    """A calculated property that reads the ingredient basis."""
    function_cp_name: str
    """A calculated property that filters ingredients by Function."""
    formulas: list[Column]
    ingredient_ids: list[str]


@contextmanager
def _private_sheet(client: Albert, seed_prefix: str, label: str) -> Iterator[PrivateSheet]:
    """A private sheet with two formulations and an attribute with calculations."""
    location = project = None
    data_columns: list[DataColumn] = []
    attributes: list[Attribute] = []
    ingredients: list[InventoryItem] = []
    try:
        location = client.locations.create(
            location=Location(
                name=f"{seed_prefix} - {label}",
                latitude=40.7,
                longitude=-74.0,
                address="1 Calculations St, New York, NY",
            )
        )
        project = client.projects.create(
            project=Project(
                description=f"{seed_prefix} - {label}",
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
                    name=f"{seed_prefix} - {label} ingredient {i}",
                    category=InventoryCategory.RAW_MATERIALS,
                    company="SDK Calculations Test Co",
                )
            )
            for i in range(2)
        ]
        data_columns = [
            client.data_columns.create(data_column=DataColumn(name=f"{seed_prefix} - {label} {i}"))
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
        function_cp_name = f"{seed_prefix} Resin Share"
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
                    FormulaMetadata(
                        display_name=function_cp_name,
                        expression='sum(wt% WHERE Function = "Resin")',
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
                    name=f"{seed_prefix} - {label} F{n}",
                    components=[
                        Component(inventory_id=ingredients[0].id, amount=amount),
                        Component(inventory_id=ingredients[1].id, amount=100 - amount),
                    ],
                )
                for n, amount in ((1, 60), (2, 30))
            ]
        )
        yield PrivateSheet(
            sheet=sheet,
            source=source,
            attribute=attribute,
            ib_name=ib_name,
            cp_name=cp_name,
            function_cp_name=function_cp_name,
            formulas=formulas,
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
    with _private_sheet(client, seed_prefix, "calculations") as private:
        sheet, attribute, formulas = private.sheet, private.attribute, private.formulas
        try:
            enable_sheet_calculations(
                client.session,
                sheet_id=sheet.id,
                attribute=attribute,
                ingredient_basis_name=private.ib_name,
                calculated_property_name=private.cp_name,
            )
            cpr_row_id = add_calculated_property_row(
                client.session,
                design_id=sheet.product_design.id,
                name=private.cp_name,
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
            ib_name=private.ib_name,
            cp_name=private.cp_name,
            cpr_row_id=cpr_row_id,
            formula_column_id=formulas[0].column_id,
            formula_inventory_id=formulas[0].inventory_id,
            ingredient_ids=private.ingredient_ids,
        )


def _row_id_for(sheet: Sheet, inventory_id: str) -> str:
    return next(
        row.row_id for row in sheet.product_design.rows if row.inventory_id == inventory_id
    )


def _cell_at(sheet: Sheet, *, column_id: str, row_id: str) -> Cell:
    cells = sheet.get_column(column_id=column_id).cells
    return next(c for c in cells if isinstance(c, Cell) and c.row_id == row_id)


def test_get_calculations(calculations_sheet: CalculationsSheet):
    """Test that a sheet lists its ingredient basis, calculated property and attribute."""
    attribute_id = calculations_sheet.attribute.id

    calculations = calculations_sheet.sheet.get_calculations()

    assert [(c.attribute_id, c.name) for c in calculations.ingredient_bases] == [
        (attribute_id, calculations_sheet.ib_name)
    ]
    assert [(c.attribute_id, c.name) for c in calculations.calculated_properties] == [
        (attribute_id, calculations_sheet.cp_name)
    ]
    assert [a.id for a in calculations.attributes] == [attribute_id]


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


def test_formula_exposes_stored_calculated_property_values(
    client: Albert, calculations_sheet: CalculationsSheet
):
    """Test that a formula's stored calculated property values are read with the item."""
    inventory_id = calculations_sheet.formula_inventory_id
    stored = client.session.get(f"/api/v3/inventories/{inventory_id}").json()
    if not stored.get("calculatedProperties"):
        pytest.skip("stored calculated property values are not available on this tenant")

    item = client.inventory.get_by_id(id=inventory_id)

    value = item.calculated_properties[calculations_sheet.attribute.id]
    assert value.value == _CP_VALUE
    assert value.updated_at


def _pin_layout(sheet: Sheet) -> list[tuple[str, str | None]]:
    sheet.grid = None
    return [(c.column_id, c.pinned) for c in sheet.columns]


def test_pin_columns_skips_ingredient_basis_columns(calculations_sheet: CalculationsSheet):
    """Test that pinning or unpinning an ingredient basis column alone changes nothing."""
    sheet = calculations_sheet.sheet
    before = _pin_layout(sheet)
    basis_id = next(c.column_id for c in sheet.columns if c.type == CellType.INGREDIENT_BASIS)

    with pytest.warns(UserWarning, match=basis_id) as record:
        sheet.pin_columns(col_ids=[basis_id], side="left")
    with pytest.warns(UserWarning, match=basis_id):
        sheet.unpin_columns(col_ids=[basis_id])

    assert _pin_layout(sheet) == before
    assert record[0].filename == __file__


def test_pin_columns_keeps_ingredient_basis_with_its_formulation_column(
    calculations_sheet: CalculationsSheet,
):
    """Test that a pinned, then unpinned, formulation column keeps its ingredient basis beside it."""
    sheet = calculations_sheet.sheet
    formula_id = calculations_sheet.formula_column_id

    def formula_and_next() -> tuple[tuple[str, str | None], tuple[str, str | None]]:
        layout = _pin_layout(sheet)
        i = next(i for i, (col_id, _) in enumerate(layout) if col_id == formula_id)
        return layout[i], layout[i + 1]

    _, (basis_id, _) = formula_and_next()
    assert next(c for c in sheet.columns if c.column_id == basis_id).type == (
        CellType.INGREDIENT_BASIS
    )
    try:
        sheet.pin_columns(col_ids=[formula_id], side="left")
        pinned_formula, pinned_next = formula_and_next()
    finally:
        sheet.unpin_columns(col_ids=[formula_id])
    unpinned_formula, unpinned_next = formula_and_next()

    assert (pinned_formula, pinned_next[0]) == ((formula_id, "left"), basis_id)
    assert (unpinned_formula, unpinned_next[0]) == ((formula_id, None), basis_id)


@pytest.fixture(scope="module")
def editable_sheet(client: Albert, seed_prefix: str) -> Iterator[PrivateSheet]:
    """A private sheet that starts without calculations, for adding and removing them."""
    with _private_sheet(client, seed_prefix, "calculation edits") as private:
        yield private


def _clear_calculations(private: PrivateSheet) -> None:
    """Take the attribute's calculations off the sheet, calculated properties first."""
    for name in (private.cp_name, private.function_cp_name, private.ib_name):
        private.sheet.remove_calculation(attribute_id=private.attribute.id, display_name=name)


def _calculated_rows(sheet: Sheet) -> dict[str, str]:
    sheet.grid = None
    rows = sheet.product_design.rows
    return {r.name: r.row_id for r in rows if r.type == CellType.CALCULATED_PROPERTY}


def _calculation_group(sheet: Sheet):
    groups = sheet.product_design.get_groups(refresh=True)
    return next((g for g in groups if g.name == "Calculated Properties"), None)


def _columns_of(sheet: Sheet, column_type: CellType) -> list[Column]:
    sheet.grid = None
    return [c for c in sheet.columns if c.type == column_type]


def test_add_calculation_brings_what_a_calculated_property_needs(editable_sheet: PrivateSheet):
    """Test that a calculated property comes with its basis, referenced attribute and row."""
    private = editable_sheet
    sheet, attribute_id = private.sheet, private.attribute.id
    try:
        calculations = sheet.add_calculation(
            attribute_id=attribute_id, display_name=private.cp_name
        )

        assert [(c.attribute_id, c.name) for c in calculations.calculated_properties] == [
            (attribute_id, private.cp_name)
        ]
        assert [(c.attribute_id, c.name) for c in calculations.ingredient_bases] == [
            (attribute_id, private.ib_name)
        ]
        assert [a.id for a in calculations.attributes] == [private.source.id]
        assert sheet.get_calculations() == calculations
        basis_columns = _columns_of(sheet, CellType.INGREDIENT_BASIS)
        formula_columns = _columns_of(sheet, CellType.INVENTORY)
        assert [c.name for c in basis_columns] == [private.ib_name] * len(formula_columns)
        assert len(_columns_of(sheet, CellType.RSL)) == 1
        rows = _calculated_rows(sheet)
        assert list(rows) == [private.cp_name]
        assert _calculation_group(sheet).child_row_ids == list(rows.values())
    finally:
        _clear_calculations(private)


def test_add_calculation_twice_changes_nothing(editable_sheet: PrivateSheet):
    """Test that adding a calculation the sheet already has leaves the sheet as it is."""
    private = editable_sheet
    sheet, attribute_id = private.sheet, private.attribute.id
    try:
        first = sheet.add_calculation(attribute_id=attribute_id, display_name=private.cp_name)
        columns = [c.column_id for c in _columns_of(sheet, CellType.INGREDIENT_BASIS)]
        rows = _calculated_rows(sheet)

        second = sheet.add_calculation(attribute_id=attribute_id, display_name=private.cp_name)

        assert second == first
        assert [c.column_id for c in _columns_of(sheet, CellType.INGREDIENT_BASIS)] == columns
        assert _calculated_rows(sheet) == rows
        assert len(_columns_of(sheet, CellType.RSL)) == 1
    finally:
        _clear_calculations(private)


def test_add_calculation_groups_rows_and_adds_a_function_column(editable_sheet: PrivateSheet):
    """Test that calculated properties share one group and a Function filter gets its column."""
    private = editable_sheet
    sheet, attribute_id = private.sheet, private.attribute.id
    try:
        sheet.add_calculation(attribute_id=attribute_id, display_name=private.cp_name)
        sheet.add_calculation(attribute_id=attribute_id, display_name=private.function_cp_name)

        rows = _calculated_rows(sheet)
        assert set(rows) == {private.cp_name, private.function_cp_name}
        assert sorted(_calculation_group(sheet).child_row_ids) == sorted(rows.values())
        assert [c.name for c in _columns_of(sheet, CellType.FNC)] == ["Function"]
    finally:
        _clear_calculations(private)


def test_remove_calculation_refuses_a_basis_a_calculated_property_reads(
    editable_sheet: PrivateSheet,
):
    """Test that an ingredient basis stays while a calculated property on the sheet uses it."""
    private = editable_sheet
    sheet, attribute_id = private.sheet, private.attribute.id
    try:
        sheet.add_calculation(attribute_id=attribute_id, display_name=private.cp_name)

        with pytest.raises(AlbertException, match=private.cp_name):
            sheet.remove_calculation(attribute_id=attribute_id, display_name=private.ib_name)

        bases = sheet.get_calculations().ingredient_bases
        assert [c.name for c in bases] == [private.ib_name]
    finally:
        _clear_calculations(private)


def test_remove_calculation_removes_the_row_and_its_empty_group(editable_sheet: PrivateSheet):
    """Test that removing the last calculated property removes its row and group."""
    private = editable_sheet
    sheet, attribute_id = private.sheet, private.attribute.id
    try:
        sheet.add_calculation(attribute_id=attribute_id, display_name=private.cp_name)

        calculations = sheet.remove_calculation(
            attribute_id=attribute_id, display_name=private.cp_name
        )

        assert calculations.calculated_properties == []
        assert [c.name for c in calculations.ingredient_bases] == [private.ib_name]
        assert _calculated_rows(sheet) == {}
        assert _calculation_group(sheet) is None
    finally:
        _clear_calculations(private)


def test_remove_calculation_removes_ingredient_basis_columns(editable_sheet: PrivateSheet):
    """Test that removing an ingredient basis removes its columns and keeps its attributes."""
    private = editable_sheet
    sheet, attribute_id = private.sheet, private.attribute.id
    try:
        sheet.add_calculation(attribute_id=attribute_id, display_name=private.ib_name)

        calculations = sheet.remove_calculation(
            attribute_id=attribute_id, display_name=private.ib_name
        )

        assert calculations.ingredient_bases == []
        assert [a.id for a in calculations.attributes] == [private.source.id]
        assert _columns_of(sheet, CellType.INGREDIENT_BASIS) == []
    finally:
        _clear_calculations(private)


def test_remove_calculation_of_an_absent_formula_changes_nothing(editable_sheet: PrivateSheet):
    """Test that removing a calculation the sheet does not have leaves it as it is."""
    sheet = editable_sheet.sheet
    before = sheet.get_calculations()

    after = sheet.remove_calculation(
        attribute_id=editable_sheet.attribute.id, display_name=editable_sheet.cp_name
    )

    assert after == before
