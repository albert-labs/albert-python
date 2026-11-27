"""Unit tests for CasCollection construction."""

import pytest

from albert import Albert
from tests.unit.conftest import UNIT_BASE_URL


def test_cas_numbers_deprecation_is_attributed_to_the_caller():
    """Test that client.cas_numbers warns from the caller's file, not the client module."""
    client = Albert(base_url=UNIT_BASE_URL, token="unit-token")

    with pytest.warns(DeprecationWarning, match="CasCollection is deprecated") as record:
        client.cas_numbers  # noqa: B018

    assert record[0].filename == __file__
