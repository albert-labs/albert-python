"""Calculated property (CPR) rows and ingredient basis (IBS) columns on sheets."""

import json

import pytest
import responses

from albert.core.shared.models.patch import PatchDatum
from albert.exceptions import AlbertPartialError
from albert.resources.sheets import Cell, CellType, Column, ColumnPosition, Sheet
from tests.unit.conftest import UNIT_BASE_URL


def _products_sheet(session=None) -> Sheet:
    return Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[{"albertId": "DES1", "designType": "products", "state": {}}],
        projectId="PRJ1",
        session=session,
    )


def _grid_row(row_id: str, row_type: str, name: str, row_item_id: str | None, values) -> dict:
    """One grid row; ``values`` are the COL1, COL5, COL7, COL6, COL8 cell values."""
    columns = [
        ("COL1", "DEF", None, "Inventory ID"),
        ("COL5", "INV", "INVMO1-001", "F1"),
        ("COL7", "IBS", "ATR2", "Solids Share"),
        ("COL6", "INV", "INVMO1-002", "F2"),
        ("COL8", "IBS", "ATR2", "Solids Share"),
    ]
    return {
        "rowId": row_id,
        "rowUniqueId": f"DES1#{row_id}",
        "type": row_type,
        "id": row_item_id,
        "name": name,
        "Values": [
            {"colId": col_id, "type": col_type, "id": item_id, "name": col_name, "value": value}
            for (col_id, col_type, item_id, col_name), value in zip(columns, values, strict=True)
        ],
    }


# Shaped like a live products grid with one ingredient basis (attribute ATR2) under two
# formulas, and a calculated property row grouped under "Calculated Properties".
_CALCULATIONS_GRID = {
    "Formulas": [
        {"colId": "COL1", "name": "Inventory ID", "type": "DEF", "state": {"pinned": "left"}},
        {
            "colId": "COL5",
            "id": "INVMO1-001",
            "name": "F1",
            "type": "INV",
            "state": {},
            "hidden": False,
            "cpReferenceValues": {"ATR2": "42.5"},
            "childCols": [
                {"colId": "COL7", "id": "ATR2", "name": "Solids Share", "type": "IBS", "state": {}}
            ],
        },
        {
            "colId": "COL6",
            "id": "INVMO1-002",
            "name": "F2",
            "type": "INV",
            "state": {},
            "hidden": False,
            "childCols": [
                {"colId": "COL8", "id": "ATR2", "name": "Solids Share", "type": "IBS", "state": {}}
            ],
        },
    ],
    "Items": [
        _grid_row("ROW15", "BLK", "Calculated Properties", None, ["", "", "", "", ""]),
        _grid_row("ROW14", "CPR", "Total Solids", None, ["", "42.5", "", "", ""]),
        _grid_row("ROW12", "INV", "Water", "INVA1", ["INVA1", "60", "30", "40", "20"]),
        _grid_row("ROW1", "TOT", "Total", "APP1", ["APP1", "60", "", "40", ""]),
    ],
}


