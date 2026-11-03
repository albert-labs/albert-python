"""Unit tests for the request routes of the v3 and v4 design-run collections.

These guard the additive v4 split: the v3 collection must keep its routes while the v4
collection targets the ``design`` service, with only the validate suffix differing.
"""

import json
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from albert.collections.design_runs import DesignRunCollection, DesignRunV4Collection
from albert.resources.design import DesignMethod
from albert.resources.design_runs import DesignRun, DesignRunState
from tests.unit.conftest import UNIT_BASE_URL

SDT = "SDT1"
INSIGHT = {"name": "run", "category": "Generate", "albertId": "INS1"}
VALIDATION = {"valid": True, "violations": []}

ROUTES = [
    (DesignRunCollection, "/api/v3/designruns", "/api/v3/designruns/validate"),
    (DesignRunV4Collection, "/api/v4/design/runs", "/api/v4/design/runs/validation"),
]


@pytest.mark.parametrize(("cls", "create_path", "validate_path"), ROUTES)
@pytest.mark.parametrize("method", ["create_optimization", "create_doe"])
@responses.activate
def test_create_posts_to_collection_route(
    offline_session, cls, create_path, validate_path, method
):
    """Test that create methods post to the collection's base route."""
    responses.post(f"{UNIT_BASE_URL}{create_path}", json=INSIGHT)

    getattr(cls(session=offline_session), method)(smart_dataset_id=SDT)

    assert len(responses.calls) == 1
    assert json.loads(responses.calls[0].request.body)["smartDatasetId"] == SDT


@pytest.mark.parametrize(("cls", "create_path", "validate_path"), ROUTES)
@pytest.mark.parametrize("method", ["validate_optimization", "validate_doe"])
@responses.activate
def test_validate_posts_to_collection_validate_route(
    offline_session, cls, create_path, validate_path, method
):
    """Test that validate methods post to the collection's validate route."""
    responses.post(f"{UNIT_BASE_URL}{validate_path}", json=VALIDATION)

    result = getattr(cls(session=offline_session), method)(smart_dataset_id=SDT)

    assert len(responses.calls) == 1
    assert result.valid is True


RUNS = f"{UNIT_BASE_URL}/api/v4/design/runs"
RUN = {
    "id": "DSR123",
    "schemaVersion": 1,
    "name": "Clearcoat sweep",
    "description": "old",
    "parentId": "PRO456",
    "method": "generate",
    "state": "complete",
    "smartDatasetId": "SDT1",
    "objectives": {"TAR1": {"operator": "gte", "value": 95, "weight": None}},
    "settings": {"numCandidatesSelected": 20},
    "resultSetId": "DCS9",
    "status": "active",
    "version": 3,
    "created": {"at": "2026-10-01T10:00:00Z", "by": "USR1"},
}


@pytest.fixture
def runs(offline_session) -> DesignRunV4Collection:
    return DesignRunV4Collection(session=offline_session)


@responses.activate
def test_get_by_id_parses_the_run_and_keeps_the_uuid_case(runs):
    """Test that only the id prefix is uppercased and the run is parsed."""
    uuid = "0b7e2c1a-4f3d-4c8e-9a51-2d6f8b9e1c47"
    responses.get(f"{RUNS}/DSR{uuid}", json={**RUN, "id": f"DSR{uuid}"})

    run = runs.get_by_id(id=f"dsr{uuid}")

    assert responses.calls[0].request.url == f"{RUNS}/DSR{uuid}"
    assert run.state == DesignRunState.COMPLETE
    assert run.method == DesignMethod.GENERATE
    assert run.result_set_id == "DCS9"
    assert run.objectives["TAR1"].weight == 1.0
    assert run.settings.num_candidates_selected == 20


@responses.activate
def test_get_by_id_parses_error_violations(runs):
    """Test that a failed run exposes its violations, including newer codes."""
    violations = [{"code": "result_persistence_failed", "message": "m", "components": ["x"]}]
    responses.get(f"{RUNS}/DSR123", json={**RUN, "state": "error", "violations": violations})

    run = runs.get_by_id(id="DSR123")

    assert run.violations[0].code == "result_persistence_failed"
    assert run.violations[0].components == ["x"]


