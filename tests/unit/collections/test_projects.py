"""Unit tests for ProjectCollection private helpers.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_acl_patch_operations`` and the
starred-project record matching / duplicate-star detection helpers, with no
I/O to fake.
"""

import json

import pytest
import requests
import responses

from albert.collections.projects import ProjectCollection
from albert.exceptions import BadRequestError
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.personalization import Personalization, PersonalizationCategory
from albert.resources.projects import ReferenceFormulaType
from tests.unit.conftest import UNIT_BASE_URL


def test_no_acl_changes_emit_no_ops(offline_session) -> None:
    """Test that identical ACL lists produce no operations."""
    existing = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR)]
    updated = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == []


def test_both_none_emit_no_ops(offline_session) -> None:
    """Test that both ACL lists being None (unset) produces no operations."""
    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=None, updated=None
    )

    assert ops == []


def test_new_acl_entry_emits_add_op_with_full_dump(offline_session) -> None:
    """Test that a newly added ACL entry emits a single add op with the full entry."""
    existing: list[ACL] = []
    updated = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == [
        {
            "attribute": "ACL",
            "operation": "add",
            "newValue": [{"id": "USR1", "fgc": "ProjectViewer"}],
        }
    ]


def test_removed_acl_entry_emits_delete_op_with_id_only(offline_session) -> None:
    """Test that a removed ACL entry emits a delete op carrying only its id."""
    existing = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER)]
    updated: list[ACL] = []

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == [
        {
            "attribute": "ACL",
            "operation": "delete",
            "oldValue": [{"id": "USR1"}],
        }
    ]


def test_changed_fgc_on_existing_entry_emits_fgc_update(offline_session) -> None:
    """Test that changing an existing entry's access level emits a per-id fgc update."""
    existing = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER)]
    updated = [ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == [
        {
            "attribute": "fgc",
            "id": "USR1",
            "operation": "update",
            "oldValue": "ProjectViewer",
            "newValue": "ProjectEditor",
        }
    ]


def test_unchanged_fgc_on_existing_entry_emits_no_op(offline_session) -> None:
    """Test that an entry present in both lists with the same fgc emits no operation."""
    existing = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER),
        ACL(id="USR2", fgc=AccessControlLevel.PROJECT_OWNER),
    ]
    updated = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER),
        ACL(id="USR2", fgc=AccessControlLevel.PROJECT_OWNER),
    ]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == []


def test_add_delete_and_update_combine_in_one_call(offline_session) -> None:
    """Test a mixed add/delete/update ACL diff emits one op per change kind."""
    existing = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_VIEWER),
        ACL(id="USR2", fgc=AccessControlLevel.PROJECT_OWNER),
    ]
    updated = [
        ACL(id="USR1", fgc=AccessControlLevel.PROJECT_EDITOR),  # changed
        ACL(id="USR3", fgc=AccessControlLevel.PROJECT_VIEWER),  # added
        # USR2 removed
    ]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    add_ops = [op for op in ops if op["operation"] == "add"]
    delete_ops = [op for op in ops if op["operation"] == "delete"]
    update_ops = [op for op in ops if op["operation"] == "update"]

    assert add_ops == [
        {
            "attribute": "ACL",
            "operation": "add",
            "newValue": [{"id": "USR3", "fgc": "ProjectViewer"}],
        }
    ]
    assert delete_ops == [
        {
            "attribute": "ACL",
            "operation": "delete",
            "oldValue": [{"id": "USR2"}],
        }
    ]
    assert update_ops == [
        {
            "attribute": "fgc",
            "id": "USR1",
            "operation": "update",
            "oldValue": "ProjectViewer",
            "newValue": "ProjectEditor",
        }
    ]


