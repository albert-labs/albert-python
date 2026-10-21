import json

import pandas as pd
import pytest
import responses
from pydantic import ValidationError

from albert.exceptions import AlbertException
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.resources.sheets import (
    Cell,
    CellType,
    Column,
    Component,
    Design,
    DesignType,
    FormulationSpec,
    Row,
    RowConfig,
    RowPosition,
    Sheet,
)
from tests.unit.conftest import UNIT_BASE_URL


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

    sheet.product_design._grid = pd.DataFrame(
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


@responses.activate
def test_get_current_cell_loads_only_the_matching_design_grid(offline_session):
    """Test that the update baseline reads only the grid of the design being patched."""
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
        session=offline_session,
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/products/grid",
        json={
            "Items": [
                {
                    "rowId": "ROW1",
                    "rowUniqueId": "DES1#ROW1",
                    "name": "Row 1",
                    "type": "INV",
                    "Values": [{"colId": "COL1", "value": "7", "id": "INV1", "type": "INV"}],
                }
            ],
            "Formulas": [],
        },
    )

    result = sheet._get_current_cell(
        cell=Cell(colId="COL1", rowId="ROW1", type=CellType.INVENTORY, design_id="DES1")
    )

    assert result is not None
    assert result.value == "7"
    assert len(responses.calls) == 1
    assert sheet.result_design._grid is None
    assert sheet.app_design._grid is None
    assert sheet.process_design._grid is None


def test_get_current_cell_unknown_design_returns_none_without_grid_read():
    """Test that a cell for an unknown design resolves to no baseline without a grid read."""
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[{"albertId": "DES1", "designType": "products", "state": {}}],
        projectId="PRJ1",
    )

    result = sheet._get_current_cell(
        cell=Cell(colId="COL1", rowId="ROW1", type=CellType.INVENTORY, design_id="DES9")
    )

    assert result is None


def _sheet_with_formatted_cell() -> Sheet:
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
    existing = Cell(
        colId="COL1",
        rowId="ROW1",
        value="1",
        type=CellType.INVENTORY,
        design_id="DES1",
        cellFormat={"precision": 2},
    )
    sheet.product_design._grid = pd.DataFrame(
        [[existing]], index=["DES1#ROW1"], columns=["COL1#INV1"]
    )
    return sheet


def test_cell_changes_leave_existing_format_alone_when_unset():
    """AI-1926: the ``{}`` format default must not emit an API-rejected cellFormat delete."""
    sheet = _sheet_with_formatted_cell()
    cell = Cell(colId="COL1", rowId="ROW1", value="5", type=CellType.INVENTORY, design_id="DES1")

    payload = sheet._get_cell_changes(cell=cell)

    assert payload is not None
    attributes = [datum.attribute for datum in payload["data"]]
    assert "cellFormat" not in attributes
    assert all(datum.operation != "delete" for datum in payload["data"])


def test_cell_changes_send_explicit_format_as_update():
    sheet = _sheet_with_formatted_cell()
    cell = Cell(
        colId="COL1",
        rowId="ROW1",
        value="1",
        type=CellType.INVENTORY,
        design_id="DES1",
        cellFormat={"precision": 3},
    )

    payload = sheet._get_cell_changes(cell=cell)

    assert payload is not None
    (datum,) = [d for d in payload["data"] if d.attribute == "cellFormat"]
    assert datum.operation == "update"
    assert datum.new_value == {"precision": 3}


def test_cell_changes_send_format_as_update_when_cell_has_no_prior_format():
    sheet = _sheet_with_formatted_cell()
    current = sheet._get_current_cell(
        cell=Cell(colId="COL1", rowId="ROW1", value="1", type=CellType.INVENTORY, design_id="DES1")
    )
    object.__setattr__(current, "format", {})
    cell = Cell(
        colId="COL1",
        rowId="ROW1",
        value="1",
        type=CellType.INVENTORY,
        design_id="DES1",
        cellFormat={"bgColor": "red"},
    )

    payload = sheet._get_cell_changes(cell=cell)

    assert payload is not None
    (datum,) = [d for d in payload["data"] if d.attribute == "cellFormat"]
    assert datum.operation == "update"
    assert datum.new_value == {"bgColor": "red"}


def test_add_formulation_restores_cleared_column_when_write_fails(monkeypatch):
    """AI-1926: ``clear=True`` must not leave the column blank after a failed write."""
    sheet = _sheet_with_formatted_cell()
    original = Cell(
        colId="COL1", rowId="ROW1", value="7", type=CellType.INVENTORY, design_id="DES1"
    )
    column = Column(colId="COL1", name="F1", type=CellType.INVENTORY, sheet=sheet)
    writes: list[list[Cell]] = []

    def _update_cells(*, cells):
        writes.append(cells)
        if len(writes) == 2:
            raise AlbertException("cellFormat")

    monkeypatch.setattr(Sheet, "columns", property(lambda self: [column]))
    monkeypatch.setattr(Sheet, "get_column", lambda self, **_: column)
    monkeypatch.setattr(Column, "cells", property(lambda self: [original]))
    monkeypatch.setattr(
        Sheet, "update_cells", lambda self, *, cells, **_: _update_cells(cells=cells)
    )
    monkeypatch.setattr(
        Sheet,
        "_ensure_rows_for_components",
        lambda self, **_: {"INV1": ["ROW1"]},
    )
    monkeypatch.setattr(Design, "rows", property(lambda self: []))

    with pytest.raises(AlbertException):
        sheet.add_formulation(
            formulation_name="F1",
            components=[Component(inventory_id="INV1", amount=5.0)],
        )

    assert writes[0][0].value == ""
    assert writes[-1] == [original]


def test_clear_formulation_ignores_empty_grid_padding(monkeypatch):
    """Test clearing a column skips empty grid padding instead of failing."""
    sheet = _empty_sheet()
    original = Cell(
        colId="COL1", rowId="ROW1", value="7", type=CellType.INVENTORY, design_id="DES1"
    )
    column = Column(colId="COL1", name="F1", type=CellType.INVENTORY, sheet=sheet)
    writes: list[list[Cell]] = []

    def _update_cells(*, cells):
        writes.append(cells)
        return cells, []

    monkeypatch.setattr(Column, "cells", property(lambda self: [original, None, float("nan")]))
    monkeypatch.setattr(
        Sheet, "update_cells", lambda self, *, cells, **_: _update_cells(cells=cells)
    )

    cleared = sheet._clear_formulation_from_column(column=column)

    assert cleared == [original]
    assert [[cell.value for cell in cells] for cells in writes] == [[""]]


