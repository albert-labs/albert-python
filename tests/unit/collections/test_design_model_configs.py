"""Unit tests for the design-model-configs collection: the requests it sends and how it
reads responses, against a faked HTTP layer."""

import json
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from albert.collections.design_model_configs import DesignModelConfigCollection
from albert.exceptions import AlbertClientError
from albert.resources.design_model_configs import (
    DesignModelConfig,
    DesignModelConfigState,
    OutputEntry,
    SetOutputOperation,
)
from albert.resources.design_spaces import RemoveComponentOperation
from tests.unit.conftest import UNIT_BASE_URL

BASE = f"{UNIT_BASE_URL}/api/v4/design/model-configs"
UUID = "0b7e2c1a-4f3d-4c8e-9a51-2d6f8b9e1c47"
CONFIG = {"id": "DMC123", "name": "Clearcoat surrogate", "state": "draft", "parentId": "PRO456"}


@pytest.fixture
def configs(offline_session) -> DesignModelConfigCollection:
    return DesignModelConfigCollection(session=offline_session)


def _body(call=None) -> dict:
    return json.loads((call or responses.calls[-1]).request.body)


def _query(call=None) -> dict:
    return parse_qs(urlparse((call or responses.calls[-1]).request.url).query)


@responses.activate
def test_create_posts_the_wire_body_and_parses_warnings(configs):
    """Test that create sends camelCase fields without Nones and parses the created draft."""
    responses.post(
        BASE, json={**CONFIG, "warnings": [{"code": "inert_mask_entry", "message": "m"}]}
    )

    created = configs.create(
        name="Clearcoat surrogate", parent_id="pro456", smart_dataset_id="SDT1"
    )

    assert _body() == {
        "name": "Clearcoat surrogate",
        "parentId": "PRO456",
        "smartDatasetId": "SDT1",
    }
    assert created.id == "DMC123"
    assert created.state == DesignModelConfigState.DRAFT
    assert created.warnings[0].code == "inert_mask_entry"


@responses.activate
def test_get_by_id_normalises_the_id_keeping_the_uuid_case(configs):
    """Test that only the id prefix is uppercased in the request path."""
    responses.get(f"{BASE}/DMC{UUID}", json={**CONFIG, "id": f"DMC{UUID}"})

    config = configs.get_by_id(id=f"dmc{UUID}")

    assert responses.calls[0].request.url == f"{BASE}/DMC{UUID}"
    assert config.id == f"DMC{UUID}"


@responses.activate
def test_get_all_sends_filters_and_follows_the_last_key_cursor(configs):
    """Test that listing sends parentId and state and pages with lastKey."""
    responses.get(BASE, json={"items": [CONFIG], "lastKey": "k1"})
    responses.get(BASE, json={"items": [{**CONFIG, "id": "DMC2"}]})

    listed = list(configs.get_all(parent_id="PRO456", state=DesignModelConfigState.PUBLISHED))

    assert [c.id for c in listed] == ["DMC123", "DMC2"]
    assert _query(responses.calls[0]) == {"parentId": ["PRO456"], "state": ["published"]}
    assert _query(responses.calls[1])["lastKey"] == ["k1"]


@responses.activate
def test_get_all_stops_at_max_items(configs):
    """Test that max_items caps the iterator."""
    responses.get(BASE, json={"items": [CONFIG, {**CONFIG, "id": "DMC2"}], "lastKey": "k1"})

    assert len(list(configs.get_all(parent_id="PRO456", max_items=1))) == 1
    assert len(responses.calls) == 1


@responses.activate
def test_update_patches_only_name_and_description(configs):
    """Test that update reads the config, then patches just the changed field."""
    responses.get(f"{BASE}/DMC123", json={**CONFIG, "description": "old"})
    responses.patch(f"{BASE}/DMC123", json={**CONFIG, "description": "new"})

    updated = configs.update(design_model_config=DesignModelConfig(id="DMC123", description="new"))

    assert responses.calls[1].request.method == "PATCH"
    assert _body()["data"] == [
        {"operation": "update", "attribute": "description", "oldValue": "old", "newValue": "new"}
    ]
    assert updated.description == "new"


@responses.activate
def test_update_sends_nothing_when_nothing_changed(configs):
    """Test that an update with no changes does not patch."""
    responses.get(f"{BASE}/DMC123", json={**CONFIG, "description": "same"})

    configs.update(design_model_config=DesignModelConfig(id="DMC123", description="same"))

    assert [c.request.method for c in responses.calls] == ["GET"]


@responses.activate
def test_apply_sends_operations_and_folded_options(configs):
    """Test that apply sends ops, flags, the preview options and the dataset, and parses all parts."""
    responses.post(
        f"{BASE}/DMC123/operations",
        json={
            "modelConfig": CONFIG,
            "validation": {"valid": True, "violations": []},
            "resolvedFeatures": {"features": [], "outputs": {}},
            "preview": {
                "numRows": 3,
                "automaticFeatures": {"count": 0},
            },
        },
    )

    result = configs.apply(
        id="DMC123",
        operations=[
            SetOutputOperation(key="TAR1", value=OutputEntry(data_type="numeric")),
            RemoveComponentOperation(path="outputs/TAR2"),
        ],
        validate=True,
        resolve=True,
        preview_rows=3,
        dry_run=True,
        smart_dataset_id="SDT1",
    )

    assert _body() == {
        "operations": [
            {"op": "setOutput", "key": "TAR1", "value": {"dataType": "numeric"}},
            {"op": "removeComponent", "path": "outputs/TAR2"},
        ],
        "validate": True,
        "resolve": True,
        "preview": {"numRows": 3},
        "dryRun": True,
        "smartDatasetId": "SDT1",
    }
    assert result.design_model_config.id == "DMC123"
    assert result.validation.valid is True
    assert result.resolved_features.features == []
    assert result.preview.num_rows == 3


