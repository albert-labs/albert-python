"""Unit tests for the query parameters ``ChatMessageCollection.get_all`` sends."""

import httpx
import respx

from albert.collections.chat_messages import ChatMessageCollection
from albert.core.async_session import AsyncAlbertSession
from tests.unit.conftest import UNIT_BASE_URL

_MESSAGES_URL = f"{UNIT_BASE_URL}/api/v3/chats/sessions/SES_TEST/messages"
_MESSAGE = {
    "sourceRequestId": "REQ_TEST",
    "componentType": "text",
    "userType": "user",
    "role": "user",
    "Content": "Test message",
}


def _collection() -> ChatMessageCollection:
    return ChatMessageCollection(
        session=AsyncAlbertSession(base_url=UNIT_BASE_URL, token="unit-token")
    )


@respx.mock
async def test_get_all_preserves_source_request_id_across_pages():
    """Test get_all sends sourceRequestId on the first and following pages."""
    route = respx.get(_MESSAGES_URL).mock(
        side_effect=[
            httpx.Response(200, json={"Items": [_MESSAGE], "lastKey": "next-page"}),
            httpx.Response(200, json={"Items": []}),
        ]
    )

    _ = [
        message
        async for message in _collection().get_all(
            session_id="SES_TEST", source_request_id="REQ_TEST"
        )
    ]

    assert route.call_count == 2
    assert dict(route.calls[0].request.url.params) == {"sourceRequestId": "REQ_TEST"}
    assert dict(route.calls[1].request.url.params) == {
        "sourceRequestId": "REQ_TEST",
        "startKey": "next-page",
    }


@respx.mock
async def test_get_all_omits_source_request_id_when_not_provided():
    """Test get_all sends no sourceRequestId query param when it is not given."""
    route = respx.get(_MESSAGES_URL).mock(return_value=httpx.Response(200, json={"Items": []}))

    _ = [message async for message in _collection().get_all(session_id="SES_TEST")]

    assert route.call_count == 1
    assert dict(route.calls[0].request.url.params) == {}
