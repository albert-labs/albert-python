"""Unit tests for the design-spaces collection: request shapes and cursor pagination."""

import json

import responses

from albert.collections.design_spaces import DesignSpaceCollection, _iter_last_key_pages
from albert.resources.design_spaces import (
    DesignSpace,
    DesignSpaceState,
    IngredientEntry,
    SetCountBoundsOperation,
    SetIngredientOperation,
    SetParameterOperation,
)
from tests.unit.conftest import UNIT_BASE_URL

BASE = "/api/v4.0/design/design-spaces"

SPACE = {
    "id": "DSP123",
    "albertId": "DSP123",
    "schemaVersion": 1,
    "name": "Low-VOC clearcoat envelope",
    "description": "Regulatory envelope.",
    "parentId": "PRO456",
    "state": "draft",
    "status": "active",
    "version": 3,
    "created": {"at": "2026-10-01T09:00:00Z", "by": "USR12", "byName": "Jane Doe"},
}

# --- _iter_last_key_pages ---


def _pager(pages: list[dict]):
    calls = []
    by_cursor = {cursor: page for cursor, page in pages}

    def fetch(cursor):
        calls.append(cursor)
        return by_cursor[cursor]

    return fetch, calls


def test_iter_last_key_pages_yields_across_pages():
    """Test that pages are followed until a page returns no cursor."""
    fetch, calls = _pager(
        [
            (None, {"items": [{"id": 1}, {"id": 2}], "lastKey": "k1"}),
            ("k1", {"items": [{"id": 3}], "lastKey": None}),
        ]
    )

    assert [item["id"] for item in _iter_last_key_pages(fetch)] == [1, 2, 3]
    assert calls == [None, "k1"]


def test_iter_last_key_pages_stops_mid_page_at_max_items():
    """Test that max_items stops iteration without fetching another page."""
    fetch, calls = _pager(
        [
            (None, {"items": [{"id": 1}, {"id": 2}], "lastKey": "k1"}),
            ("k1", {"items": [{"id": 3}], "lastKey": None}),
        ]
    )

    assert [item["id"] for item in _iter_last_key_pages(fetch, max_items=1)] == [1]
    assert calls == [None]


def test_iter_last_key_pages_drops_a_page_with_a_repeated_cursor():
    """Test that a page whose lastKey was already seen is dropped, ending iteration."""
    fetch, calls = _pager(
        [
            (None, {"items": [{"id": 1}], "lastKey": "k1"}),
            ("k1", {"items": [{"id": 2}], "lastKey": "k1"}),
        ]
    )

    assert [item["id"] for item in _iter_last_key_pages(fetch)] == [1]
    assert calls == [None, "k1"]


def test_iter_last_key_pages_continues_past_an_empty_page_with_a_cursor():
    """Test that an empty page carrying a cursor does not end iteration."""
    fetch, calls = _pager(
        [
            (None, {"items": [], "lastKey": "k1"}),
            ("k1", {"items": [{"id": 1}], "lastKey": None}),
        ]
    )

    assert [item["id"] for item in _iter_last_key_pages(fetch)] == [1]
    assert calls == [None, "k1"]


# --- create ---


@responses.activate
def test_create_posts_minimal_body(offline_session):
    """Test that create sends only the fields the caller gave."""
    responses.post(f"{UNIT_BASE_URL}{BASE}", json=SPACE, status=201)

    space = DesignSpaceCollection(session=offline_session).create(
        name="Low-VOC clearcoat envelope", parent_id="PRO456"
    )

    assert json.loads(responses.calls[0].request.body) == {
        "name": "Low-VOC clearcoat envelope",
        "parentId": "PRO456",
    }
    assert isinstance(space, DesignSpace)
    assert space.id == "DSP123"


@responses.activate
def test_create_posts_smart_dataset_id(offline_session):
    """Test that create carries the smart dataset the draft is seeded from."""
    responses.post(f"{UNIT_BASE_URL}{BASE}", json=SPACE, status=201)

    DesignSpaceCollection(session=offline_session).create(
        name="Derived", parent_id="PRO456", description="d", smart_dataset_id="SDT789"
    )

    assert json.loads(responses.calls[0].request.body) == {
        "name": "Derived",
        "parentId": "PRO456",
        "description": "d",
        "smartDatasetId": "SDT789",
    }


# --- get_by_id ---


@responses.activate
def test_get_by_id_gets_the_space_route(offline_session):
    """Test that get_by_id reads the single-space route."""
    responses.get(f"{UNIT_BASE_URL}{BASE}/DSP123", json=SPACE)

    space = DesignSpaceCollection(session=offline_session).get_by_id(id="DSP123")

    assert len(responses.calls) == 1
    assert space.id == "DSP123"
    assert space.state == DesignSpaceState.DRAFT
    assert space.parent_id == "PRO456"