def _register_calculations_grid():
    responses.get(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/products/grid", json=_CALCULATIONS_GRID)


# --- Design._get_columns ---


def test_get_columns_keeps_ingredient_basis_columns_without_inventory_id():
    """Test that ingredient basis columns stay in place, typed, with no inventory ID."""
    sheet = _products_sheet()

    columns = sheet.product_design._get_columns(grid_response=_CALCULATIONS_GRID)

    assert [(c.column_id, c.type, c.inventory_id) for c in columns] == [
        ("COL1", "DEF", None),
        ("COL5", CellType.INVENTORY, "INVMO1-001"),
        ("COL7", CellType.INGREDIENT_BASIS, None),
        ("COL6", CellType.INVENTORY, "INVMO1-002"),
        ("COL8", CellType.INGREDIENT_BASIS, None),
    ]


def test_get_columns_reads_cp_reference_values_and_leaves_absent_ones_none():
    """Test that each formulation column carries its calculated property reference values."""
    sheet = _products_sheet()

    columns = sheet.product_design._get_columns(grid_response=_CALCULATIONS_GRID)

    assert [c.cp_reference_values for c in columns] == [None, {"ATR2": "42.5"}, None, None, None]


def test_column_dump_excludes_cp_reference_values():
    """Test that cp_reference_values never leaves the SDK in a serialized column."""
    column = Column(
        colId="COL5", type=CellType.INVENTORY, sheet=_products_sheet(), cp_reference_values={}
    )

    assert "cp_reference_values" not in column.model_dump()
    assert "cpReferenceValues" not in column.model_dump(by_alias=True)


# --- Design._get_rows ---


def test_get_rows_types_calculated_property_rows():
    """Test that a calculated property row parses as one, with no inventory ID."""
    sheet = _products_sheet()

    rows = sheet.product_design._get_rows(grid_response=_CALCULATIONS_GRID)

    assert [(r.row_id, r.type) for r in rows] == [
        ("ROW15", CellType.BLANK),
        ("ROW14", CellType.CALCULATED_PROPERTY),
        ("ROW12", CellType.INVENTORY),
        ("ROW1", CellType.TOTAL),
    ]
    assert rows[1].inventory_id is None


# --- Design._grid_to_cell_df ---


@responses.activate
def test_ingredient_basis_column_cells_have_no_inventory_id(offline_session):
    """Test that an ingredient basis column's cells resolve and carry no inventory ID."""
    sheet = _products_sheet(session=offline_session)
    _register_calculations_grid()

    cells = sheet.get_column(column_id="COL7").cells

    assert [(c.row_id, c.value, c.inventory_id) for c in cells] == [
        ("ROW15", "", None),
        ("ROW14", "", None),
        ("ROW12", "30", None),
        ("ROW1", "", None),
    ]


# --- Sheet._writes_calculated_value ---


def _cell(*, column_id: str, row_id: str, cell_type: str, row_type: str | None) -> Cell:
    return Cell(colId=column_id, rowId=row_id, type=cell_type, row_type=row_type, design_id="DES1")


def _changes(*attributes: str) -> list[PatchDatum]:
    return [
        PatchDatum(operation="update", attribute=attribute, new_value="1")
        for attribute in attributes
    ]


_ORDINARY_CELLS = [
    pytest.param(
        _cell(column_id="COL5", row_id="ROW12", cell_type="INV", row_type="INV"),
        id="ingredient-amount",
    ),
    pytest.param(
        _cell(column_id="COL5", row_id="ROW1", cell_type="INV", row_type="TOT"), id="total"
    ),
    pytest.param(
        _cell(column_id="COL5", row_id="ROW15", cell_type="INV", row_type="BLK"),
        id="group-header",
    ),
    pytest.param(
        _cell(column_id="COL5", row_id="ROW2", cell_type="INV", row_type=None),
        id="built-without-row-type",
    ),
]

_CALCULATED_CELLS = [
    pytest.param(
        _cell(column_id="COL5", row_id="ROW14", cell_type="INV", row_type="CPR"),
        id="calculated-property-row",
    ),
    pytest.param(
        _cell(column_id="COL7", row_id="ROW12", cell_type="IBS", row_type="INV"),
        id="ingredient-basis-column",
    ),
    pytest.param(
        _cell(column_id="COL7", row_id="ROW1", cell_type="IBS", row_type="TOT"),
        id="ingredient-basis-total",
    ),
    pytest.param(
        _cell(column_id="COL7", row_id="ROW14", cell_type="IBS", row_type="CPR"), id="both"
    ),
]


def _writes(cell: Cell, changes: list[PatchDatum], rows=(), columns=()) -> bool:
    return Sheet._writes_calculated_value(
        cell=cell, changes=changes, calculated_row_ids=set(rows), basis_column_ids=set(columns)
    )


@pytest.mark.parametrize("cell", _ORDINARY_CELLS)
def test_writes_calculated_value_allows_any_change_to_ordinary_cells(cell):
    """Test that value and calculation changes to cells outside calculated rows and columns pass."""
    assert not _writes(cell, _changes("cell", "calculation"), rows={"ROW14"}, columns={"COL7"})


@pytest.mark.parametrize("cell", _CALCULATED_CELLS)
@pytest.mark.parametrize("attribute", ["cell", "calculation", "minValue", "maxValue"])
def test_writes_calculated_value_blocks_value_changes_to_calculated_cells(cell, attribute):
    """Test that a value, calculation or bound change to a calculated cell is blocked."""
    assert _writes(cell, _changes("cellFormat", attribute))


@pytest.mark.parametrize("cell", _CALCULATED_CELLS)
def test_writes_calculated_value_allows_formatting_calculated_cells(cell):
    """Test that a formatting-only change to a calculated cell is allowed."""
    assert not _writes(cell, _changes("cellFormat"))


@pytest.mark.parametrize(
    "cell",
    [
        pytest.param(
            _cell(column_id="COL5", row_id="ROW14", cell_type="INV", row_type=None),
            id="calculated-property-row-without-row-type",
        ),
        pytest.param(
            _cell(column_id="COL7", row_id="ROW12", cell_type="INV", row_type="INV"),
            id="ingredient-basis-column-typed-as-inventory",
        ),
        pytest.param(
            _cell(column_id="COL7", row_id="ROW12", cell_type="INV", row_type=None),
            id="ingredient-basis-column-untyped",
        ),
    ],
)
def test_writes_calculated_value_trusts_the_sheet_over_the_cell(cell):
    """Test that the sheet's row and column types block a value change the cell's own types hide."""
    assert _writes(cell, _changes("cell"), rows={"ROW14"}, columns={"COL7"})


# --- Sheet.update_cells ---


@responses.activate
def test_update_cells_never_sends_calculated_cells(offline_session):
    """Test that a mixed write sends only ordinary cells and fails the calculated ones."""
    sheet = _products_sheet(session=offline_session)
    _register_calculations_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)
    grid = sheet.product_design.grid
    amount = grid.at["DES1#ROW12", "COL5#INVMO1-001"].model_copy(update={"value": "65"})
    cp = grid.at["DES1#ROW14", "COL5#INVMO1-001"].model_copy(update={"value": "99"})
    basis = grid.at["DES1#ROW12", "COL7#Solids Share"].model_copy(update={"value": "99"})

    with pytest.warns(UserWarning, match="2 cell"):
        updated, failed = sheet.update_cells(refresh=False, cells=[cp, amount, basis])

    assert (updated, failed) == ([amount], [cp, basis])
    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    assert [
        (entry["Id"]["rowId"], entry["Id"]["colId"])
        for entry in json.loads(patches[0].request.body)
    ] == [("ROW12", "COL5")]
    cached = sheet.product_design.grid
    assert cached.at["DES1#ROW14", "COL5#INVMO1-001"].value == "42.5"
    assert cached.at["DES1#ROW12", "COL7#Solids Share"].value == "30"


