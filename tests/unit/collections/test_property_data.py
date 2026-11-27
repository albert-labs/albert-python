"""Unit tests for PropertyDataCollection search parameters."""

from urllib.parse import parse_qs, urlparse

import pytest
import responses

from albert.collections.property_data import PropertyDataCollection
from tests.unit.conftest import UNIT_BASE_URL

_SEARCH_URL = f"{UNIT_BASE_URL}/api/v3/propertydata/search"


def _query(call: responses.Call) -> dict[str, list[str]]:
    return parse_qs(urlparse(call.request.url).query)


@responses.activate
def test_search_sends_no_void_filter_by_default(offline_session) -> None:
    """Test that a default search omits ``void``, which some platforms reject with a 400."""
    responses.get(_SEARCH_URL, json={"Items": []})

    list(PropertyDataCollection(session=offline_session).search(project_ids="PRO1"))

    assert "void" not in _query(responses.calls[0])


@pytest.mark.parametrize(("void", "sent"), [(False, "false"), (True, "true")])
@responses.activate
def test_search_sends_void_when_set(offline_session, void: bool, sent: str) -> None:
    """Test that an explicit ``void`` is passed through to the platform."""
    responses.get(_SEARCH_URL, json={"Items": []})

    list(PropertyDataCollection(session=offline_session).search(project_ids="PRO1", void=void))

    assert _query(responses.calls[0])["void"] == [sent]
