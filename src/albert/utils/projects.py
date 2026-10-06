"""Helper utilities for projects, reference formulas, and smart project scopes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from albert.core.shared.identifiers import (
    InventoryId,
    ProjectId,
    TargetId,
    WorksheetId,
)
from albert.resources.smart_datasets import SmartDatasetScope

if TYPE_CHECKING:
    from albert.resources.projects import ReferenceFormulaType


def reference_formula_path(
    project_id: ProjectId | None = None,
    sheet_id: WorksheetId | None = None,
    inventory_id: InventoryId | None = None,
    *,
    base_path: str = "/api/v3/projects",
) -> str:
    """Construct the endpoint path for addressing a reference formula.

    When ``sheet_id`` is ``None``, maps to the literal ``external`` segment
    representing cross-project linked reference formulas.

    Parameters
    ----------
    project_id : ProjectId, optional
        The project ID holding the designation.
    sheet_id : WorksheetId, optional
        The sheet ID for an in-project designation, or None for linked formulas.
    inventory_id : InventoryId, optional
        The formula inventory ID.
    base_path : str, optional
        The base API route for projects (default ``"/api/v3/projects"``).

    Returns
    -------
    str
        The formatted endpoint URL path.
    """
    key_segment = sheet_id if sheet_id is not None else "external"
    return f"{base_path}/{project_id}/referenceFormulas/{key_segment}/{inventory_id}"


def in_project_reference_formula_payload(
    *,
    project_id: ProjectId,
    sheet_id: WorksheetId,
    inventory_id: InventoryId,
    reference_formula_type: ReferenceFormulaType | str,
) -> dict[str, Any]:
    """Build the payload for designating an in-project reference formula.

    Parameters
    ----------
    project_id : ProjectId
        The project ID the formula and worksheet belong to.
    sheet_id : WorksheetId
        The sheet ID within the project worksheet where the formula is designated.
    inventory_id : InventoryId
        The inventory ID of the formula to designate.
    reference_formula_type : ReferenceFormulaType | str
        The role of the reference formula (e.g. Original, Leading, Final, Control).

    Returns
    -------
    dict[str, Any]
        Wire-format JSON payload for the POST /projects/{id}/referenceFormulas request.
    """
    type_val = (
        reference_formula_type.value
        if hasattr(reference_formula_type, "value")
        else str(reference_formula_type)
    )
    return {
        "worksheetId": sheet_id,
        "parentProjectId": project_id,
        "inventoryId": inventory_id,
        "isExternalFormula": False,
        "referenceFormulaType": type_val,
    }


def linked_reference_formula_payload(
    *,
    parent_project_id: ProjectId,
    inventory_id: InventoryId,
    reference_formula_type: ReferenceFormulaType | str,
) -> dict[str, Any]:
    """Build the payload for designating a linked cross-project reference formula.

    Parameters
    ----------
    parent_project_id : ProjectId
        The source project ID where the formula originates (must differ from host project).
    inventory_id : InventoryId
        The inventory ID of the external formula.
    reference_formula_type : ReferenceFormulaType | str
        The role of the reference formula (e.g. Control, Other, or a custom label).

    Returns
    -------
    dict[str, Any]
        Wire-format JSON payload for the POST /projects/{id}/referenceFormulas request.
    """
    type_val = (
        reference_formula_type.value
        if hasattr(reference_formula_type, "value")
        else str(reference_formula_type)
    )
    return {
        "parentProjectId": parent_project_id,
        "inventoryId": inventory_id,
        "isExternalFormula": True,
        "referenceFormulaType": type_val,
    }


def build_default_smart_dataset_scope(
    *,
    project_id: ProjectId,
    target_ids: list[TargetId] | None = None,
    linked_parent_project_ids: list[ProjectId] | None = None,
) -> SmartDatasetScope:
    """Build the default SmartDatasetScope for a smart project dataset update.

    Includes the host project ID and any parent projects of linked reference formulas
    (deduped), all target IDs in scope mapped to the host project, and explicit null
    sheet IDs matching the UI sync behavior.

    Parameters
    ----------
    project_id : ProjectId
        The host project ID.
    target_ids : list[TargetId], optional
        The target IDs currently in the smart project's scope.
    linked_parent_project_ids : list[ProjectId], optional
        Parent project IDs from all cross-project linked reference formulas.

    Returns
    -------
    SmartDatasetScope
        The populated smart dataset scope ready for build/sync requests.
    """
    targets = list(target_ids) if target_ids else []

    project_ids: list[ProjectId] = [project_id]
    seen_projects = {project_id}
    if linked_parent_project_ids:
        for parent_id in linked_parent_project_ids:
            if parent_id and parent_id not in seen_projects:
                seen_projects.add(parent_id)
                project_ids.append(parent_id)

    return SmartDatasetScope(
        project_ids=project_ids,
        target_ids=targets,
        sheet_ids=None,
        target_parent_ids={t: project_id for t in targets},
    )
