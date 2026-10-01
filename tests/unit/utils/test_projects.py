"""Unit tests for project and reference formula utility helpers."""

import pytest

from albert.resources.projects import ReferenceFormulaType
from albert.utils.projects import (
    build_default_smart_dataset_scope,
    in_project_reference_formula_payload,
    linked_reference_formula_payload,
    reference_formula_path,
    reference_formula_payload,
)


def test_reference_formula_path_in_project() -> None:
    """Test reference formula path formats sheet key segment when sheet_id is provided."""
    path = reference_formula_path(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
    )
    assert path == "/api/v3/projects/PRO123/referenceFormulas/WKS456/INV789"


def test_reference_formula_path_linked() -> None:
    """Test reference formula path maps to external segment when sheet_id is None."""
    path = reference_formula_path(
        project_id="PRO123",
        sheet_id=None,
        inventory_id="INV789",
    )
    assert path == "/api/v3/projects/PRO123/referenceFormulas/external/INV789"


def test_in_project_reference_formula_payload() -> None:
    """Test in-project reference formula payload includes sheet, host parent, and flags."""
    payload = in_project_reference_formula_payload(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
        reference_formula_type=ReferenceFormulaType.ORIGINAL,
    )
    assert payload == {
        "worksheetId": "WKS456",
        "parentProjectId": "PRO123",
        "inventoryId": "INV789",
        "isExternalFormula": False,
        "referenceFormulaType": "Original",
    }


def test_linked_reference_formula_payload() -> None:
    """Test linked reference formula payload sets source parent, external flag, and omits sheet."""
    payload = linked_reference_formula_payload(
        parent_project_id="PRO456",
        inventory_id="INV789",
        reference_formula_type=ReferenceFormulaType.CONTROL,
    )
    assert payload == {
        "parentProjectId": "PRO456",
        "inventoryId": "INV789",
        "isExternalFormula": True,
        "referenceFormulaType": "Control",
    }
    assert "worksheetId" not in payload


def test_reference_formula_payload_custom_string_type() -> None:
    """Test reference formula payload builder tolerates arbitrary string type designations."""
    in_project = reference_formula_payload(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
        reference_formula_type="CustomBaseline",
    )
    assert in_project["referenceFormulaType"] == "CustomBaseline"

    linked = reference_formula_payload(
        parent_project_id="PRO456",
        inventory_id="INV789",
        reference_formula_type="CustomBaseline",
    )
    assert linked["referenceFormulaType"] == "CustomBaseline"


def test_reference_formula_payload_missing_required_ids() -> None:
    """Test reference_formula_payload raises ValueError when required project IDs are omitted."""
    with pytest.raises(ValueError, match="project_id is required"):
        reference_formula_payload(
            sheet_id="WKS123",
            inventory_id="INV123",
            reference_formula_type=ReferenceFormulaType.ORIGINAL,
        )

    with pytest.raises(ValueError, match="parent_project_id is required"):
        reference_formula_payload(
            sheet_id=None,
            inventory_id="INV123",
            reference_formula_type=ReferenceFormulaType.CONTROL,
        )


def test_build_default_smart_dataset_scope_target_parent_map() -> None:
    """Test default smart dataset scope maps every target to the host project."""
    scope = build_default_smart_dataset_scope(
        project_id="PRO1",
        target_ids=["TAR1", "TAR2"],
    )
    assert scope.project_ids == ["PRO1"]
    assert scope.target_ids == ["TAR1", "TAR2"]
    assert scope.target_parent_ids == {"TAR1": "PRO1", "TAR2": "PRO1"}
    assert scope.sheet_ids is None


def test_build_default_smart_dataset_scope_sheet_ids_none() -> None:
    """Test default smart dataset scope explicitly sets sheet_ids to None."""
    scope = build_default_smart_dataset_scope(project_id="PRO1")
    assert scope.sheet_ids is None


def test_build_default_smart_dataset_scope_deduped_linked_projects() -> None:
    """Test default smart dataset scope appends deduped linked parent project IDs."""
    scope = build_default_smart_dataset_scope(
        project_id="PRO1",
        target_ids=["TAR1"],
        linked_parent_project_ids=["PRO2", "PRO3", "PRO2", "PRO1"],
    )
    assert scope.project_ids == ["PRO1", "PRO2", "PRO3"]
    assert scope.target_ids == ["TAR1"]
    assert scope.target_parent_ids == {"TAR1": "PRO1"}


def test_build_default_smart_dataset_scope_empty_targets() -> None:
    """Test default smart dataset scope handles empty target list cleanly."""
    scope = build_default_smart_dataset_scope(
        project_id="PRO1",
        target_ids=[],
        linked_parent_project_ids=None,
    )
    assert scope.project_ids == ["PRO1"]
    assert scope.target_ids == []
    assert scope.target_parent_ids == {}
    assert scope.sheet_ids is None
