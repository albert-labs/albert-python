import pytest

from albert.resources.projects import Project, ReferenceFormula, ReferenceFormulaType


@pytest.mark.parametrize(
    "raw_status, expected",
    [
        ("ACTIVE", "active"),
        ("Active", "active"),
        ("closed - success", "closed - success"),
        (None, None),
    ],
)
def test_project_status_validator_lowercases_strings(raw_status, expected):
    """Test Project.status lowercases string input and passes through non-string values."""
    project = Project(description="Test project", status=raw_status)
    assert project.status == expected


def test_project_status_excluded_from_dump():
    """Test Project.status stays out of the wire payload despite being settable."""
    project = Project(description="Test project", status="Active")
    dumped = project.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert "status" not in dumped


def test_reference_formula_wire_deserialization():
    """Test ReferenceFormula deserializes wire camelCase fields correctly."""
    wire_data = {
        "projectId": "PRO123",
        "worksheetId": "WKS456",
        "inventoryId": "INV789",
        "inventoryName": "Water Base A",
        "parentProjectId": "PRO123",
        "isExternalFormula": False,
        "referenceFormulaType": "Original",
    }
    rf = ReferenceFormula.model_validate(wire_data)
    assert rf.project_id == "PRO123"
    assert rf.sheet_id == "WKS456"
    assert rf.inventory_id == "INV789"
    assert rf.inventory_name == "Water Base A"
    assert rf.parent_project_id == "PRO123"
    assert rf.is_external_formula is False
    assert rf.reference_formula_type == "Original"


def test_reference_formula_linked_deserialization_omitted_sheet():
    """Test linked ReferenceFormula parses cleanly when worksheetId is absent."""
    wire_data = {
        "projectId": "PRO123",
        "inventoryId": "INV789",
        "parentProjectId": "PRO456",
        "isExternalFormula": True,
        "referenceFormulaType": ReferenceFormulaType.CONTROL,
    }
    rf = ReferenceFormula.model_validate(wire_data)
    assert rf.project_id == "PRO123"
    assert rf.sheet_id is None
    assert rf.inventory_name is None
    assert rf.parent_project_id == "PRO456"
    assert rf.is_external_formula is True
    assert rf.reference_formula_type == "Control"


def test_reference_formula_custom_type_string_accepted():
    """Test ReferenceFormula accepts custom non-enum designation strings."""
    rf = ReferenceFormula(
        project_id="PRO123",
        inventory_id="INV789",
        is_external_formula=False,
        reference_formula_type="CustomBaseline",
    )
    assert rf.reference_formula_type == "CustomBaseline"
    dumped = rf.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["referenceFormulaType"] == "CustomBaseline"
    assert dumped["projectId"] == "PRO123"
    assert dumped["inventoryId"] == "INV789"