# --- get_all ---


@responses.activate
def test_get_all_sends_parent_id_and_state(offline_session):
    """Test that get_all scopes the listing by project and lifecycle state."""
    responses.get(f"{UNIT_BASE_URL}{BASE}", json={"items": [SPACE], "count": 1, "limit": 20})

    spaces = list(
        DesignSpaceCollection(session=offline_session).get_all(
            parent_id="PRO456", state=DesignSpaceState.DRAFT
        )
    )

    assert len(spaces) == 1
    assert responses.calls[0].request.params == {"parentId": "PRO456", "state": "draft"}


@responses.activate
def test_get_all_follows_the_last_key_cursor(offline_session):
    """Test that get_all continues with the returned cursor until it runs out."""
    responses.get(
        f"{UNIT_BASE_URL}{BASE}",
        json={"items": [{**SPACE, "id": "DSP1", "albertId": "DSP1"}], "lastKey": "abc"},
    )
    responses.get(
        f"{UNIT_BASE_URL}{BASE}",
        json={"items": [{**SPACE, "id": "DSP2", "albertId": "DSP2"}], "lastKey": None},
    )

    spaces = list(DesignSpaceCollection(session=offline_session).get_all(parent_id="PRO456"))

    assert [s.id for s in spaces] == ["DSP1", "DSP2"]
    assert responses.calls[0].request.params == {"parentId": "PRO456"}
    assert responses.calls[1].request.params == {"parentId": "PRO456", "lastKey": "abc"}


# --- update ---


@responses.activate
def test_update_sends_one_op_per_changed_field(offline_session):
    """Test that update sends the stored value it expects to replace for each change."""
    responses.get(f"{UNIT_BASE_URL}{BASE}/DSP123", json=SPACE)
    responses.patch(f"{UNIT_BASE_URL}{BASE}/DSP123", json=SPACE)

    collection = DesignSpaceCollection(session=offline_session)
    updated = DesignSpace(id="DSP123", name="Renamed", description=None)
    collection.update(design_space=updated)

    body = json.loads(responses.calls[1].request.body)
    assert sorted(body["data"], key=lambda op: op["attribute"]) == [
        {"operation": "delete", "attribute": "description", "oldValue": "Regulatory envelope."},
        {
            "operation": "update",
            "attribute": "name",
            "oldValue": "Low-VOC clearcoat envelope",
            "newValue": "Renamed",
        },
    ]


@responses.activate
def test_update_skips_unset_fields(offline_session):
    """Test that fields the caller never set emit no operations and no write."""
    responses.get(f"{UNIT_BASE_URL}{BASE}/DSP123", json=SPACE)

    collection = DesignSpaceCollection(session=offline_session)
    result = collection.update(design_space=DesignSpace(id="DSP123"))

    assert len(responses.calls) == 1
    assert result.id == "DSP123"


@responses.activate
def test_update_skips_unchanged_fields(offline_session):
    """Test that fields set to their stored values emit no operations and no write."""
    responses.get(f"{UNIT_BASE_URL}{BASE}/DSP123", json=SPACE)

    collection = DesignSpaceCollection(session=offline_session)
    unchanged = DesignSpace(
        id="DSP123",
        name="Low-VOC clearcoat envelope",
        description="Regulatory envelope.",
    )
    result = collection.update(design_space=unchanged)

    assert len(responses.calls) == 1
    assert result.id == "DSP123"


# --- delete ---


@responses.activate
def test_delete_calls_the_space_route(offline_session):
    """Test that delete targets the single-space route."""
    responses.delete(f"{UNIT_BASE_URL}{BASE}/DSP123", status=204)

    assert DesignSpaceCollection(session=offline_session).delete(id="DSP123") is None
    assert len(responses.calls) == 1


# --- apply ---


@responses.activate
def test_apply_posts_operations_with_flags(offline_session):
    """Test that apply sends the operations and folds in validate, preview, and dry run."""
    result_body = {"designSpace": SPACE, "warnings": []}
    responses.post(f"{UNIT_BASE_URL}{BASE}/DSP123/operations", json=result_body)

    DesignSpaceCollection(session=offline_session).apply(
        id="DSP123",
        operations=[
            SetParameterOperation(
                parameter_id="PRM07",
                data_template_id="DAT01",
                parameter_group_id=None,
                unit_id="UNI12",
                value={
                    "data_type": "numeric",
                    "constraint": {"type": "continuous", "min": 60, "max": 120},
                },
            ),
            SetIngredientOperation(
                key="INV004", value=IngredientEntry(action="mayInclude", min=0.0, max=0.03)
            ),
        ],
        validate=True,
        preview=5,
        dry_run=True,
    )

    assert json.loads(responses.calls[0].request.body) == {
        "operations": [
            {
                "op": "setParameter",
                "parameterId": "PRM07",
                "dataTemplateId": "DAT01",
                "parameterGroupId": None,
                "unitId": "UNI12",
                "value": {
                    "dataType": "numeric",
                    "constraint": {"type": "continuous", "min": 60.0, "max": 120.0},
                },
            },
            {
                "op": "setIngredient",
                "key": "INV004",
                "value": {"action": "mayInclude", "min": 0.0, "max": 0.03},
            },
        ],
        "validate": True,
        "preview": {"numSamples": 5},
        "dryRun": True,
    }