@responses.activate
def test_get_all_sends_filters_and_follows_the_last_key_cursor(runs):
    """Test that listing sends the filters and pages with lastKey."""
    responses.get(RUNS, json={"items": [RUN], "lastKey": "k1"})
    responses.get(RUNS, json={"items": [{**RUN, "id": "DSR2"}]})

    listed = list(
        runs.get_all(
            parent_id="PRO456", state=DesignRunState.COMPLETE, method=DesignMethod.GENERATE
        )
    )

    assert [r.id for r in listed] == ["DSR123", "DSR2"]
    assert parse_qs(urlparse(responses.calls[0].request.url).query) == {
        "parentId": ["PRO456"],
        "state": ["complete"],
        "method": ["generate"],
    }
    assert parse_qs(urlparse(responses.calls[1].request.url).query)["lastKey"] == ["k1"]


@responses.activate
def test_get_all_with_only_parent_id_sends_no_other_filters_and_honours_max_items(runs):
    """Test that unset state and method are omitted and max_items caps the iterator."""
    responses.get(RUNS, json={"items": [RUN, {**RUN, "id": "DSR2"}], "lastKey": "k1"})

    assert len(list(runs.get_all(parent_id="PRO456", max_items=1))) == 1
    assert len(responses.calls) == 1
    assert parse_qs(urlparse(responses.calls[0].request.url).query) == {"parentId": ["PRO456"]}


@responses.activate
def test_update_patches_only_name_and_description(runs):
    """Test that update reads the run, then patches just the changed field."""
    responses.get(f"{RUNS}/DSR123", json=RUN)
    responses.patch(f"{RUNS}/DSR123", json={**RUN, "description": "new"})

    updated = runs.update(design_run=DesignRun(id="DSR123", description="new"))

    assert responses.calls[1].request.method == "PATCH"
    assert json.loads(responses.calls[1].request.body)["data"] == [
        {"operation": "update", "attribute": "description", "oldValue": "old", "newValue": "new"}
    ]
    assert updated.description == "new"


@responses.activate
def test_update_sends_nothing_when_nothing_changed(runs):
    """Test that an update with no changes does not patch."""
    responses.get(f"{RUNS}/DSR123", json=RUN)

    runs.update(design_run=DesignRun(id="DSR123", name="Clearcoat sweep"))

    assert len(responses.calls) == 1


@responses.activate
@pytest.mark.parametrize("method", ["create_optimization", "create_doe"])
def test_v4_create_returns_a_design_run_and_sends_ownership_fields(runs, method):
    """Test that v4 create sends parentId and the space/config ids and returns a DesignRun."""
    responses.post(RUNS, json={**RUN, "state": "queued"}, status=201)

    run = getattr(runs, method)(
        smart_dataset_id=SDT,
        parent_id="pro456",
        design_space_id="DSP1",
        design_model_config_id="DMC1",
    )

    assert json.loads(responses.calls[0].request.body) == {
        "method": "generate" if method == "create_optimization" else "space_filling",
        "smartDatasetId": SDT,
        "parentId": "PRO456",
        "designSpaceId": "DSP1",
        "designModelConfigId": "DMC1",
    }
    assert isinstance(run, DesignRun)
    assert run.state == DesignRunState.QUEUED


@responses.activate
@pytest.mark.parametrize("method", ["validate_optimization", "validate_doe"])
def test_v4_validate_sends_ownership_fields(runs, method):
    """Test that v4 validate sends parentId and the space/config ids."""
    responses.post(f"{RUNS}/validation", json=VALIDATION)

    result = getattr(runs, method)(
        smart_dataset_id=SDT, parent_id="PRO456", design_space_id="DSP1"
    )

    body = json.loads(responses.calls[0].request.body)
    assert body["parentId"] == "PRO456"
    assert body["designSpaceId"] == "DSP1"
    assert "designModelConfigId" not in body
    assert result.valid is True


@responses.activate
def test_v3_create_still_returns_an_insight_without_ownership_fields(offline_session):
    """Test that the v3 collection is unchanged: BTInsight back, no new fields sent."""
    responses.post(f"{UNIT_BASE_URL}/api/v3/designruns", json=INSIGHT)

    result = DesignRunCollection(session=offline_session).create_doe(smart_dataset_id=SDT)

    assert type(result).__name__ == "BTInsight"
    assert set(json.loads(responses.calls[0].request.body)) == {"method", "smartDatasetId"}


def test_reference_not_published_violation_code_parses():
    """Test that the reference_not_published violation code is a known code."""
    run = DesignRun(
        **{
            **RUN,
            "state": "error",
            "violations": [{"code": "reference_not_published", "message": "m"}],
        }
    )

    assert run.violations[0].code == "reference_not_published"