def _empty_sheet() -> Sheet:
    return Sheet(
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


def test_filter_cells_marks_only_failed_items_as_failed():
    """Test that a partial success with no UpdatedItems key keeps non-failed cells updated."""
    sheet = _empty_sheet()
    cells = [
        Cell(colId="COL1", rowId="ROW1", type=CellType.TOTAL, design_id="DES1"),
        Cell(colId="COL2", rowId="ROW1", type=CellType.TOTAL, design_id="DES1"),
    ]
    updated, failed = sheet._filter_cells(
        cells=cells,
        response_dict={
            "error": "Some values are not updated properly. Try again!",
            "FailedItems": [
                {
                    "id": {"rowId": "ROW1", "colId": "COL2"},
                    "msg": "You cannot edit values in formulas that are locked",
                }
            ],
        },
    )
    assert [cell.column_id for cell in updated] == ["COL1"]
    assert [cell.column_id for cell in failed] == ["COL2"]


def test_filter_cells_ignores_updated_items_column_records():
    """Test that UpdatedItems column records and wrapped failure ids parse correctly."""
    sheet = _empty_sheet()
    cells = [
        Cell(colId="COL5", rowId="ROW1", type=CellType.TOTAL, design_id="DES1"),
        Cell(colId="COL6", rowId="ROW1", type=CellType.TOTAL, design_id="DES1"),
        Cell(colId="COL7", rowId="ROW1", type=CellType.TOTAL, design_id="DES1"),
    ]
    updated, failed = sheet._filter_cells(
        cells=cells,
        response_dict={
            "error": "Some values are not updated properly. Try again!",
            "UpdatedItems": [
                {
                    "PK": "TEN1#DES1",
                    "SK": "COL5",
                    "id": "INVKENV1",
                    "colId": "COL5",
                    "type": "INV",
                    "state": {},
                }
            ],
            "FailedItems": [
                {
                    "id": {"rowId": "ROW1", "colId": "COL6"},
                    "msg": "You cannot edit values in formulas that are locked",
                },
                {
                    "msg": "Some values are not updated properly. Try again!",
                    "id": [{"id": {"rowId": "ROW1", "colId": "COL7"}}],
                },
            ],
        },
    )
    assert [cell.column_id for cell in updated] == ["COL5"]
    assert [cell.column_id for cell in failed] == ["COL6", "COL7"]


@responses.activate
def test_add_formulation_skips_locked_columns_when_extending_totals(monkeypatch, offline_session):
    """A new ingredient row must not rewrite Total formulas on locked columns."""
    sheet = _products_sheet(session=offline_session)
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/products/grid",
        json={
            "Items": [
                {
                    "rowId": "ROW1",
                    "rowUniqueId": "DES1#ROW1",
                    "name": "Total",
                    "type": "TOT",
                    "Values": [
                        {
                            "colId": "COL2",
                            "value": "10",
                            "calculation": "=COL2ROW2",
                            "id": "INVO",
                            "type": "INV",
                        },
                        {
                            "colId": "COL6",
                            "value": "10",
                            "calculation": "=COL6ROW2",
                            "id": "INVL",
                            "type": "INV",
                        },
                    ],
                }
            ],
            "Formulas": [
                {"colId": "COL2", "name": "Open", "state": {}},
                {"colId": "COL6", "name": "Locked", "state": {}},
            ],
        },
    )
    total_row = Row(
        rowId="ROW1",
        type=CellType.TOTAL,
        design=sheet.product_design,
        sheet=sheet,
    )
    new_column = Column(
        colId="COL5", name="New", type=CellType.INVENTORY, sheet=sheet, locked=False
    )
    unlocked = Column(
        colId="COL2", name="Open", type=CellType.INVENTORY, sheet=sheet, locked=False
    )
    locked = Column(colId="COL6", name="Locked", type=CellType.INVENTORY, sheet=sheet, locked=True)
    written: list[list[Cell]] = []

    def _ensure_rows(self, *, formulations_components, product_rows):
        product_rows.append(
            Row(
                rowId="ROW9",
                type=CellType.INVENTORY,
                design=self.product_design,
                sheet=self,
                inventory_id="INVA1",
                name="New ingredient",
            )
        )
        return {"INVA1": ["ROW9"]}

    def _update_cells(self, *, cells, **_):
        written.append(list(cells))
        return ([], [])

    monkeypatch.setattr(Design, "rows", property(lambda self: [total_row]))
    monkeypatch.setattr(Sheet, "columns", property(lambda self: [unlocked, locked]))
    monkeypatch.setattr(Sheet, "add_formulation_columns", lambda self, **_: [new_column])
    monkeypatch.setattr(Sheet, "get_column", lambda self, **_: new_column)
    monkeypatch.setattr(Sheet, "_ensure_rows_for_components", _ensure_rows)
    monkeypatch.setattr(Sheet, "update_cells", _update_cells)

    sheet.add_formulation(
        formulation_name="New",
        components=[Component(inventory_id="INVA1", amount=5.0)],
        clear=False,
    )

    total_column_ids = [
        cell.column_id
        for batch in written
        for cell in batch
        if cell.type == CellType.TOTAL or cell.row_type == CellType.TOTAL
    ]
    assert "COL5" in total_column_ids
    assert "COL2" in total_column_ids
    assert "COL6" not in total_column_ids


def test_reformat_formulation_addition_payload_reads_inventory_id_from_formula_id():
    """Test that the created column's inventory ID comes from its formula entry."""
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[{"albertId": "DES1", "designType": "products", "state": {}}],
        projectId="PRJ1",
    )
    response_json = [
        {
            "type": "INV",
            "name": "Formulation A",
            "referenceId": "COL5",
            "Formulas": [{"formulaId": "INVP623-002", "colId": "COL6"}],
            "childCols": [],
        }
    ]

    result = sheet._reformat_formulation_addition_payload(response_json=response_json)

    assert result == [
        {
            "colId": "COL6",
            "Formulas": [{"formulaId": "INVP623-002", "name": "Formulation A"}],
            "name": "Formulation A",
            "type": "INV",
            "session": None,
            "sheet": sheet,
            "inventory_id": "INVP623-002",
        }
    ]


def test_reformat_formulation_addition_payload_prefers_top_level_id():
    """Test that a top-level id on the item wins over the formula entry."""
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[{"albertId": "DES1", "designType": "products", "state": {}}],
        projectId="PRJ1",
    )
    response_json = [
        {
            "id": "INVP623-002",
            "type": "INV",
            "name": "Formulation A",
            "Formulas": [{"formulaId": "INVP623-999", "colId": "COL6"}],
        }
    ]

    result = sheet._reformat_formulation_addition_payload(response_json=response_json)

    assert result[0]["inventory_id"] == "INVP623-002"


def test_reformat_formulation_addition_payload_maps_each_response_item():
    """Test that each created column keeps its own formula's inventory ID, in order."""
    sheet = Sheet(
        albertId="SHEET1",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[{"albertId": "DES1", "designType": "products", "state": {}}],
        projectId="PRJ1",
    )
    response_json = [
        {
            "type": "INV",
            "name": "Formulation A",
            "referenceId": "COL5",
            "Formulas": [{"formulaId": "INVP623-001", "colId": "COL6"}],
            "childCols": [],
        },
        {
            "type": "INV",
            "name": "Formulation B",
            "referenceId": "COL6",
            "Formulas": [{"formulaId": "INVP623-002", "colId": "COL7"}],
            "childCols": [],
        },
    ]

    result = sheet._reformat_formulation_addition_payload(response_json=response_json)

    assert result == [
        {
            "colId": "COL6",
            "Formulas": [{"formulaId": "INVP623-001", "name": "Formulation A"}],
            "name": "Formulation A",
            "type": "INV",
            "session": None,
            "sheet": sheet,
            "inventory_id": "INVP623-001",
        },
        {
            "colId": "COL7",
            "Formulas": [{"formulaId": "INVP623-002", "name": "Formulation B"}],
            "name": "Formulation B",
            "type": "INV",
            "session": None,
            "sheet": sheet,
            "inventory_id": "INVP623-002",
        },
    ]


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


_PROCESS_SHEET = {
    "albertId": "SHEET1",
    "name": "Test",
    "Formulas": [],
    "hidden": False,
    "Designs": [
        {"albertId": "DES1", "designType": "products", "state": {}},
        {"albertId": "DES2", "designType": "results", "state": {}},
        {"albertId": "DES3", "designType": "apps", "state": {}},
        {"albertId": "DES4", "designType": "process", "state": {}},
    ],
    "projectId": "PRJ1",
}


def _process_sheet(session) -> Sheet:
    sheet = Sheet(**_PROCESS_SHEET, session=session)
    # Nested Designs are not always given the parent session by validators.
    for design in sheet.designs:
        design._session = session
    return sheet


@responses.activate
def test_add_parameter_group_row_empty_process_design_omits_reference(offline_session):
    """Test that the first PRG row on an empty Process Design sends no referenceId/position."""
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/designs/DES4/rows",
        json=[{"rowId": "ROW5", "id": "PRG1", "type": "PRG", "name": "Mix", "labelName": "Mix"}],
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/designs/DES4/grid",
        json={"total": 0, "designId": "DES4", "Items": [], "Formulas": [], "RowSequence": []},
    )

    row = _process_sheet(offline_session).add_parameter_group_row(parameter_group_id="PRG1")

    assert row.row_id == "ROW5"
    assert row.type == CellType.PRG
    posted = [c for c in responses.calls if c.request.method == "POST"]
    assert len(posted) == 1
    assert json.loads(posted[0].request.body) == [{"type": "PRG", "id": "PRG1"}]