@responses.activate
def test_update_cells_with_only_calculated_cells_sends_nothing(offline_session):
    """Test that a write of only calculated cells makes no call and fails every cell."""
    sheet = _products_sheet(session=offline_session)
    _register_calculations_grid()
    cp = sheet.product_design.grid.at["DES1#ROW14", "COL5#INVMO1-001"]

    with pytest.warns(UserWarning, match="1 cell"):
        updated, failed = sheet.update_cells(cells=[cp.model_copy(update={"value": "99"})])

    assert updated == []
    assert [(c.row_id, c.column_id) for c in failed] == [("ROW14", "COL5")]
    assert [c.request.method for c in responses.calls] == ["GET"]


@responses.activate
def test_update_cells_refuses_calculated_cells_built_without_sheet_types(offline_session):
    """Test that calculated cells built by hand, untyped or typed as inventory, are not sent."""
    sheet = _products_sheet(session=offline_session)
    _register_calculations_grid()
    cp = Cell(colId="COL5", rowId="ROW14", type="INV", design_id="DES1", value="99")
    basis = Cell(colId="COL7", rowId="ROW12", type="INV", design_id="DES1", value="99")

    with pytest.warns(UserWarning, match="retrying will not write them") as record:
        updated, failed = sheet.update_cells(cells=[cp, basis])

    assert (updated, failed) == ([], [cp, basis])
    assert [c.request.method for c in responses.calls] == ["GET"]
    assert record[0].filename == __file__


