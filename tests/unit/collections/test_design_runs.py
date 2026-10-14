"""Unit tests for the request routes of the v3 and v4 design-run collections.

These guard the additive v4 split: the v3 collection must keep its routes while the v4
collection targets the ``design`` service, with only the validate suffix differing.
"""

import json

import pytest
import responses

from albert.collections.design_runs import DesignRunCollection, DesignRunV4Collection
from tests.unit.conftest import UNIT_BASE_URL

SDT = "SDT1"
INSIGHT = {"name": "run", "category": "Generate", "albertId": "INS1"}
VALIDATION = {"valid": True, "violations": []}

ROUTES = [
    (DesignRunCollection, "/api/v3/designruns", "/api/v3/designruns/validate"),
    (DesignRunV4Collection, "/api/v4.0/design/runs", "/api/v4.0/design/runs/validation"),
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
