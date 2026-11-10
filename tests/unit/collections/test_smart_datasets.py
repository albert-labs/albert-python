"""Unit tests for the smart dataset update patch builder.

Allowed under the patch-builder exception in OPINIONS.md: these guard that a
changed ``build_error`` is sent under its wire name ``buildError``, that an
explicit None clears the stored reason, and that an unset or unchanged
``build_error`` sends nothing.
"""

import pytest

from albert.collections.smart_datasets import SmartDatasetCollection
from albert.resources.smart_datasets import SmartDataset, SmartDatasetBuildState


def _existing() -> SmartDataset:
    return SmartDataset(
        id="SDT1",
        build_state=SmartDatasetBuildState.FAILED,
        build_error="You don't have permission to sync. Contact your admin.",
    )


def _patches(
    offline_session, *, updated: SmartDataset, existing: SmartDataset | None
) -> list[dict]:
    payload = SmartDatasetCollection(session=offline_session)._generate_patch_payload(
        existing=existing, updated=updated
    )
    return payload.model_dump(mode="json", by_alias=True, exclude_none=False)["data"]


def test_build_error_unset_emits_no_op(offline_session):
    """Test that a build_error the caller never set produces no patch operation."""
    updated = SmartDataset(id="SDT1", build_state=SmartDatasetBuildState.FAILED)

    assert _patches(offline_session, updated=updated, existing=_existing()) == []


def test_build_error_unchanged_emits_no_op(offline_session):
    """Test that an unchanged build_error produces no patch operation."""
    updated = SmartDataset(
        id="SDT1",
        build_error="You don't have permission to sync. Contact your admin.",
    )

    assert _patches(offline_session, updated=updated, existing=_existing()) == []


def test_build_error_changed_emits_update(offline_session):
    """Test that a changed build_error is patched under its wire name buildError."""
    updated = SmartDataset(id="SDT1", build_error="Sync failed because of a server error.")

    assert _patches(offline_session, updated=updated, existing=_existing()) == [
        {
            "operation": "update",
            "attribute": "buildError",
            "oldValue": "You don't have permission to sync. Contact your admin.",
            "newValue": "Sync failed because of a server error.",
        }
    ]


def test_build_error_set_on_dataset_without_one_emits_update(offline_session):
    """Test that setting build_error where none was stored sends only the new value."""
    existing = SmartDataset(id="SDT1", build_state=SmartDatasetBuildState.FAILED)
    updated = SmartDataset(id="SDT1", build_error="Sync failed because of a server error.")

    assert _patches(offline_session, updated=updated, existing=existing) == [
        {
            "operation": "update",
            "attribute": "buildError",
            "oldValue": None,
            "newValue": "Sync failed because of a server error.",
        }
    ]


def test_build_error_explicit_none_clears(offline_session):
    """Test that an explicit None build_error clears the stored failure reason."""
    updated = SmartDataset(id="SDT1", build_error=None)

    assert _patches(offline_session, updated=updated, existing=_existing()) == [
        {
            "operation": "update",
            "attribute": "buildError",
            "oldValue": "You don't have permission to sync. Contact your admin.",
            "newValue": None,
        }
    ]


@pytest.mark.parametrize(
    "raw",
    [
        {"id": "SDT1", "buildState": "failed", "buildError": "Target 'TAR1' not found."},
        {"id": "SDT1", "buildState": "ready"},
    ],
)
def test_build_error_wire_round_trip(raw):
    """Test buildError parses from the wire shape and serializes back under the same key."""
    dataset = SmartDataset(**raw)

    assert dataset.build_error == raw.get("buildError")
    dumped = dataset.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped.get("buildError") == raw.get("buildError")
