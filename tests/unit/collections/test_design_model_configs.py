"""Unit tests for the design-model-configs collection's private helpers.

Public methods are covered by the integration suite (tests/unit/TESTING.md).
"""

import pytest

from albert.collections.design_model_configs import DesignModelConfigCollection
from albert.resources.design_model_configs import (
    DesignModelConfig,
    DesignModelConfigState,
    OutputEntry,
    SetOutputOperation,
)
from albert.resources.design_spaces import RemoveComponentOperation, UpdateComponentOperation

REMOVE = RemoveComponentOperation(path="outputs/TAR2")


@pytest.fixture
def configs(offline_session) -> DesignModelConfigCollection:
    return DesignModelConfigCollection(session=offline_session)


def _operations_body(**overrides) -> dict:
    options = {
        "operations": [REMOVE],
        "validate": False,
        "resolve": False,
        "preview_rows": None,
        "preview_max_columns": None,
        "dry_run": False,
        "smart_dataset_id": None,
    }
    return DesignModelConfigCollection._operations_body(**{**options, **overrides})


def test_patch_payload_carries_only_the_changed_description(configs):
    """Test that an edited description becomes the one update operation."""
    existing = DesignModelConfig(id="DMC123", name="Clearcoat surrogate", description="old")
    updated = DesignModelConfig(id="DMC123", name="Clearcoat surrogate", description="new")

    payload = configs._generate_patch_payload(existing=existing, updated=updated)

    assert payload.model_dump(mode="json", by_alias=True)["data"] == [
        {"operation": "update", "attribute": "description", "oldValue": "old", "newValue": "new"}
    ]


def test_patch_payload_ignores_fields_that_cannot_be_updated(configs):
    """Test that a changed state is not patched, and an unchanged config yields no operations."""
    existing = DesignModelConfig(id="DMC123", description="same", state="draft")
    updated = DesignModelConfig(id="DMC123", description="same", state="published")

    assert configs._generate_patch_payload(existing=existing, updated=updated).data == []


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (None, {"parentId": "PRO456"}),
        (DesignModelConfigState.PUBLISHED, {"parentId": "PRO456", "state": "published"}),
    ],
)
def test_list_params_send_the_state_only_when_given(state, expected):
    """Test that the list query carries the project and an optional state."""
    assert DesignModelConfigCollection._list_params(parent_id="PRO456", state=state) == expected


def test_operations_body_folds_every_option():
    """Test that the body carries ops, flags, the preview and the dataset in wire form."""
    body = _operations_body(
        operations=[
            SetOutputOperation(key="TAR1", value=OutputEntry(data_type="numeric")),
            REMOVE,
        ],
        validate=True,
        resolve=True,
        preview_rows=3,
        dry_run=True,
        smart_dataset_id="SDT1",
    )

    assert body == {
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


def test_operations_body_keeps_an_explicit_null_value_that_clears_a_field():
    """Test that updateComponent with value=None is sent with its null, so it clears the field."""
    clear = UpdateComponentOperation(path="outputs/TAR1", field="features", value=None)

    assert _operations_body(operations=[clear])["operations"] == [
        {"op": "updateComponent", "path": "outputs/TAR1", "field": "features", "value": None}
    ]


def test_operations_body_defaults_send_no_preview_or_dataset():
    """Test that defaults omit preview and smartDatasetId but keep the three flags."""
    body = _operations_body()

    assert "preview" not in body
    assert "smartDatasetId" not in body
    assert (body["validate"], body["resolve"], body["dryRun"]) == (False, False, False)


@pytest.mark.parametrize(
    ("counts", "sent"),
    [
        ({"preview_rows": "all"}, {"numRows": None}),
        ({"preview_max_columns": 5}, {"maxColumns": 5}),
        ({"preview_rows": 3, "preview_max_columns": "all"}, {"numRows": 3, "maxColumns": None}),
    ],
)
def test_operations_body_sends_the_given_preview_counts_with_all_as_null(counts, sent):
    """Test that the folded preview keeps exactly the counts given, "all" as null."""
    assert _operations_body(smart_dataset_id="SDT1", **counts)["preview"] == sent


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ({}, {"smartDatasetId": "SDT1"}),
        (
            {"num_rows": "all", "max_columns": 5},
            {"smartDatasetId": "SDT1", "numRows": "all", "maxColumns": 5},
        ),
    ],
)
def test_feature_values_params_send_only_the_given_counts(counts, expected):
    """Test that unset counts are omitted and "all" is sent verbatim."""
    params = {"num_rows": None, "max_columns": None, **counts}

    assert (
        DesignModelConfigCollection._feature_values_params(smart_dataset_id="SDT1", **params)
        == expected
    )