def test_none_fgc_on_both_sides_emits_no_op(offline_session) -> None:
    """Test that an entry with fgc unset on both sides emits no fgc update."""
    existing = [ACL(id="USR1", fgc=None)]
    updated = [ACL(id="USR1", fgc=None)]

    ops = ProjectCollection(session=offline_session)._generate_acl_patch_operations(
        existing=existing, updated=updated
    )

    assert ops == []


def test_reference_formula_path_in_project() -> None:
    """Test reference formula path with a sheet ID formats sheet key segment."""
    path = ProjectCollection._reference_formula_path(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
    )
    assert path == "/api/v3/projects/PRO123/referenceFormulas/WKS456/INV789"


def test_reference_formula_path_linked() -> None:
    """Test reference formula path without a sheet ID maps to external segment."""
    path = ProjectCollection._reference_formula_path(
        project_id="PRO123",
        sheet_id=None,
        inventory_id="INV789",
    )
    assert path == "/api/v3/projects/PRO123/referenceFormulas/external/INV789"


def test_in_project_reference_formula_payload() -> None:
    """Test in-project reference formula payload contains required sheet and parent."""
    payload = ProjectCollection._in_project_reference_formula_payload(
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
    """Test linked reference formula payload omits worksheetId and flags external."""
    payload = ProjectCollection._linked_reference_formula_payload(
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
    """Test reference formula payloads tolerate arbitrary string type designations."""
    in_project = ProjectCollection._in_project_reference_formula_payload(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
        reference_formula_type="CustomBaseline",
    )
    assert in_project["referenceFormulaType"] == "CustomBaseline"

    linked = ProjectCollection._linked_reference_formula_payload(
        parent_project_id="PRO456",
        inventory_id="INV789",
        reference_formula_type="CustomBaseline",
    )
    assert linked["referenceFormulaType"] == "CustomBaseline"


@pytest.mark.parametrize(
    "project_id, sheet_id, linked_only, match",
    [
        (None, "WKS123", False, "sheet_id and linked_only require project_id"),
        (None, None, True, "sheet_id and linked_only require project_id"),
        ("PRO123", "WKS123", True, "sheet_id and linked_only are mutually exclusive"),
    ],
)
def test_get_all_reference_formulas_argument_validation(
    offline_session, project_id, sheet_id, linked_only, match
) -> None:
    """Test get_all_reference_formulas enforces argument exclusivity and requirements."""
    collection = ProjectCollection(session=offline_session)
    with pytest.raises(ValueError, match=match):
        collection.get_all_reference_formulas(
            project_id=project_id,
            sheet_id=sheet_id,
            linked_only=linked_only,
        )


@responses.activate
def test_set_reference_formula_wire(offline_session) -> None:
    """Test set_reference_formula sends expected POST body and parses response."""
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        json={
            "projectId": "PRO123",
            "worksheetId": "WKS456",
            "inventoryId": "INV789",
            "inventoryName": "Formula A",
            "parentProjectId": "PRO123",
            "isExternalFormula": False,
            "referenceFormulaType": "Original",
        },
        status=200,
    )
    collection = ProjectCollection(session=offline_session)
    rf = collection.set_reference_formula(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
        reference_formula_type=ReferenceFormulaType.ORIGINAL,
    )
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call.request.method == "POST"
    assert json.loads(call.request.body) == {
        "worksheetId": "WKS456",
        "parentProjectId": "PRO123",
        "inventoryId": "INV789",
        "isExternalFormula": False,
        "referenceFormulaType": "Original",
    }
    assert rf.project_id == "PRO123"
    assert rf.sheet_id == "WKS456"
    assert rf.inventory_id == "INV789"
    assert rf.reference_formula_type == "Original"
    assert rf.is_external_formula is False


@responses.activate
def test_link_reference_formula_wire(offline_session) -> None:
    """Test link_reference_formula sends expected POST body without worksheetId."""
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        json={
            "projectId": "PRO123",
            "inventoryId": "INV789",
            "parentProjectId": "PRO456",
            "isExternalFormula": True,
            "referenceFormulaType": "Control",
        },
        status=200,
    )
    collection = ProjectCollection(session=offline_session)
    rf = collection.link_reference_formula(
        project_id="PRO123",
        parent_project_id="PRO456",
        inventory_id="INV789",
        reference_formula_type=ReferenceFormulaType.CONTROL,
    )
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call.request.method == "POST"
    assert json.loads(call.request.body) == {
        "parentProjectId": "PRO456",
        "inventoryId": "INV789",
        "isExternalFormula": True,
        "referenceFormulaType": "Control",
    }
    assert rf.project_id == "PRO123"
    assert rf.sheet_id is None
    assert rf.parent_project_id == "PRO456"
    assert rf.is_external_formula is True


