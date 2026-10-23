"""Unit tests for SmartProject resource behavior."""

import json as _json

import pytest
import responses

from albert.resources.smart_projects import SmartProject, SmartProjectScope
from tests.unit.conftest import UNIT_BASE_URL


@responses.activate
def test_update_dataset_catches_albert_http_error(offline_session, caplog) -> None:
    """Test update_dataset catches AlbertHTTPError, logs warning, and completes sync."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        status=404,
        json={"error": "Not found"},
    )
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/addDatasetToProject",
        status=200,
        json={},
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/getSmartProject",
        status=200,
        json={"smart": [{"scope": {"targetIds": ["TAR1"]}}]},
    )

    smart = SmartProject(
        project_id="PRO123",
        session=offline_session,
        scope=SmartProjectScope(target_ids=["TAR1"]),
    )

    smart.update_dataset()

    assert "Could not fetch linked reference formulas for project PRO123" in caplog.text
    # Verify addDatasetToProject was still called with host project scope
    post_call = next(c for c in responses.calls if c.request.method == "POST")
    body = _json.loads(post_call.request.body)
    assert body["scope"]["projectIds"] == ["PRO123"]


@responses.activate
def test_update_dataset_surfaces_non_http_errors(offline_session, monkeypatch) -> None:
    """Test update_dataset does not swallow non-AlbertHTTPError exceptions."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        status=200,
        json={"Items": [{"parentProjectId": "PRO456"}]},
    )

    smart = SmartProject(
        project_id="PRO123",
        session=offline_session,
        scope=SmartProjectScope(target_ids=["TAR1"]),
    )

    # Simulate an unexpected programming error inside the try block (e.g., json decoding crash)
    def broken_json(*args, **kwargs):
        raise TypeError("Unexpected type error")

    monkeypatch.setattr(
        offline_session, "get", lambda *args, **kwargs: type("Resp", (), {"json": broken_json})()
    )

    with pytest.raises(TypeError, match="Unexpected type error"):
        smart.update_dataset()


@responses.activate
def test_update_dataset_includes_linked_parent_projects(offline_session) -> None:
    """Test update_dataset includes parent projects of linked reference formulas in scope."""
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/referenceFormulas",
        status=200,
        json={"Items": [{"parentProjectId": "PRO456"}]},
    )
    responses.post(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/addDatasetToProject",
        status=200,
        json={},
    )
    responses.get(
        f"{UNIT_BASE_URL}/api/v3/projects/PRO123/getSmartProject",
        status=200,
        json={"smart": [{"scope": {"targetIds": ["TAR1"]}}]},
    )

    smart = SmartProject(
        project_id="PRO123",
        session=offline_session,
        scope=SmartProjectScope(target_ids=["TAR1"]),
    )

    smart.update_dataset()

    post_call = next(c for c in responses.calls if c.request.method == "POST")
    body = _json.loads(post_call.request.body)
    assert body["scope"]["projectIds"] == ["PRO123", "PRO456"]