@responses.activate
def test_apply_defaults_send_no_preview_or_dataset(configs):
    """Test that an apply with defaults omits preview and smartDatasetId."""
    responses.post(f"{BASE}/DMC123/operations", json={"modelConfig": CONFIG})

    configs.apply(id="DMC123", operations=[RemoveComponentOperation(path="outputs/TAR2")])

    body = _body()
    assert "preview" not in body
    assert "smartDatasetId" not in body
    assert (body["validate"], body["resolve"], body["dryRun"]) == (False, False, False)


@responses.activate
def test_apply_surfaces_a_422_as_a_client_error(configs):
    """Test that a rejected apply raises the SDK's client error."""
    responses.post(
        f"{BASE}/DMC123/operations",
        status=422,
        json={
            "statusCode": 422,
            "message": [{"code": "invalid_settings", "message": "bad transform"}],
        },
    )

    with pytest.raises(AlbertClientError):
        configs.apply(id="DMC123", operations=[RemoveComponentOperation(path="outputs/TAR2")])


@responses.activate
def test_apply_rejects_an_empty_operation_list_before_sending(configs):
    """Test that an empty operation list fails locally."""
    with pytest.raises(ValueError):
        configs.apply(id="DMC123", operations=[])

    assert len(responses.calls) == 0


@responses.activate
def test_check_compatibility_posts_the_dataset_and_returns_an_invalid_result(configs):
    """Test that valid=False is returned as a result, not raised."""
    responses.post(
        f"{BASE}/DMC123/validation",
        json={"valid": False, "violations": [{"code": "target_not_in_dataset", "message": "m"}]},
    )

    result = configs.check_compatibility(id="DMC123", smart_dataset_id="sdt1")

    assert _body() == {"smartDatasetId": "SDT1"}
    assert result.valid is False
    assert result.violations[0].code == "target_not_in_dataset"


@responses.activate
def test_get_resolved_features_sends_the_dataset_as_a_query_param(configs):
    """Test the features route, its query param and the typed response."""
    responses.get(
        f"{BASE}/DMC123/features",
        json={
            "features": [
                {
                    "key": "label/TAG1",
                    "family": "label_fraction",
                    "descriptor": {"type": "labelFraction", "label": "TAG1"},
                }
            ],
            "outputs": {"TAR1": ["label/TAG1"]},
        },
    )

    resolved = configs.get_resolved_features(id="DMC123", smart_dataset_id="SDT1")

    assert _query() == {"smartDatasetId": ["SDT1"]}
    assert resolved.features[0].key == "label/TAG1"
    assert resolved.outputs == {"TAR1": ["label/TAG1"]}


@responses.activate
def test_get_feature_values_sends_the_dataset_as_a_query_param(configs):
    """Test the feature-values route, its query param and the typed response."""
    responses.get(
        f"{BASE}/DMC123/feature-values",
        json={
            "numRows": 1,
            "rows": [{"experimentId": "E1", "values": {"label/TAG1": 0.2}}],
            "automaticFeatures": {"count": 0},
        },
    )

    preview = configs.get_feature_values(id="DMC123", smart_dataset_id="SDT1")

    assert _query() == {"smartDatasetId": ["SDT1"]}
    assert preview.rows[0].values == {"label/TAG1": 0.2}


@responses.activate
def test_publish_posts_to_publication(configs):
    """Test that publish posts to the publication route and parses the config."""
    responses.post(f"{BASE}/DMC123/publication", json={**CONFIG, "state": "published"})

    assert configs.publish(id="DMC123").state == DesignModelConfigState.PUBLISHED
    assert responses.calls[0].request.body is None


@responses.activate
def test_fork_sends_the_target_project_only_when_given(configs):
    """Test that fork sends an empty body by default and parentId when given."""
    responses.post(f"{BASE}/DMC123/forks", json={**CONFIG, "forkedFromId": "DMC123"})

    forked = configs.fork(id="DMC123")
    assert _body() == {}
    assert forked.forked_from_id == "DMC123"

    configs.fork(id="DMC123", parent_id="pro9")
    assert _body() == {"parentId": "PRO9"}


@responses.activate
def test_get_references_sends_the_component_as_a_query_param(configs):
    """Test the references route, its query param and the open response."""
    responses.get(f"{BASE}/DMC123/references", json={"references": ["x"]})

    refs = configs.get_references(id="DMC123", component="outputs/TAR046")

    assert _query() == {"component": ["outputs/TAR046"]}
    assert refs.model_dump() == {"references": ["x"]}


@responses.activate
def test_delete_sends_a_delete(configs):
    """Test that delete issues DELETE on the config route."""
    responses.delete(f"{BASE}/DMC123", status=204)

    assert configs.delete(id="DMC123") is None
    assert responses.calls[0].request.method == "DELETE"