@responses.activate
def test_get_all_reference_formulas_tenant_wide_no_limit(offline_session) -> None:
    """Test get_all_reference_formulas tenant-wide route sends no query parameters."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/referenceFormulas",
        json={
            "total": 1,
            "Items": [
                {
                    "projectId": "PRO123",
                    "worksheetId": "WKS456",
                    "inventoryId": "INV789",
                    "isExternalFormula": False,
                    "referenceFormulaType": "Original",
                }
            ],
        },
    )
    collection = ProjectCollection(session=offline_session)
    items = list(collection.get_all_reference_formulas())
    assert len(items) == 1
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call.request.method == "GET"
    assert "limit" not in (call.request.params or {})


@responses.activate
def test_get_all_reference_formulas_project_scoped_filters(offline_session) -> None:
    """Test get_all_reference_formulas passes sheet_id or external query param."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        json={"Items": []},
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        json={"Items": []},
    )
    collection = ProjectCollection(session=offline_session)

    # sheet_id filter
    list(collection.get_all_reference_formulas(project_id="PRO123", sheet_id="WKS456"))
    assert responses.calls[0].request.params == {"worksheetId": "WKS456"}

    # linked_only filter
    list(collection.get_all_reference_formulas(project_id="PRO123", linked_only=True))
    assert responses.calls[1].request.params == {"worksheetId": "external"}


@responses.activate
def test_update_reference_formula_type_wire(offline_session) -> None:
    """Test update_reference_formula_type sends PATCH datum and returns hydrated ReferenceFormula."""
    responses.patch(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas/WKS456/INV789",
        status=204,
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        json={
            "Items": [
                {
                    "projectId": "PRO123",
                    "worksheetId": "WKS456",
                    "inventoryId": "INV789",
                    "inventoryName": "Formula A",
                    "parentProjectId": "PRO123",
                    "isExternalFormula": False,
                    "referenceFormulaType": "Leading",
                }
            ]
        },
    )
    responses.patch(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas/external/INV789",
        status=204,
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        json={
            "Items": [
                {
                    "projectId": "PRO123",
                    "inventoryId": "INV789",
                    "inventoryName": "Formula External",
                    "parentProjectId": "PRO456",
                    "isExternalFormula": True,
                    "referenceFormulaType": "CustomType",
                }
            ]
        },
    )
    collection = ProjectCollection(session=offline_session)

    # With expected_type on sheet formula
    rf1 = collection.update_reference_formula_type(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
        reference_formula_type=ReferenceFormulaType.LEADING,
        expected_type=ReferenceFormulaType.ORIGINAL,
    )
    call1 = responses.calls[0]
    assert json.loads(call1.request.body) == {
        "data": [
            {
                "operation": "update",
                "attribute": "referenceFormulaType",
                "newValue": "Leading",
                "oldValue": "Original",
            }
        ]
    }
    assert rf1.reference_formula_type == "Leading"
    assert rf1.sheet_id == "WKS456"
    assert rf1.inventory_name == "Formula A"
    assert rf1.parent_project_id == "PRO123"
    assert rf1.is_external_formula is False

    # Linked formula (no sheet_id) without expected_type preserves external parent_project_id
    rf2 = collection.update_reference_formula_type(
        project_id="PRO123",
        inventory_id="INV789",
        reference_formula_type="CustomType",
    )
    call2 = responses.calls[2]
    assert json.loads(call2.request.body) == {
        "data": [
            {
                "operation": "update",
                "attribute": "referenceFormulaType",
                "newValue": "CustomType",
            }
        ]
    }
    assert rf2.reference_formula_type == "CustomType"
    assert rf2.sheet_id is None
    assert rf2.inventory_name == "Formula External"
    assert rf2.parent_project_id == "PRO456"
    assert rf2.is_external_formula is True