@responses.activate
def test_add_parameter_group_row_empty_response_raises(offline_session):
    """Test that an empty create response raises a clear AlbertException."""
    responses.post(f"{UNIT_BASE_URL}/api/v3/designs/DES4/rows", json=[])

    with pytest.raises(AlbertException, match="No rows returned"):
        _process_sheet(offline_session).add_parameter_group_row(
            parameter_group_id="PRG1", reference_id="ROW1"
        )


def test_component_requires_inventory_item_or_id():
    """Test that a Component must be given an inventory_item or an inventory_id."""
    with pytest.raises(ValidationError, match="requires either"):
        Component(amount=1.0)


def test_component_inventory_item_must_have_id():
    """Test that a Component's inventory_item must carry an id."""
    with pytest.raises(ValidationError, match="must include an 'id'"):
        Component(inventory_item=InventoryItem(name="x", category="RawMaterials"), amount=1.0)


def test_component_populates_inventory_id_from_item():
    """Test that inventory_id is set from inventory_item.id when both are omitted/derived."""
    item = InventoryItem(name="x", category=InventoryCategory.RAW_MATERIALS, albertId="INVA1")
    component = Component(inventory_item=item, amount=5.0)
    assert component.inventory_id == "INVA1"


def test_component_accepts_bare_inventory_id():
    """Test that a Component can be constructed from just an inventory_id."""
    component = Component(inventory_id="INVA1", amount=5.0)
    assert component.inventory_id == "INVA1"
    assert component.inventory_item is None


def test_sheet_set_session_propagates_to_designs(offline_session):
    """Test that a Sheet's session is copied onto each of its Designs after init."""
    sheet = Sheet(**_PROCESS_SHEET, session=offline_session)
    assert all(d.session is offline_session for d in sheet.designs)


def test_sheet_set_session_none_leaves_designs_unset():
    """Test that a Sheet built without a session leaves its Designs without one."""
    sheet = Sheet(**_PROCESS_SHEET)
    assert all(d.session is None for d in sheet.designs)


def test_sheet_set_sheet_fields_binds_designs_by_type():
    """Test that each Design is bound to the matching Sheet property by design_type."""
    sheet = Sheet(**_PROCESS_SHEET)

    assert sheet.product_design.id == "DES1"
    assert sheet.result_design.id == "DES2"
    assert sheet.app_design.id == "DES3"
    assert sheet.process_design.id == "DES4"
    # Every design gets a back-reference to its parent sheet.
    assert all(d._sheet is sheet for d in sheet.designs)


def test_sheet_set_sheet_fields_unknown_design_type_binds_nothing():
    """Test that a Design with an unrecognized design_type is not bound to any property."""
    sheet = Sheet(
        albertId="SHEET2",
        name="Test",
        Formulas=[],
        hidden=False,
        Designs=[{"albertId": "DES9", "designType": "other", "state": {}}],
        projectId="PRJ1",
    )
    assert sheet.app_design is None
    assert sheet.product_design is None
    assert sheet.result_design is None
    assert sheet.process_design is None


def test_column_locked_none_coerced_to_false():
    """Test that Column.locked coerces a None input to False before type validation."""
    sheet = Sheet(**_PROCESS_SHEET)
    column = Column(colId="COL1", type=CellType.INVENTORY, sheet=sheet, locked=None)
    assert column.locked is False


def test_column_locked_true_passes_through():
    """Test that an explicit locked=True is preserved."""
    sheet = Sheet(**_PROCESS_SHEET)
    column = Column(colId="COL1", type=CellType.INVENTORY, sheet=sheet, locked=True)
    assert column.locked is True


def test_row_config_coerces_dict_to_row_config():
    """Test that Row.config accepts a plain dict and coerces it to a RowConfig."""
    sheet = Sheet(**_PROCESS_SHEET)
    design = sheet.designs[0]
    row = Row(
        rowId="ROW1",
        type=CellType.APP,
        design=design,
        sheet=sheet,
        config={"option": "left", "value": "APP1"},
    )
    assert isinstance(row.config, RowConfig)
    assert row.config.option == "left"
    assert row.config.value == "APP1"


def test_row_config_accepts_row_config_instance():
    """Test that Row.config passes through an existing RowConfig instance unchanged."""
    sheet = Sheet(**_PROCESS_SHEET)
    design = sheet.designs[0]
    config = RowConfig(option="left", value="APP1")
    row = Row(rowId="ROW1", type=CellType.APP, design=design, sheet=sheet, config=config)
    assert row.config is config


def test_row_config_invalid_value_coerced_to_none():
    """Test that a non-dict, non-RowConfig config value is coerced to None."""
    sheet = Sheet(**_PROCESS_SHEET)
    design = sheet.designs[0]
    row = Row(rowId="ROW1", type=CellType.APP, design=design, sheet=sheet, config="bogus")
    assert row.config is None


def test_move_rows_payload_whole_shape():
    """Test the row-move payload for multiple rows moved below a reference row."""
    assert Sheet._move_rows_payload(
        row_ids=["ROW13", "ROW16"], reference_id="ROW10", position=RowPosition.BELOW
    ) == {
        "data": [
            {
                "operation": "update",
                "attribute": "sequence",
                "sourceId": ["ROW13", "ROW16"],
                "referenceId": "ROW10",
                "position": "below",
            }
        ]
    }


@pytest.mark.parametrize(
    ("position", "expected"),
    [(RowPosition.ABOVE, "above"), (RowPosition.BELOW, "below"), ("above", "above")],
)
def test_move_rows_payload_position(position, expected):
    """Test that the row-move payload serializes enum and string positions to wire values."""
    payload = Sheet._move_rows_payload(row_ids=["ROW2"], reference_id="ROW1", position=position)
    assert payload["data"][0]["position"] == expected


def test_move_rows_rejects_reference_in_moved_rows():
    """Test that move_rows rejects a reference row that is also being moved."""
    sheet = Sheet(**_PROCESS_SHEET)
    with pytest.raises(AlbertException, match="reference_id"):
        sheet.move_rows(row_ids=["ROW1", "ROW2"], reference_id="ROW2", design_id="DES1")


@responses.activate
@pytest.mark.parametrize(
    ("method", "kwargs", "url"),
    [
        (
            "delete_row",
            {"row_id": "ROW1", "design_id": "DES1"},
            "/api/v3/worksheet/design/DES1/rows",
        ),
        (
            "delete_rows",
            {"row_ids": ["ROW1"], "design_id": "DES1"},
            "/api/v3/worksheet/design/DES1/rows",
        ),
        ("delete_column", {"column_id": "COL1"}, "/api/v3/worksheet/sheet/SHEET1/columns"),
        ("delete_columns", {"column_ids": ["COL1"]}, "/api/v3/worksheet/sheet/SHEET1/columns"),
    ],
)
def test_delete_clears_design_level_grid_cache(offline_session, method, kwargs, url):
    """Test that deletes clear cached design grids even when the sheet grid itself is unset."""
    sheet = _products_sheet(session=offline_session)
    design = sheet.product_design
    design._grid = pd.DataFrame(index=["DES1#ROW1"])
    design._rows = [_inv_row(sheet, "ROW1", "INV1")]
    design._columns = [Column(colId="COL1", type=CellType.LKP, sheet=sheet)]
    responses.delete(f"{UNIT_BASE_URL}{url}", status=204)

    getattr(sheet, method)(**kwargs)

    assert design._grid is None
    assert design._rows is None
    assert design._columns is None


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


def _inv_row(sheet: Sheet, row_id: str, inventory_id: str | None) -> Row:
    return Row(
        rowId=row_id,
        type=CellType.INVENTORY,
        design=sheet.product_design,
        sheet=sheet,
        inventory_id=inventory_id,
    )


# --- Sheet._plan_missing_inventory_rows ---