@responses.activate
def test_apply_keeps_an_explicit_null_count_bound(offline_session):
    """Test that a count bound set to None clears the bound rather than leaving it."""
    responses.post(
        f"{UNIT_BASE_URL}{BASE}/DSP123/operations", json={"designSpace": SPACE, "warnings": []}
    )

    DesignSpaceCollection(session=offline_session).apply(
        id="DSP123", operations=[SetCountBoundsOperation(min_count=None, max_count=4)]
    )

    assert json.loads(responses.calls[0].request.body)["operations"] == [
        {"op": "setCountBounds", "minCount": None, "maxCount": 4}
    ]


# --- check_feasibility ---


@responses.activate
def test_check_feasibility_sends_empty_body_without_context(offline_session):
    """Test that a bare feasibility check carries no context."""
    responses.post(
        f"{UNIT_BASE_URL}{BASE}/DSP123/validation", json={"valid": True, "violations": []}
    )

    result = DesignSpaceCollection(session=offline_session).check_feasibility(id="DSP123")

    assert json.loads(responses.calls[0].request.body) == {}
    assert result.valid is True


@responses.activate
def test_check_feasibility_sends_dataset_and_model_config(offline_session):
    """Test that the optional bind-check context is carried by ID."""
    responses.post(
        f"{UNIT_BASE_URL}{BASE}/DSP123/validation", json={"valid": False, "violations": []}
    )

    DesignSpaceCollection(session=offline_session).check_feasibility(
        id="DSP123", smart_dataset_id="SDT789", design_model_config_id="DMC1"
    )

    assert json.loads(responses.calls[0].request.body) == {
        "smartDatasetId": "SDT789",
        "designModelConfigId": "DMC1",
    }


# --- get_sample_preview ---


@responses.activate
def test_get_sample_preview_defaults_to_ten_samples(offline_session):
    """Test that the preview size defaults to ten."""
    responses.post(f"{UNIT_BASE_URL}{BASE}/DSP123/samples", json={"rows": []})

    DesignSpaceCollection(session=offline_session).get_sample_preview(id="DSP123")

    assert json.loads(responses.calls[0].request.body) == {"numSamples": 10}


@responses.activate
def test_get_sample_preview_sends_the_asked_size(offline_session):
    """Test that the preview size is carried."""
    responses.post(f"{UNIT_BASE_URL}{BASE}/DSP123/samples", json={"rows": []})

    DesignSpaceCollection(session=offline_session).get_sample_preview(id="DSP123", num_samples=5)

    assert json.loads(responses.calls[0].request.body) == {"numSamples": 5}


# --- publish ---


@responses.activate
def test_publish_posts_without_a_body(offline_session):
    """Test that publish takes no input beyond the space ID."""
    responses.post(f"{UNIT_BASE_URL}{BASE}/DSP123/publication", json=SPACE)

    DesignSpaceCollection(session=offline_session).publish(id="DSP123")

    assert len(responses.calls) == 1
    assert not responses.calls[0].request.body


# --- fork ---


@responses.activate
def test_fork_posts_an_empty_body_without_a_target_project(offline_session):
    """Test that a same-project fork carries no fields."""
    responses.post(f"{UNIT_BASE_URL}{BASE}/DSP123/forks", json=SPACE, status=201)

    DesignSpaceCollection(session=offline_session).fork(id="DSP123")

    assert json.loads(responses.calls[0].request.body) == {}


@responses.activate
def test_fork_sends_the_target_project(offline_session):
    """Test that a cross-project fork carries the target project."""
    responses.post(f"{UNIT_BASE_URL}{BASE}/DSP123/forks", json=SPACE, status=201)

    DesignSpaceCollection(session=offline_session).fork(id="DSP123", parent_id="PRO789")

    assert json.loads(responses.calls[0].request.body) == {"parentId": "PRO789"}


# --- get_references ---


@responses.activate
def test_get_references_sends_the_component_path(offline_session):
    """Test that the component path is passed as the reference query."""
    responses.get(f"{UNIT_BASE_URL}{BASE}/DSP123/references", json={"references": []})

    DesignSpaceCollection(session=offline_session).get_references(
        id="DSP123", component="ingredients/INV004"
    )

    assert responses.calls[0].request.params == {"component": "ingredients/INV004"}