@responses.activate
def test_update_reference_formula_type_fallback_on_get_error(offline_session) -> None:
    """Test update_reference_formula_type falls back to constructed model when fetch fails."""
    responses.patch(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas/WKS456/INV789",
        status=204,
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        status=500,
        json={"error": "Internal error"},
    )
    collection = ProjectCollection(session=offline_session)
    rf = collection.update_reference_formula_type(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
        reference_formula_type=ReferenceFormulaType.LEADING,
    )
    assert rf.reference_formula_type == "Leading"
    assert rf.sheet_id == "WKS456"
    assert rf.project_id == "PRO123"


@responses.activate
def test_delete_reference_formula_wire(offline_session) -> None:
    """Test delete_reference_formula sends DELETE to expected paths."""
    responses.delete(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas/WKS456/INV789",
        status=204,
    )
    responses.delete(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas/external/INV789",
        status=204,
    )
    collection = ProjectCollection(session=offline_session)

    collection.delete_reference_formula(
        project_id="PRO123",
        sheet_id="WKS456",
        inventory_id="INV789",
    )
    assert responses.calls[0].request.method == "DELETE"

    collection.delete_reference_formula(
        project_id="PRO123",
        inventory_id="INV789",
    )
    assert responses.calls[1].request.method == "DELETE"


def test_starred_record_ids_match_project_case_insensitively() -> None:
    """Test that starred-record lookup matches the project ID regardless of case."""
    records = [
        Personalization(
            id="USP1", category=PersonalizationCategory.STARRED_PROJECTS, saved_id="PRO1"
        ),
        Personalization(
            id="USP2", category=PersonalizationCategory.STARRED_PROJECTS, saved_id="pro2"
        ),
        Personalization(
            id="USP3", category=PersonalizationCategory.STARRED_PROJECTS, saved_id="PRO2"
        ),
    ]

    ids = ProjectCollection._starred_record_ids(records=records, project_id="PRO2")

    assert ids == ["USP2", "USP3"]


def test_starred_record_ids_empty_when_project_not_starred() -> None:
    """Test that an unstarred project yields no record IDs, so unstar does nothing."""
    records = [
        Personalization(
            id="USP1", category=PersonalizationCategory.STARRED_PROJECTS, saved_id="PRO1"
        ),
        Personalization(category=PersonalizationCategory.STARRED_PROJECTS, saved_id="PRO2"),
    ]

    ids = ProjectCollection._starred_record_ids(records=records, project_id="PRO2")

    assert ids == []


def _bad_request(body: object) -> BadRequestError:
    request = requests.Request("POST", f"{UNIT_BASE_URL}/api/v3/personalization").prepare()
    response = requests.Response()
    response.status_code = 400
    response.request = request
    response._content = json.dumps(body).encode()
    return BadRequestError(response)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"title": "Bad Request", "errors": [{"msg": "savedId already exist"}]}, True),
        ({"title": "Bad Request", "errors": [{"msg": "projectId PRO1 does not exist"}]}, False),
        ({"title": "Bad Request"}, False),
    ],
)
def test_is_already_starred_error(body: object, expected: bool) -> None:
    """Test that only the duplicate-star error is recognized as already starred."""
    assert ProjectCollection._is_already_starred_error(_bad_request(body)) is expected