def test_plan_missing_inventory_rows_returns_empty_when_all_components_have_rows():
    """Test that no rows are planned when every component already has a row."""
    sheet = _empty_sheet()
    product_rows = [_inv_row(sheet, "ROW2", "INVA1")]

    missing = Sheet._plan_missing_inventory_rows(
        formulations_components=[[Component(inventory_id="INVA1", amount=1.0)]],
        product_rows=product_rows,
    )

    assert missing == []


def test_plan_missing_inventory_rows_lists_only_ids_without_rows():
    """Test that only inventory IDs lacking a row are planned."""
    sheet = _empty_sheet()
    product_rows = [_inv_row(sheet, "ROW2", "INVA1")]

    missing = Sheet._plan_missing_inventory_rows(
        formulations_components=[
            [
                Component(inventory_id="INVA1", amount=1.0),
                Component(inventory_id="INVA2", amount=2.0),
            ]
        ],
        product_rows=product_rows,
    )

    assert missing == ["INVA2"]


def test_plan_missing_inventory_rows_repeats_id_per_duplicate_component():
    """Test that a duplicated ingredient in one formulation gets one new row per extra use."""
    sheet = _empty_sheet()
    product_rows = [_inv_row(sheet, "ROW2", "INVA1")]
    components = [
        Component(inventory_id="INVA1", amount=1.0),
        Component(inventory_id="INVA1", amount=2.0),
        Component(inventory_id="INVA1", amount=3.0),
    ]

    missing = Sheet._plan_missing_inventory_rows(
        formulations_components=[components], product_rows=product_rows
    )

    assert missing == ["INVA1", "INVA1"]


def test_plan_missing_inventory_rows_shares_rows_across_formulations():
    """Test that row counts take the maximum per formulation, not the sum."""
    formulations_components = [
        [Component(inventory_id="INVA1", amount=1.0), Component(inventory_id="INVA1", amount=2.0)],
        [Component(inventory_id="INVA1", amount=3.0)],
    ]

    missing = Sheet._plan_missing_inventory_rows(
        formulations_components=formulations_components, product_rows=[]
    )

    assert missing == ["INVA1", "INVA1"]


def test_plan_missing_inventory_rows_ignores_rows_without_inventory_id():
    """Test that total and other non-inventory rows do not count as ingredient rows."""
    sheet = _empty_sheet()
    product_rows = [
        Row(rowId="ROW1", type=CellType.TOTAL, design=sheet.product_design, sheet=sheet)
    ]

    missing = Sheet._plan_missing_inventory_rows(
        formulations_components=[[Component(inventory_id="INVA1", amount=1.0)]],
        product_rows=product_rows,
    )

    assert missing == ["INVA1"]


# --- Sheet._build_formulation_total_cells ---


def test_build_formulation_total_cells_builds_one_total_per_column(monkeypatch):
    """Test each new column gets a Total cell summing its components over all rows."""
    sheet = _empty_sheet()
    product_rows = [
        Row(rowId="ROW1", type=CellType.TOTAL, design=sheet.product_design, sheet=sheet),
        _inv_row(sheet, "ROW2", "INVA1"),
        _inv_row(sheet, "ROW3", "INVA2"),
    ]
    col_a = Column(
        colId="COL5", name="FA", type=CellType.INVENTORY, sheet=sheet, inventory_id="INVFA"
    )
    col_b = Column(
        colId="COL6", name="FB", type=CellType.INVENTORY, sheet=sheet, inventory_id="INVFB"
    )
    other = Column(colId="COL2", name="Other", type=CellType.INVENTORY, sheet=sheet)
    monkeypatch.setattr(Sheet, "columns", property(lambda self: [col_a, col_b, other]))

    cells = sheet._build_formulation_total_cells(
        columns_components=[
            (
                col_a,
                [
                    Component(inventory_id="INVA1", amount=70.0),
                    Component(inventory_id="INVA2", amount=30.0),
                ],
            ),
            (col_b, [Component(inventory_id="INVA1", amount=55.0)]),
        ],
        product_rows=product_rows,
        rewrite_other_columns=False,
    )

    assert [(c.column_id, c.row_id, c.value, c.calculation) for c in cells] == [
        ("COL5", "ROW1", "100", "=COL5ROW2+COL5ROW3"),
        ("COL6", "ROW1", "55", "=COL6ROW2+COL6ROW3"),
    ]


def test_build_formulation_total_cells_rewrites_other_unlocked_columns(monkeypatch):
    """Test other unlocked formula columns get their Totals extended to all rows."""
    sheet = _empty_sheet()
    product_rows = [
        Row(rowId="ROW1", type=CellType.TOTAL, design=sheet.product_design, sheet=sheet),
        _inv_row(sheet, "ROW2", "INVA1"),
        _inv_row(sheet, "ROW3", "INVA2"),
    ]
    new_col = Column(colId="COL5", name="FA", type=CellType.INVENTORY, sheet=sheet)
    unlocked = Column(
        colId="COL2", name="Open", type=CellType.INVENTORY, sheet=sheet, locked=False
    )
    locked = Column(colId="COL7", name="Locked", type=CellType.INVENTORY, sheet=sheet, locked=True)
    lookup = Column(colId="COL3", name="Lookup", type=CellType.LKP, sheet=sheet)
    monkeypatch.setattr(
        Sheet, "columns", property(lambda self: [new_col, unlocked, locked, lookup])
    )

    def _total_grid_cell(col_id: str) -> Cell:
        return Cell(
            colId=col_id,
            rowId="ROW1",
            value="1",
            calculation=f"={col_id}ROW2",
            type=CellType.TOTAL,
            row_type=CellType.TOTAL,
            design_id="DES1",
        )

    sheet.product_design._grid = pd.DataFrame(
        {
            "COL2#INVO": [_total_grid_cell("COL2")],
            "COL7#INVL": [_total_grid_cell("COL7")],
            "COL3#Lookup": [_total_grid_cell("COL3")],
        },
        index=["DES1#ROW1"],
    )

    cells = sheet._build_formulation_total_cells(
        columns_components=[(new_col, [Component(inventory_id="INVA1", amount=1.0)])],
        product_rows=product_rows,
        rewrite_other_columns=True,
    )

    by_id = {c.column_id: c for c in cells}
    assert set(by_id) == {"COL5", "COL2"}
    assert by_id["COL2"].calculation == "=COL2ROW2+COL2ROW3"


def test_build_formulation_total_cells_returns_empty_without_total_row():
    """Test that a sheet without a Total row produces no Total cells."""
    sheet = _empty_sheet()
    product_rows = [_inv_row(sheet, "ROW2", "INVA1")]

    cells = sheet._build_formulation_total_cells(
        columns_components=[
            (
                Column(colId="COL5", name="F", type=CellType.INVENTORY, sheet=sheet),
                [Component(inventory_id="INVA1", amount=1.0)],
            )
        ],
        product_rows=product_rows,
        rewrite_other_columns=True,
    )

    assert cells == []


# --- Sheet.add_inventory_rows ---


@responses.activate
def test_add_inventory_rows_posts_all_ids_in_one_call(offline_session):
    """Test that ingredient rows are created with a single array body."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {
                "rowId": "ROW3",
                "id": "INVA2",
                "type": "INV",
                "name": "Ethanol",
                "manufacturer": None,
            },
            {"rowId": "ROW4", "id": "INVA3", "type": "INV", "name": "Water", "manufacturer": None},
        ],
    )

    rows = sheet.add_inventory_rows(inventory_ids=["A2", "INVA3"])

    assert [row.row_id for row in rows] == ["ROW3", "ROW4"]
    assert [row.inventory_id for row in rows] == ["INVA2", "INVA3"]
    assert len(responses.calls) == 1
    assert json.loads(responses.calls[0].request.body) == [
        {"type": "INV", "id": "INVA2", "referenceId": "ROW1", "position": "above"},
        {"type": "INV", "id": "INVA3", "referenceId": "ROW1", "position": "above"},
    ]


@responses.activate
def test_add_inventory_rows_chunks_at_platform_limit(offline_session):
    """Test that more rows than the per-call cap are split across multiple calls."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {
                "rowId": f"ROW{i + 10}",
                "id": f"INVA{i}",
                "type": "INV",
                "name": f"n{i}",
                "manufacturer": None,
            }
            for i in range(24)
        ],
    )
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {"rowId": "ROW99", "id": "INVA24", "type": "INV", "name": "n24", "manufacturer": None}
        ],
    )

    rows = sheet.add_inventory_rows(inventory_ids=[f"INVA{i}" for i in range(25)])

    assert len(rows) == 25
    assert len(responses.calls) == 2
    assert len(json.loads(responses.calls[0].request.body)) == 24
    assert json.loads(responses.calls[1].request.body) == [
        {"type": "INV", "id": "INVA24", "referenceId": "ROW1", "position": "above"}
    ]


