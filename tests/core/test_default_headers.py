"""Caller-supplied default headers on the sync and async sessions.

The motivating case is audit metadata: Ask Albert stamps turn context onto
every platform call so an activity record can be traced back to the
conversation that produced it. Before this seam existed, the only way to do
that was to mutate the private ``AsyncAlbertSession._client``.
"""

import httpx
import pytest

from albert import Albert, AsyncAlbert
from albert.core.async_session import AsyncAlbertSession
from albert.core.session import AlbertSession

_BASE_URL = "https://test.albertinvent.com"
_METADATA = {"x-s2s-metadata": '{"chatId":"SES4515"}'}


def test_sync_session_applies_default_headers():
    session = AlbertSession(base_url=_BASE_URL, token="tok", headers=_METADATA)

    assert session.headers["x-s2s-metadata"] == '{"chatId":"SES4515"}'


def test_sync_session_keeps_its_own_defaults():
    """Extra headers must add to the SDK defaults, not replace them."""
    session = AlbertSession(base_url=_BASE_URL, token="tok", headers=_METADATA)

    assert session.headers["Content-Type"] == "application/json"
    assert session.headers["User-Agent"].startswith("albert-SDK")


def test_sync_session_without_headers_is_unchanged():
    assert "x-s2s-metadata" not in AlbertSession(base_url=_BASE_URL, token="tok").headers


def test_async_session_applies_default_headers():
    session = AsyncAlbertSession(base_url=_BASE_URL, token="tok", headers=_METADATA)

    assert session._client.headers["x-s2s-metadata"] == '{"chatId":"SES4515"}'
    assert session._client.headers["Content-Type"] == "application/json"


def test_client_constructors_pass_headers_through():
    sync_client = Albert.from_token(base_url=_BASE_URL, token="tok", headers=_METADATA)
    async_client = AsyncAlbert.from_token(base_url=_BASE_URL, token="tok", headers=_METADATA)

    assert sync_client.session.headers["x-s2s-metadata"] == '{"chatId":"SES4515"}'
    assert async_client.session._client.headers["x-s2s-metadata"] == '{"chatId":"SES4515"}'


@pytest.mark.asyncio
async def test_async_default_headers_ride_every_request():
    """The point of the seam: the header is on the wire, not just the client."""
    seen: list[httpx.Headers] = []

    def _capture(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        return httpx.Response(200, json={})

    session = AsyncAlbertSession(base_url=_BASE_URL, token="tok", headers=_METADATA)
    session._client = httpx.AsyncClient(
        base_url=_BASE_URL,
        headers=session._client.headers,
        transport=httpx.MockTransport(_capture),
    )
    await session.get("/api/v3/projects")
    await session.get("/api/v3/inventories")

    assert len(seen) == 2
    assert all(h["x-s2s-metadata"] == '{"chatId":"SES4515"}' for h in seen)


@pytest.mark.asyncio
async def test_authorization_cannot_be_overridden_by_default_headers():
    """Auth is applied per request, so a caller header can never displace it."""
    seen: list[httpx.Headers] = []

    def _capture(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        return httpx.Response(200, json={})

    session = AsyncAlbertSession(
        base_url=_BASE_URL, token="real-token", headers={"Authorization": "Bearer spoofed"}
    )
    session._client = httpx.AsyncClient(
        base_url=_BASE_URL,
        headers=session._client.headers,
        transport=httpx.MockTransport(_capture),
    )
    await session.get("/api/v3/projects")

    assert seen[0]["Authorization"] == "Bearer real-token"
