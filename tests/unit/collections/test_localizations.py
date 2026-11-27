"""Unit tests for LocalizationCollection guards."""

import responses

from albert.collections.localizations import LocalizationCollection


@responses.activate
def test_update_sends_nothing_for_empty_patches(offline_session) -> None:
    """Test that an empty patch list sends no requests at all."""
    LocalizationCollection(session=offline_session).update(id="DAT1", patches=[])

    assert len(responses.calls) == 0