@responses.activate
def test_add_inventory_row_normalizes_unprefixed_inventory_id(offline_session):
    """Test a created row carries the normalized INV-prefixed inventory ID."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json={"rowId": "ROW10", "id": "INVA123", "type": "INV", "name": "n", "manufacturer": None},
    )

    row = sheet.add_inventory_row(inventory_id="A123")

    assert row.inventory_id == "INVA123"
    assert json.loads(responses.calls[0].request.body)["id"] == "INVA123"


@responses.activate
def test_add_inventory_rows_short_circuits_on_empty_input(offline_session):
    """Test that an empty list makes no call and returns no rows."""
    sheet = _products_sheet(session=offline_session)

    assert sheet.add_inventory_rows(inventory_ids=[]) == []
    assert len(responses.calls) == 0


# --- Sheet.add_formulations ---


@responses.activate
def test_add_formulations_short_circuits_on_empty_input(offline_session):
    """Test that an empty list makes no calls and returns no columns."""
    sheet = _products_sheet(session=offline_session)

    assert sheet.add_formulations(formulations=[]) == []
    assert len(responses.calls) == 0


def _register_products_grid():
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/products/grid",
        json={
            "Items": [
                {
                    "rowId": "ROW1",
                    "rowUniqueId": "DES1#ROW1",
                    "name": "Total",
                    "type": "TOT",
                    "Values": [
                        {
                            "colId": "COL1",
                            "value": "10",
                            "calculation": "=COL1ROW2",
                            "id": "INVF0",
                            "type": "INV",
                        }
                    ],
                },
                {
                    "rowId": "ROW2",
                    "rowUniqueId": "DES1#ROW2",
                    "name": "Salt",
                    "type": "INV",
                    "id": "INVA1",
                    "Values": [{"colId": "COL1", "value": "10", "id": "INVF0", "type": "INV"}],
                },
            ],
            "Formulas": [{"colId": "COL1", "name": "Existing", "state": {}}],
        },
    )


@responses.activate
def test_add_formulations_batches_row_creation_and_defers_totals(offline_session):
    """Test one row-creation call per bulk build and a single Totals pass at the end."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/sheet/SHEET1/columns",
        json=[
            {
                "name": "FA",
                "type": "INV",
                "id": "INVFA",
                "Formulas": [{"colId": "COL5", "formulaId": "INVFA"}],
            },
            {
                "name": "FB",
                "type": "INV",
                "id": "INVFB",
                "Formulas": [{"colId": "COL6", "formulaId": "INVFB"}],
            },
        ],
    )
    _register_products_grid()
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {
                "rowId": "ROW3",
                "id": "INVA2",
                "type": "INV",
                "name": "Ethanol",
                "manufacturer": None,
            },
            {"rowId": "ROW4", "id": "INVA3", "type": "INV", "name": "Water", "manufacturer": None},
        ],
    )
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    columns = sheet.add_formulations(
        formulations=[
            FormulationSpec(
                name="FA",
                components=[
                    Component(inventory_id="INVA1", amount=70.0),
                    Component(inventory_id="INVA2", amount=30.0),
                ],
            ),
            FormulationSpec(
                name="FB",
                components=[
                    Component(inventory_id="INVA1", amount=55.0),
                    Component(inventory_id="INVA3", amount=45.0),
                ],
            ),
        ]
    )

    assert [col.column_id for col in columns] == ["COL5", "COL6"]

    posts = [c for c in responses.calls if c.request.method == "POST"]
    rows_posts = [c for c in posts if c.request.url.endswith("/rows")]
    assert len(rows_posts) == 1
    assert [entry["id"] for entry in json.loads(rows_posts[0].request.body)] == ["INVA2", "INVA3"]

    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    assert len(patches) == 2
    ingredient_payload = json.loads(patches[0].request.body)
    assert [
        (entry["Id"]["rowId"], entry["Id"]["colId"], entry["data"][0]["newValue"])
        for entry in ingredient_payload
    ] == [
        ("ROW2", "COL5", "70.0"),
        ("ROW3", "COL5", "30.0"),
        ("ROW2", "COL6", "55.0"),
        ("ROW4", "COL6", "45.0"),
    ]
    total_payload = json.loads(patches[1].request.body)
    totals_by_col = {entry["Id"]["colId"]: entry["data"] for entry in total_payload}
    assert set(totals_by_col) == {"COL5", "COL6", "COL1"}
    assert totals_by_col["COL5"] == [
        {"operation": "add", "attribute": "calculation", "newValue": "=COL5ROW2+COL5ROW3+COL5ROW4"}
    ]
    assert totals_by_col["COL1"] == [
        {
            "operation": "update",
            "attribute": "calculation",
            "newValue": "=COL1ROW2+COL1ROW3+COL1ROW4",
            "oldValue": "=COL1ROW2",
        }
    ]

    # The initial load is the only read during the call: columns, rows, and
    # written cells are folded into the cached grid in memory while building.
    gets = [c for c in responses.calls if c.request.method == "GET"]
    assert len(gets) == 1

    # The cache is dropped when the operation completes, so the next read
    # reloads fresh state.
    assert sheet.product_design._grid is None
    _ = sheet.product_design.grid
    assert len([c for c in responses.calls if c.request.method == "GET"]) == 2


# --- Sheet._plan_ordered_component_rows ---


def test_plan_ordered_component_rows_fresh_sheet_creates_one_run_in_order():
    """Test that a fresh sheet plans one anchored-at-default run in component order."""
    assignments, runs, virtual_order = Sheet._plan_ordered_component_rows(
        formulations_components=[
            [
                Component(inventory_id="INVA1", amount=1.0),
                Component(inventory_id="INVA2", amount=2.0),
                Component(inventory_id="INVA1", amount=3.0),
            ]
        ],
        product_rows=[],
    )

    assert assignments == [["__new_0__", "__new_1__", "__new_2__"]]
    assert runs == [
        {
            "anchor": None,
            "inventory_ids": ["INVA1", "INVA2", "INVA1"],
            "keys": ["__new_0__", "__new_1__", "__new_2__"],
        }
    ]
    assert virtual_order == ["__new_0__", "__new_1__", "__new_2__"]


def test_plan_ordered_component_rows_reuses_rows_already_in_order():
    """Test that existing rows are reused when they already follow component order."""
    sheet = _empty_sheet()
    product_rows = [
        Row(rowId="ROW1", type=CellType.TOTAL, design=sheet.product_design, sheet=sheet),
        _inv_row(sheet, "ROW2", "INVA1"),
        _inv_row(sheet, "ROW3", "INVA2"),
    ]

    assignments, runs, virtual_order = Sheet._plan_ordered_component_rows(
        formulations_components=[
            [
                Component(inventory_id="INVA1", amount=1.0),
                Component(inventory_id="INVA2", amount=2.0),
            ]
        ],
        product_rows=product_rows,
    )

    assert assignments == [["ROW2", "ROW3"]]
    assert runs == []
    assert virtual_order == ["ROW1", "ROW2", "ROW3"]