@responses.activate
def test_update_cells_without_calculated_cells_does_not_warn(offline_session, recwarn):
    """Test that a write touching no calculated cells emits no warning."""
    sheet = _products_sheet(session=offline_session)
    _register_calculations_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)
    amount = sheet.product_design.grid.at["DES1#ROW12", "COL5#INVMO1-001"]

    sheet.update_cells(refresh=False, cells=[amount.model_copy(update={"value": "65"})])

    assert [w for w in recwarn if issubclass(w.category, UserWarning)] == []


@responses.activate
def test_update_cells_writes_formatting_on_calculated_cells(offline_session):
    """Test that recoloring calculated cells sends their formatting and reports them updated."""
    sheet = _products_sheet(session=offline_session)
    _register_calculations_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)
    grid = sheet.product_design.grid
    yellow = {"bgColor": "#FFFF00"}
    cp = grid.at["DES1#ROW14", "COL5#INVMO1-001"].model_copy(update={"format": yellow})
    basis = grid.at["DES1#ROW12", "COL7#Solids Share"].model_copy(update={"format": yellow})

    updated, failed = sheet.update_cells(refresh=False, cells=[cp, basis])

    assert (updated, failed) == ([cp, basis], [])
    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    assert [
        (entry["Id"]["rowId"], entry["Id"]["colId"], [d["attribute"] for d in entry["data"]])
        for entry in json.loads(patches[0].request.body)
    ] == [("ROW14", "COL5", ["cellFormat"]), ("ROW12", "COL7", ["cellFormat"])]


# --- Sheet._clear_formulation_from_column / Sheet._write_cells_or_raise ---


@responses.activate
def test_clear_formulation_leaves_calculated_property_rows_alone(offline_session, monkeypatch):
    """Test that clearing a formulation column skips calculated property and Total rows."""
    sheet = _products_sheet(session=offline_session)
    _register_calculations_grid()
    column = sheet.get_column(column_id="COL5")
    writes: list[list[Cell]] = []
    monkeypatch.setattr(
        Sheet, "update_cells", lambda self, *, cells, **_: (writes.append(cells), (cells, []))[1]
    )

    cleared = sheet._clear_formulation_from_column(column=column)

    assert [c.row_id for c in cleared] == ["ROW15", "ROW12"]
    assert [[(c.row_id, c.value) for c in cells] for cells in writes] == [
        [("ROW15", ""), ("ROW12", "")]
    ]


def test_write_cells_or_raise_raises_with_the_cells_not_written(monkeypatch):
    """Test that cells reported as failed raise a partial error naming them."""
    sheet = _products_sheet()
    written = _cell(column_id="COL5", row_id="ROW12", cell_type="INV", row_type="INV")
    refused = _cell(column_id="COL5", row_id="ROW14", cell_type="INV", row_type="CPR")
    monkeypatch.setattr(Sheet, "update_cells", lambda self, **_: ([written], [refused]))

    with pytest.raises(AlbertPartialError) as error:
        sheet._write_cells_or_raise(cells=[written, refused])

    assert error.value.failed_items == [{"rowId": "ROW14", "colId": "COL5"}]


def test_write_cells_or_raise_returns_when_every_cell_is_written(monkeypatch):
    """Test that a write with no failed cells returns quietly."""
    sheet = _products_sheet()
    cell = _cell(column_id="COL5", row_id="ROW12", cell_type="INV", row_type="INV")
    calls: list[dict] = []
    monkeypatch.setattr(
        Sheet, "update_cells", lambda self, **kwargs: (calls.append(kwargs), ([cell], []))[1]
    )

    assert sheet._write_cells_or_raise(cells=[cell]) is None
    assert calls == [{"cells": [cell], "refresh": False}]


# --- Sheet._last_top_level_column_id ---


def _column(column_id: str, column_type: str) -> Column:
    return Column(colId=column_id, type=column_type, sheet=_products_sheet())


