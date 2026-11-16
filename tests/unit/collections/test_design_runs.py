"""Unit tests for the v3 and v4 design-run collections.

The route tests guard the additive v4 split: the v3 collection must keep its routes while the
v4 collection targets the ``design`` service, with only the validate suffix differing. The
rest cover the v4 collection's private helpers; public methods are covered by the integration
suite (tests/unit/TESTING.md).
"""

import json

import pytest
import responses

from albert.collections.design_runs import DesignRunCollection, DesignRunV4Collection
from albert.resources.design import DesignMethod
from albert.resources.design_runs import DesignRun, DesignRunState
from tests.unit.conftest import UNIT_BASE_URL

SDT = "SDT1"
INSIGHT = {"name": "run", "category": "Generate", "albertId": "INS1"}
VALIDATION = {"valid": True, "violations": []}


def _owner(cls) -> dict[str, str]:
    """The project a v4 run must name; the v3 collection takes none."""
    return {"parent_id": "PRO456"} if cls is DesignRunV4Collection else {}


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

    getattr(cls(session=offline_session), method)(smart_dataset_id=SDT, **_owner(cls))

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

    result = getattr(cls(session=offline_session), method)(smart_dataset_id=SDT, **_owner(cls))

    assert len(responses.calls) == 1
    assert result.valid is True


@pytest.fixture
def runs(offline_session) -> DesignRunV4Collection:
    return DesignRunV4Collection(session=offline_session)


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({}, {"parentId": "PRO456"}),
        (
            {"state": DesignRunState.COMPLETE, "method": DesignMethod.GENERATE},
            {"parentId": "PRO456", "state": "complete", "method": "generate"},
        ),
    ],
)
def test_list_params_send_state_and_method_only_when_given(filters, expected):
    """Test that the list query carries the project and the optional filters."""
    params = {"state": None, "method": None, **filters}

    assert DesignRunV4Collection._list_params(parent_id="PRO456", **params) == expected


def test_patch_payload_carries_only_the_changed_description(runs):
    """Test that an edited description becomes the one update operation."""
    existing = DesignRun(id="DSR123", name="Clearcoat sweep", description="old")
    updated = DesignRun(id="DSR123", name="Clearcoat sweep", description="new")

    payload = runs._generate_patch_payload(existing=existing, updated=updated)

    assert payload.model_dump(mode="json", by_alias=True)["data"] == [
        {"operation": "update", "attribute": "description", "oldValue": "old", "newValue": "new"}
    ]


def test_patch_payload_ignores_fields_that_cannot_be_updated(runs):
    """Test that registry fields such as state are never patched by a rename."""
    existing = DesignRun(id="DSR123", name="Clearcoat sweep", state="running")
    updated = DesignRun(id="DSR123", name="Clearcoat sweep", state="complete")

    assert runs._generate_patch_payload(existing=existing, updated=updated).data == []