def test_plan_ordered_component_rows_duplicates_rows_that_are_too_early():
    """Test that an ingredient whose row sits before the running position gets a new row."""
    sheet = _empty_sheet()
    product_rows = [
        Row(rowId="ROW1", type=CellType.TOTAL, design=sheet.product_design, sheet=sheet),
        _inv_row(sheet, "ROW2", "INVA2"),
        _inv_row(sheet, "ROW3", "INVA1"),
    ]

    assignments, runs, virtual_order = Sheet._plan_ordered_component_rows(
        formulations_components=[
            [
                Component(inventory_id="INVA1", amount=1.0),
                Component(inventory_id="INVA2", amount=2.0),
            ]
        ],
        product_rows=product_rows,
    )

    assert assignments == [["ROW3", "__new_0__"]]
    assert runs == [{"anchor": "ROW3", "inventory_ids": ["INVA2"], "keys": ["__new_0__"]}]
    assert virtual_order == ["ROW1", "ROW2", "ROW3", "__new_0__"]


def test_plan_ordered_component_rows_starts_a_new_run_per_anchor():
    """Test that creations anchored to different rows become separate runs."""
    sheet = _empty_sheet()
    product_rows = [
        Row(rowId="ROW1", type=CellType.TOTAL, design=sheet.product_design, sheet=sheet),
        _inv_row(sheet, "ROW2", "INVA1"),
    ]

    assignments, runs, virtual_order = Sheet._plan_ordered_component_rows(
        formulations_components=[
            [
                Component(inventory_id="INVA1", amount=1.0),
                Component(inventory_id="INVA2", amount=2.0),
            ],
            [
                Component(inventory_id="INVA1", amount=3.0),
                Component(inventory_id="INVA3", amount=4.0),
            ],
        ],
        product_rows=product_rows,
    )

    assert assignments == [["ROW2", "__new_0__"], ["ROW2", "__new_1__"]]
    assert runs == [
        {"anchor": "ROW2", "inventory_ids": ["INVA2"], "keys": ["__new_0__"]},
        {"anchor": "ROW2", "inventory_ids": ["INVA3"], "keys": ["__new_1__"]},
    ]
    assert virtual_order == ["ROW1", "ROW2", "__new_1__", "__new_0__"]


@responses.activate
def test_add_formulations_enforce_order_creates_runs_in_place(offline_session):
    """Test ordered bulk creation places new rows below their anchor rows."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/sheet/SHEET1/columns",
        json=[
            {
                "name": "FA",
                "type": "INV",
                "id": "INVFA",
                "Formulas": [{"colId": "COL5", "formulaId": "INVFA"}],
            },
            {
                "name": "FB",
                "type": "INV",
                "id": "INVFB",
                "Formulas": [{"colId": "COL6", "formulaId": "INVFB"}],
            },
        ],
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/products/grid",
        json={
            "Items": [
                {
                    "rowId": "ROW1",
                    "rowUniqueId": "DES1#ROW1",
                    "name": "Total",
                    "type": "TOT",
                    "Values": [
                        {
                            "colId": "COL1",
                            "value": "10",
                            "calculation": "=COL1ROW2+COL1ROW3",
                            "id": "INVF0",
                            "type": "INV",
                        }
                    ],
                },
                {
                    "rowId": "ROW2",
                    "rowUniqueId": "DES1#ROW2",
                    "name": "Salt",
                    "type": "INV",
                    "id": "INVA1",
                    "Values": [{"colId": "COL1", "value": "5", "id": "INVF0", "type": "INV"}],
                },
                {
                    "rowId": "ROW3",
                    "rowUniqueId": "DES1#ROW3",
                    "name": "Ethanol",
                    "type": "INV",
                    "id": "INVA2",
                    "Values": [{"colId": "COL1", "value": "5", "id": "INVF0", "type": "INV"}],
                },
            ],
            "Formulas": [{"colId": "COL1", "name": "Existing", "state": {}}],
        },
    )
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {"rowId": "ROW9", "id": "INVA3", "type": "INV", "name": "Water", "manufacturer": None}
        ],
    )
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {"rowId": "ROW10", "id": "INVA1", "type": "INV", "name": "Salt", "manufacturer": None}
        ],
    )
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    columns = sheet.add_formulations(
        enforce_order=True,
        formulations=[
            FormulationSpec(
                name="FA",
                components=[
                    Component(inventory_id="INVA2", amount=50.0),
                    Component(inventory_id="INVA1", amount=50.0),
                ],
            ),
            FormulationSpec(
                name="FB",
                components=[
                    Component(inventory_id="INVA1", amount=60.0),
                    Component(inventory_id="INVA3", amount=40.0),
                ],
            ),
        ],
    )

    assert [col.column_id for col in columns] == ["COL5", "COL6"]

    rows_posts = [
        c
        for c in responses.calls
        if c.request.method == "POST" and c.request.url.endswith("/rows")
    ]
    assert len(rows_posts) == 2
    assert json.loads(rows_posts[0].request.body) == [
        {"type": "INV", "id": "INVA3", "referenceId": "ROW2", "position": "below"}
    ]
    assert json.loads(rows_posts[1].request.body) == [
        {"type": "INV", "id": "INVA1", "referenceId": "ROW3", "position": "below"}
    ]

    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    ingredient_payload = json.loads(patches[0].request.body)
    assert [(entry["Id"]["rowId"], entry["Id"]["colId"]) for entry in ingredient_payload] == [
        ("ROW3", "COL5"),
        ("ROW10", "COL5"),
        ("ROW2", "COL6"),
        ("ROW9", "COL6"),
    ]

    # The cache is dropped when the operation completes, so the next read
    # reloads fresh state.
    assert sheet.product_design._grid is None


@responses.activate
def test_add_formulation_enforce_order_batches_new_rows(offline_session):
    """Test that a single ordered formulation creates its new rows in one call."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/sheet/SHEET1/columns",
        json=[
            {
                "name": "FA",
                "type": "INV",
                "id": "INVFA",
                "Formulas": [{"colId": "COL5", "formulaId": "INVFA"}],
            }
        ],
    )
    _register_products_grid()
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {
                "rowId": "ROW9",
                "id": "INVA2",
                "type": "INV",
                "name": "Ethanol",
                "manufacturer": None,
            },
            {"rowId": "ROW10", "id": "INVA1", "type": "INV", "name": "Salt", "manufacturer": None},
        ],
    )
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    column = sheet.add_formulation(
        formulation_name="FA",
        components=[
            Component(inventory_id="INVA2", amount=50.0),
            Component(inventory_id="INVA1", amount=50.0),
        ],
        enforce_order=True,
        clear=False,
    )

    assert column.column_id == "COL5"
    rows_posts = [
        c
        for c in responses.calls
        if c.request.method == "POST" and c.request.url.endswith("/rows")
    ]
    assert len(rows_posts) == 1
    assert json.loads(rows_posts[0].request.body) == [
        {"type": "INV", "id": "INVA2", "referenceId": "ROW2", "position": "below"},
        {"type": "INV", "id": "INVA1", "referenceId": "ROW2", "position": "below"},
    ]


