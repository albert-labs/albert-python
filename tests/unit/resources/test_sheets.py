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
    Row,
    RowConfig,
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
    sheet._grid = pd.DataFrame([[existing]], index=["DES1#ROW1"], columns=["COL1#INV1"])
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
    monkeypatch.setattr(Sheet, "update_cells", lambda self, *, cells: _update_cells(cells=cells))
    monkeypatch.setattr(Sheet, "_get_row_id_for_component", lambda self, **_: "ROW1")
    monkeypatch.setattr(Design, "rows", property(lambda self: []))

    with pytest.raises(AlbertException):
        sheet.add_formulation(
            formulation_name="F1",
            components=[Component(inventory_id="INV1", amount=5.0)],
        )

    assert writes[0][0].value == ""
    assert writes[-1] == [original]


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
