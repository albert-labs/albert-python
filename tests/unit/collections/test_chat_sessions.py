"""Unit tests for the query parameters ``ChatSessionCollection.get_all`` sends.

Uses ``respx`` to intercept the underlying ``httpx.AsyncClient`` so the real
``AsyncAlbertSession`` and ``AsyncAlbertPaginator`` code runs unmodified.
"""

import httpx
import respx

from albert.collections.chat_sessions import ChatSessionCollection
from albert.core.async_session import AsyncAlbertSession
from albert.resources.chats import ChatSessionKind
from tests.unit.conftest import UNIT_BASE_URL

_SESSIONS_URL = f"{UNIT_BASE_URL}/api/v3/chats/sessions"


def _collection() -> ChatSessionCollection:
    return ChatSessionCollection(
        session=AsyncAlbertSession(base_url=UNIT_BASE_URL, token="unit-token")
    )


@respx.mock
async def test_get_all_sends_kind_and_automation_id_when_provided():
    """Test get_all sends kind and automationId query params when they are given."""
    route = respx.get(_SESSIONS_URL).mock(return_value=httpx.Response(200, json={"Items": []}))

    _ = [
        s
        async for s in _collection().get_all(kind=ChatSessionKind.AUTOMATION, automation_id="AUT1")
    ]

    assert route.call_count == 1
    assert dict(route.calls[0].request.url.params) == {
        "kind": "automation",
        "automationId": "AUT1",
    }


@respx.mock
async def test_get_all_omits_kind_and_automation_id_when_not_provided():
    """Test get_all sends no kind or automationId query params when they are not given."""
    route = respx.get(_SESSIONS_URL).mock(return_value=httpx.Response(200, json={"Items": []}))

    _ = [s async for s in _collection().get_all()]

    assert route.call_count == 1
    assert dict(route.calls[0].request.url.params) == {}
