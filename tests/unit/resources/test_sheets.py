import json

import pandas as pd
import pytest
import responses

from albert.exceptions import AlbertException
from albert.resources.sheets import (
    Cell,
    CellType,
    DesignType,
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