@responses.activate
def test_add_formulations_creates_contiguous_new_rows_in_one_call(offline_session):
    """Test new rows that are contiguous in the planned order are created in one call."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/sheet/SHEET1/columns",
        json=[
            {
                "name": "FA",
                "type": "INV",
                "id": "INVFA",
                "Formulas": [{"colId": "COL5", "formulaId": "INVFA"}],
            },
            {
                "name": "FB",
                "type": "INV",
                "id": "INVFB",
                "Formulas": [{"colId": "COL6", "formulaId": "INVFB"}],
            },
        ],
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/products/grid",
        json={
            "Items": [
                {
                    "rowId": "ROW1",
                    "rowUniqueId": "DES1#ROW1",
                    "name": "Total",
                    "type": "TOT",
                    "Values": [],
                }
            ],
            "Formulas": [],
        },
    )
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {"rowId": "ROW10", "id": "INVA1", "type": "INV", "name": "Salt", "manufacturer": None},
            {
                "rowId": "ROW11",
                "id": "INVA2",
                "type": "INV",
                "name": "Sugar",
                "manufacturer": None,
            },
            {"rowId": "ROW12", "id": "INVA1", "type": "INV", "name": "Salt", "manufacturer": None},
        ],
    )
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    columns = sheet.add_formulations(
        enforce_order=True,
        formulations=[
            FormulationSpec(
                name="FA",
                components=[
                    Component(inventory_id="INVA1", amount=50.0),
                    Component(inventory_id="INVA2", amount=50.0),
                ],
            ),
            FormulationSpec(
                name="FB",
                components=[
                    Component(inventory_id="INVA2", amount=60.0),
                    Component(inventory_id="INVA1", amount=40.0),
                ],
            ),
        ],
    )

    assert [col.column_id for col in columns] == ["COL5", "COL6"]
    rows_posts = [
        c
        for c in responses.calls
        if c.request.method == "POST" and c.request.url.endswith("/rows")
    ]
    assert len(rows_posts) == 1
    assert json.loads(rows_posts[0].request.body) == [
        {"type": "INV", "id": "INVA1", "referenceId": "ROW1", "position": "below"},
        {"type": "INV", "id": "INVA2", "referenceId": "ROW1", "position": "below"},
        {"type": "INV", "id": "INVA1", "referenceId": "ROW1", "position": "below"},
    ]

    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    ingredient_payload = json.loads(patches[0].request.body)
    assert [(entry["Id"]["rowId"], entry["Id"]["colId"]) for entry in ingredient_payload] == [
        ("ROW10", "COL5"),
        ("ROW11", "COL5"),
        ("ROW11", "COL6"),
        ("ROW12", "COL6"),
    ]


@responses.activate
def test_update_cells_applies_writes_to_the_cached_grid(offline_session):
    """Test that written values land in the cached grid without a refetch."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    cell = sheet.product_design.grid.at["DES1#ROW2", "COL1#INVF0"]
    updated, failed = sheet.update_cells(
        refresh=False, cells=[cell.model_copy(update={"value": "25"})]
    )

    assert len(updated) == 1
    assert failed == []
    cached_grid = sheet.product_design.grid
    assert cached_grid.at["DES1#ROW2", "COL1#INVF0"].value == "25"
    assert cached_grid.at["DES1#ROW1", "COL1#INVF0"].value == "25"
    assert len([c for c in responses.calls if c.request.method == "GET"]) == 1


@responses.activate
def test_update_cells_keeps_failed_cells_out_of_the_cache(offline_session):
    """Test that a partially rejected write only applies the accepted cells."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(
        f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values",
        status=206,
        json={
            "error": "Some values are not updated properly. Try again!",
            "FailedItems": [{"id": {"rowId": "ROW2", "colId": "COL1"}, "msg": "locked"}],
        },
    )

    cell = sheet.product_design.grid.at["DES1#ROW2", "COL1#INVF0"]
    updated, failed = sheet.update_cells(
        refresh=False, cells=[cell.model_copy(update={"value": "25"})]
    )

    assert updated == []
    assert len(failed) == 1
    cached_grid = sheet.product_design.grid
    assert cached_grid.at["DES1#ROW2", "COL1#INVF0"].value == "10"
    assert cached_grid.at["DES1#ROW1", "COL1#INVF0"].value == "10"


@responses.activate
def test_add_inventory_rows_registers_rows_in_the_cached_grid(offline_session):
    """Test new ingredient rows appear in the cached grid without a refetch."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/design/DES1/rows",
        json=[
            {
                "rowId": "ROW3",
                "id": "INVA2",
                "type": "INV",
                "name": "Ethanol",
                "manufacturer": None,
            }
        ],
    )

    _ = sheet.product_design.rows  # load the cache
    rows = sheet.add_inventory_rows(inventory_ids=["INVA2"])

    assert [row.row_id for row in rows] == ["ROW3"]
    assert [row.row_id for row in sheet.product_design.rows] == ["ROW3", "ROW1", "ROW2"]
    assert list(sheet.product_design.grid.index) == ["DES1#ROW3", "DES1#ROW1", "DES1#ROW2"]
    assert len([c for c in responses.calls if c.request.method == "GET"]) == 1


@responses.activate
def test_update_cells_tracks_applied_values_as_the_next_baseline(offline_session):
    """Test that a second write diffs against the applied value without a refetch."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    cell = sheet.product_design.grid.at["DES1#ROW2", "COL1#INVF0"]
    sheet.update_cells(refresh=False, cells=[cell.model_copy(update={"value": "25"})])
    sheet.update_cells(refresh=False, cells=[cell.model_copy(update={"value": "40"})])

    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    second_payload = json.loads(patches[1].request.body)
    assert second_payload[0]["data"][0]["oldValue"] == "25"
    assert second_payload[0]["data"][0]["newValue"] == "40"
    cached_grid = sheet.product_design.grid
    assert cached_grid.at["DES1#ROW2", "COL1#INVF0"].value == "40"
    assert cached_grid.at["DES1#ROW1", "COL1#INVF0"].value == "40"
    assert len([c for c in responses.calls if c.request.method == "GET"]) == 1


@responses.activate
def test_update_cells_caches_amounts_the_way_the_sheet_stores_them(offline_session):
    """Test that written amounts render like a refetch: as numbers, not written strings."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    cell = sheet.product_design.grid.at["DES1#ROW2", "COL1#INVF0"]
    sheet.update_cells(
        refresh=False,
        cells=[cell.model_copy(update={"value": "80.0", "min_value": "5.0", "max_value": "95.5"})],
    )

    cached = sheet.product_design.grid.at["DES1#ROW2", "COL1#INVF0"]
    assert cached.value == "80"
    assert cached.min_value == "5.000000000"
    assert cached.max_value == "95.500000000"


@responses.activate
def test_update_cells_refresh_default_discards_the_cache(offline_session):
    """Test a direct write drops the cached grid so the next read reloads it."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)
    _register_products_grid()

    cell = sheet.product_design.grid.at["DES1#ROW2", "COL1#INVF0"]
    updated, failed = sheet.update_cells(cells=[cell.model_copy(update={"value": "25"})])

    assert len(updated) == 1
    assert failed == []
    assert sheet.product_design._grid is None
    _ = sheet.product_design.grid
    assert len([c for c in responses.calls if c.request.method == "GET"]) == 2


@responses.activate
def test_update_cells_drops_the_cache_for_unknown_rows(offline_session):
    """Test that a write to a row the cache does not know forces a fresh read."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)
    _register_products_grid()

    _ = sheet.product_design.grid  # load the cache
    updated, failed = sheet.update_cells(
        refresh=False,
        cells=[
            Cell(
                colId="COL1",
                rowId="ROW99",
                value="5",
                type=CellType.INVENTORY,
                design_id="DES1",
                row_type=CellType.INVENTORY,
            )
        ],
    )

    assert len(updated) == 1
    assert failed == []
    # The design's caches were dropped, so the next read fetched fresh state.
    _ = sheet.product_design.grid
    assert len([c for c in responses.calls if c.request.method == "GET"]) == 2


@responses.activate
def test_update_cells_groups_large_writes_into_platform_sized_calls(offline_session):
    """Test that a write of more than 200 cells is split at the platform guardrail."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    _ = sheet.product_design.grid  # load the cache
    cells = [
        Cell(
            colId="COL1",
            rowId=f"ROW{1000 + i}",
            value=str(i),
            type=CellType.INVENTORY,
            design_id="DES1",
        )
        for i in range(450)
    ]
    updated, failed = sheet.update_cells(cells=cells)

    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    assert [len(json.loads(c.request.body)) for c in patches] == [200, 200, 50]
    assert len(updated) == 450
    assert failed == []


@responses.activate
def test_update_cells_packs_two_changes_per_entry(offline_session):
    """Test a combined value-and-calculation clear travels as a single entry."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    cell = sheet.product_design.grid.at["DES1#ROW1", "COL1#INVF0"]
    assert cell.calculation == "=COL1ROW2"
    updated, failed = sheet.update_cells(
        cells=[cell.model_copy(update={"value": "", "calculation": ""})]
    )

    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    assert len(patches) == 1
    body = json.loads(patches[0].request.body)
    assert len(body) == 1
    assert body[0]["Id"] == {"rowId": "ROW1", "colId": "COL1"}
    assert [(d["attribute"], d["operation"]) for d in body[0]["data"]] == [
        ("calculation", "delete"),
        ("cell", "delete"),
    ]
    assert len(updated) == 1
    assert failed == []


