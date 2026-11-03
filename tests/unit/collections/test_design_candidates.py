"""Unit tests for the design candidate-set and candidate collections: the requests they
send and how they read responses, against a faked HTTP layer."""

from urllib.parse import parse_qs, urlparse

import pytest
import responses

from albert.collections.design_candidate_sets import DesignCandidateSetCollection
from albert.collections.design_candidates import DesignCandidateCollection
from albert.resources.design_candidate_sets import CandidateSetSourceType
from albert.resources.design_candidates import IngredientAmountInput, ParameterInput
from tests.unit.conftest import UNIT_BASE_URL

SETS = f"{UNIT_BASE_URL}/api/v4/design/candidate-sets"
CANDIDATES = f"{UNIT_BASE_URL}/api/v4/design/candidates"
UUID = "0b7e2c1a-4f3d-4c8e-9a51-2d6f8b9e1c47"
SET = {
    "id": "DCS2201",
    "schemaVersion": 1,
    "parentId": "PRO456",
    "source": {"sourceType": "design_run", "sourceId": "DSR1042"},
    "smartDatasetId": "SDT789",
    "objectives": {"TAR1": {"operator": "gte", "value": 95}},
    "status": "active",
    "version": 1,
}
CANDIDATE = {
    "id": "DCN1",
    "schemaVersion": 1,
    "candidateSetId": "DCS2201",
    "parentId": "PRO456",
    "inputs": [
        {"type": "ingredientAmount", "ingredient": "INV001", "value": 0.231},
        {
            "type": "parameter",
            "parameter": "DAT01#PRM07#UNI12",
            "ref": {
                "parameterId": "PRM07",
                "dataTemplateId": "DAT01",
                "parameterGroupId": None,
                "unitId": "UNI12",
            },
            "value": "cured",
        },
    ],
    "predictions": {
        "TAR1": {
            "value": 96.5,
            "uncertainty": 1.2,
            "dataType": "numeric",
            "quantiles": {"levels": [0.1, 0.9], "values": [95.0, 98.0]},
        }
    },
    "acquisition": {"score": 0.8, "perObjective": {"TAR1": 0.8}},
    "rank": 1,
    "status": "active",
    "version": 1,
}


@pytest.fixture
def sets(offline_session) -> DesignCandidateSetCollection:
    return DesignCandidateSetCollection(session=offline_session)


@pytest.fixture
def candidates(offline_session) -> DesignCandidateCollection:
    return DesignCandidateCollection(session=offline_session)


def _query(call) -> dict:
    return parse_qs(urlparse(call.request.url).query)


@responses.activate
def test_set_get_by_id_normalises_the_id_and_parses_the_set(sets):
    """Test that only the id prefix is uppercased and the set is parsed."""
    responses.get(f"{SETS}/DCS{UUID}", json={**SET, "id": f"DCS{UUID}"})

    candidate_set = sets.get_by_id(id=f"dcs{UUID}")

    assert responses.calls[0].request.url == f"{SETS}/DCS{UUID}"
    assert candidate_set.source.source_type == CandidateSetSourceType.DESIGN_RUN
    assert candidate_set.source.source_id == "DSR1042"
    assert candidate_set.design_space_id is None
    assert candidate_set.objectives["TAR1"].weight == 1.0


@responses.activate
def test_set_get_candidates_pages_with_last_key(sets):
    """Test that a set's candidates come from the nested route and follow lastKey."""
    responses.get(f"{SETS}/DCS2201/candidates", json={"items": [CANDIDATE], "lastKey": "k1"})
    responses.get(f"{SETS}/DCS2201/candidates", json={"items": [{**CANDIDATE, "id": "DCN2"}]})

    listed = list(sets.get_candidates(id="DCS2201"))

    assert [c.id for c in listed] == ["DCN1", "DCN2"]
    assert _query(responses.calls[1])["lastKey"] == ["k1"]


@responses.activate
def test_candidate_get_all_sends_the_set_id_and_parses_rank_and_inputs(candidates):
    """Test that listing sends candidateSetId and parses inputs, predictions and rank."""
    responses.get(CANDIDATES, json={"items": [CANDIDATE]})

    (candidate,) = list(candidates.get_all(candidate_set_id="dcs2201"))

    assert _query(responses.calls[0]) == {"candidateSetId": ["DCS2201"]}
    assert candidate.rank == 1
    assert isinstance(candidate.inputs[0], IngredientAmountInput)
    assert candidate.inputs[0].value == 0.231
    assert isinstance(candidate.inputs[1], ParameterInput)
    assert candidate.inputs[1].ref.unit_id == "UNI12"
    assert candidate.inputs[1].value == "cured"
    assert candidate.predictions["TAR1"].quantiles.values == [95.0, 98.0]
    assert candidate.acquisition.per_objective == {"TAR1": 0.8}


@responses.activate
def test_candidate_get_all_stops_at_max_items(candidates):
    """Test that max_items caps the iterator."""
    responses.get(
        CANDIDATES, json={"items": [CANDIDATE, {**CANDIDATE, "id": "DCN2"}], "lastKey": "k"}
    )

    assert len(list(candidates.get_all(candidate_set_id="DCS2201", max_items=1))) == 1
    assert len(responses.calls) == 1


@responses.activate
def test_candidate_get_by_id_has_no_rank_and_tolerates_a_sampling_candidate(candidates):
    """Test that a single read without rank, predictions or acquisition parses."""
    sampling = {
        k: v for k, v in CANDIDATE.items() if k not in {"rank", "predictions", "acquisition"}
    }
    responses.get(f"{CANDIDATES}/DCN{UUID}", json={**sampling, "id": f"DCN{UUID}"})

    candidate = candidates.get_by_id(id=f"dcn{UUID}")

    assert responses.calls[0].request.url == f"{CANDIDATES}/DCN{UUID}"
    assert candidate.rank is None
    assert candidate.predictions is None
    assert candidate.acquisition is None