def test_last_top_level_column_id_skips_trailing_ingredient_basis_columns():
    """Test that new columns anchor on the last formulation, not its ingredient basis column."""
    columns = [_column("COL5", "INV"), _column("COL7", "IBS"), _column("COL6", "INV")]
    columns.append(_column("COL8", "IBS"))

    assert Sheet._last_top_level_column_id(columns=columns) == "COL6"


def test_last_top_level_column_id_returns_last_column_without_ingredient_basis():
    """Test that the last column is the anchor on a sheet without ingredient basis columns."""
    columns = [_column("COL5", "INV"), _column("COL6", "BLK")]

    assert Sheet._last_top_level_column_id(columns=columns) == "COL6"


def test_last_top_level_column_id_returns_none_without_columns():
    """Test that a sheet without columns has no anchor column."""
    assert Sheet._last_top_level_column_id(columns=[]) is None


# --- Sheet._plan_column_moves ---


def _replay(order: list[str], moves: list[tuple[str, str, ColumnPosition]]) -> list[str]:
    """Apply top-level moves the way the sheet does: source goes beside the reference."""
    order = list(order)
    for source_id, reference_id, position in moves:
        order.remove(source_id)
        offset = 1 if position == ColumnPosition.RIGHT_OF else 0
        order.insert(order.index(reference_id) + offset, source_id)
    return order


_CURRENT = ["COL1", "COL5", "COL7", "COL6", "COL8", "COL9"]
_CHILDREN = {"COL7", "COL8"}


def test_plan_column_moves_moves_only_top_level_columns():
    """Test that moves never use an ingredient basis column as source or reference."""
    moves = Sheet._plan_column_moves(
        current_ids=_CURRENT,
        column_ids=["COL1", "COL6", "COL8", "COL9", "COL5", "COL7"],
        child_ids=_CHILDREN,
    )

    assert moves == [
        ("COL6", "COL5", ColumnPosition.LEFT_OF),
        ("COL9", "COL5", ColumnPosition.LEFT_OF),
    ]


def test_plan_column_moves_replay_reaches_requested_order():
    """Test that replaying the planned moves yields the requested top-level order."""
    moves = Sheet._plan_column_moves(
        current_ids=_CURRENT,
        column_ids=["COL9", "COL6", "COL8", "COL1", "COL5", "COL7"],
        child_ids=_CHILDREN,
    )

    assert _replay(["COL1", "COL5", "COL6", "COL9"], moves) == ["COL9", "COL6", "COL1", "COL5"]


def test_plan_column_moves_ignores_where_ingredient_basis_columns_are_listed():
    """Test that listing, omitting, or misplacing ingredient basis columns plans the same moves."""
    listed = Sheet._plan_column_moves(
        current_ids=_CURRENT,
        column_ids=["COL1", "COL6", "COL8", "COL5", "COL7", "COL9"],
        child_ids=_CHILDREN,
    )
    misplaced = Sheet._plan_column_moves(
        current_ids=_CURRENT,
        column_ids=["COL7", "COL1", "COL6", "COL5", "COL9", "COL8"],
        child_ids=_CHILDREN,
    )
    omitted = Sheet._plan_column_moves(
        current_ids=_CURRENT, column_ids=["COL1", "COL6", "COL5", "COL9"], child_ids=_CHILDREN
    )

    assert listed == misplaced == omitted == [("COL6", "COL5", ColumnPosition.LEFT_OF)]


def test_plan_column_moves_returns_no_moves_when_top_level_order_matches():
    """Test that an order differing only in ingredient basis positions plans no moves."""
    moves = Sheet._plan_column_moves(
        current_ids=_CURRENT,
        column_ids=["COL8", "COL1", "COL5", "COL6", "COL9", "COL7"],
        child_ids=_CHILDREN,
    )

    assert moves == []


def test_plan_column_moves_without_children_moves_every_misplaced_column():
    """Test that a sheet without ingredient basis columns reorders as before."""
    moves = Sheet._plan_column_moves(
        current_ids=["COL1", "COL2", "COL3"], column_ids=["COL3", "COL1", "COL2"], child_ids=set()
    )

    assert moves == [("COL3", "COL1", ColumnPosition.LEFT_OF)]