@responses.activate
def test_update_cells_splits_non_calculation_changes_into_single_change_entries(offline_session):
    """Test a value+bounds write on a plain cell travels as one change per entry."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    cell = sheet.product_design.grid.at["DES1#ROW2", "COL1#INVF0"]
    assert cell.calculation in (None, "")
    updated, failed = sheet.update_cells(
        cells=[cell.model_copy(update={"value": "20", "min_value": "1", "max_value": "30"})]
    )

    patches = [c for c in responses.calls if c.request.method == "PATCH"]
    assert len(patches) == 3
    for patch, attribute in zip(patches, ["cell", "minValue", "maxValue"], strict=True):
        body = json.loads(patch.request.body)
        assert len(body) == 1
        assert body[0]["Id"] == {"rowId": "ROW2", "colId": "COL1"}
        assert [d["attribute"] for d in body[0]["data"]] == [attribute]
    assert len(updated) == 1
    assert failed == []


@responses.activate
def test_add_formulation_columns_groups_large_additions_and_preserves_order(offline_session):
    """Test that adding many columns splits at 25 per call and keeps the requested order."""
    sheet = _products_sheet(session=offline_session)
    _register_products_grid()

    names = [f"F{i}" for i in range(60)]
    for offset, count in ((0, 25), (25, 25), (50, 10)):
        responses.post(
            f"{UNIT_BASE_URL}/api/v3/worksheet/sheet/SHEET1/columns",
            json=[
                {
                    "name": names[offset + j],
                    "type": "INV",
                    "id": f"INVF{offset + j}",
                    "Formulas": [
                        {"colId": f"COL{100 + offset + j}", "formulaId": f"INVF{offset + j}"}
                    ],
                }
                for j in range(count)
            ],
        )

    columns = sheet.add_formulation_columns(formulation_names=names)

    posts = [c for c in responses.calls if c.request.method == "POST"]
    bodies = [json.loads(c.request.body) for c in posts]
    assert [len(body) for body in bodies] == [25, 25, 10]
    assert bodies[0][0]["referenceId"] == "COL1"
    assert bodies[1][0]["referenceId"] == "COL124"
    assert bodies[2][0]["referenceId"] == "COL149"
    assert [col.name for col in columns] == names


@responses.activate
def test_add_formulations_clear_reuses_existing_columns(offline_session):
    """Test that clear=True rebuilds an existing named column instead of adding one."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/sheet/SHEET1/columns",
        json=[
            {
                "name": "FB",
                "type": "INV",
                "id": "INVFB",
                "Formulas": [{"colId": "COL5", "formulaId": "INVFB"}],
            },
        ],
    )
    # The grid is re-read after the cleared column's write drops the cache; the
    # second read reflects the platform state with the new column present.
    grid_calls = {"count": 0}

    def _grid_callback(request):
        grid_calls["count"] += 1
        if grid_calls["count"] == 1:
            return (
                200,
                {},
                json.dumps(
                    {
                        "Items": [
                            {
                                "rowId": "ROW1",
                                "rowUniqueId": "DES1#ROW1",
                                "name": "Total",
                                "type": "TOT",
                                "Values": [
                                    {
                                        "colId": "COL1",
                                        "value": "10",
                                        "calculation": "=COL1ROW2",
                                        "id": "INVF0",
                                        "type": "INV",
                                    }
                                ],
                            },
                            {
                                "rowId": "ROW2",
                                "rowUniqueId": "DES1#ROW2",
                                "name": "Salt",
                                "type": "INV",
                                "id": "INVA1",
                                "Values": [
                                    {"colId": "COL1", "value": "10", "id": "INVF0", "type": "INV"}
                                ],
                            },
                        ],
                        "Formulas": [{"colId": "COL1", "name": "Existing", "state": {}}],
                    }
                ),
            )
        return (
            200,
            {},
            json.dumps(
                {
                    "Items": [
                        {
                            "rowId": "ROW1",
                            "rowUniqueId": "DES1#ROW1",
                            "name": "Total",
                            "type": "TOT",
                            "Values": [
                                {
                                    "colId": "COL1",
                                    "value": "10",
                                    "calculation": "=COL1ROW2",
                                    "id": "INVF0",
                                    "type": "INV",
                                },
                                {"colId": "COL5", "value": "", "id": "INVFB", "type": "INV"},
                            ],
                        },
                        {
                            "rowId": "ROW2",
                            "rowUniqueId": "DES1#ROW2",
                            "name": "Salt",
                            "type": "INV",
                            "id": "INVA1",
                            "Values": [
                                {"colId": "COL5", "value": "", "id": "INVFB", "type": "INV"}
                            ],
                        },
                    ],
                    "Formulas": [
                        {"colId": "COL1", "name": "Existing", "state": {}},
                        {"colId": "COL5", "name": "FB", "state": {}},
                    ],
                }
            ),
        )

    responses.add_callback(
        responses.GET, f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/products/grid", _grid_callback
    )
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    columns = sheet.add_formulations(
        formulations=[
            FormulationSpec(
                name="Existing", components=[Component(inventory_id="INVA1", amount=99.0)]
            ),
            FormulationSpec(name="FB", components=[Component(inventory_id="INVA1", amount=5.0)]),
        ]
    )

    # Only the genuinely new name adds a column.
    posts = [c for c in responses.calls if c.request.method == "POST"]
    assert len(posts) == 1
    assert [entry["name"] for entry in json.loads(posts[0].request.body)] == ["FB"]

    # Results follow the requested order: reused column first, then the new one.
    assert [col.column_id for col in columns] == ["COL1", "COL5"]

    patches = [json.loads(c.request.body) for c in responses.calls if c.request.method == "PATCH"]
    assert len(patches) == 3
    # The existing column is emptied before the new amounts land.
    assert [
        (entry["Id"]["rowId"], entry["Id"]["colId"], entry["data"][0]["operation"])
        for entry in patches[0]
    ] == [("ROW2", "COL1", "delete")]
    assert {
        (entry["Id"]["rowId"], entry["Id"]["colId"], entry["data"][0]["newValue"])
        for entry in patches[1]
    } == {("ROW2", "COL1", "99.0"), ("ROW2", "COL5", "5.0")}


@responses.activate
def test_add_formulations_clear_false_adds_new_columns(offline_session):
    """Test that clear=False adds a new column even when the name already exists."""
    sheet = _products_sheet(session=offline_session)
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/worksheet/sheet/SHEET1/columns",
        json=[
            {
                "name": "Existing",
                "type": "INV",
                "id": "INVFA2",
                "Formulas": [{"colId": "COL5", "formulaId": "INVFA2"}],
            },
        ],
    )
    _register_products_grid()
    responses.patch(f"{UNIT_BASE_URL}/api/v3/worksheet/DES1/values", status=204)

    columns = sheet.add_formulations(
        formulations=[
            FormulationSpec(
                name="Existing", components=[Component(inventory_id="INVA1", amount=99.0)]
            )
        ],
        clear=False,
    )

    posts = [c for c in responses.calls if c.request.method == "POST"]
    assert len(posts) == 1
    assert [entry["name"] for entry in json.loads(posts[0].request.body)] == ["Existing"]
    assert [col.column_id for col in columns] == ["COL5"]
    # No clearing write: the first patch already carries the new amount.
    first_patch = json.loads(
        [c for c in responses.calls if c.request.method == "PATCH"][0].request.body
    )
    assert first_patch[0]["data"][0]["newValue"] == "99.0"
