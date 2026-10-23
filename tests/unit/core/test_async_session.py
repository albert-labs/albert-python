"""Tests for ``AsyncAlbertSession``: URL joining, auth, exception mapping, lifecycle.

Uses ``respx`` to intercept the underlying ``httpx.AsyncClient`` so the real
request path (headers, error handling, raise_for_status) runs unmodified.
"""

import httpx
import pytest
import respx

from albert.core.async_session import AsyncAlbertSession
from albert.exceptions import (
    AlbertClientError,
    AlbertServerError,
    BadGateway,
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
)

_BASE_URL = "https://unit.test"


class _FakeAuthManager:
    """Minimal duck-typed auth manager exposing only what the session needs."""

    def __init__(self, token: str) -> None:
        self._token = token
        self.calls = 0

    def get_access_token(self) -> str:
        self.calls += 1
        return self._token


# --- construction --------------------------------------------------------------


def test_requires_token_or_auth_manager():
    """Test that omitting both token and auth_manager raises ValueError."""
    with pytest.raises(ValueError):
        AsyncAlbertSession(base_url=_BASE_URL)


def test_static_token_used_when_no_auth_manager():
    """Test that the access token comes from the static token by default."""
    session = AsyncAlbertSession(base_url=_BASE_URL, token="static-token")

    assert session._access_token == "static-token"


def test_auth_manager_overrides_static_token():
    """Test that an auth_manager takes priority over a provided static token."""
    manager = _FakeAuthManager("manager-token")
    session = AsyncAlbertSession(base_url=_BASE_URL, token="static-token", auth_manager=manager)

    assert session._access_token == "manager-token"
    assert manager.calls == 1


def test_no_extra_headers_leaves_only_sdk_defaults():
    """Test that omitting the headers argument leaves just the SDK default headers."""
    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")

    assert session._client.headers["Content-Type"] == "application/json"
    assert "x-custom" not in session._client.headers


# --- URL joining -----------------------------------------------------------------


@respx.mock
async def test_relative_path_is_joined_with_base_url():
    """Test that a relative path is appended to the session's base_url."""
    route = respx.get(f"{_BASE_URL}/api/v3/x/1").mock(return_value=httpx.Response(200, json={}))
    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")

    await session.get("/api/v3/x/1")

    assert route.called


@respx.mock
async def test_leading_slash_path_does_not_reset_base_url_subpath():
    """Test that httpx's join keeps a base_url subpath even with a leading-slash path.

    Unlike ``urljoin`` (used by the sync session), httpx's ``base_url`` merge treats
    the base_url as a directory prefix regardless of a leading slash on the path.
    """
    session = AsyncAlbertSession(base_url=f"{_BASE_URL}/tenant/sub/", token="t")
    route = respx.get(f"{_BASE_URL}/tenant/sub/api/v3/x").mock(
        return_value=httpx.Response(200, json={})
    )

    await session.get("/api/v3/x")

    assert route.called


@respx.mock
async def test_absolute_url_path_bypasses_base_url():
    """Test that an absolute URL passed as the path is requested as-is."""
    route = respx.get("https://other.example/api/v3/x").mock(
        return_value=httpx.Response(200, json={})
    )
    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")

    await session.get("https://other.example/api/v3/x")

    assert route.called


# --- Authorization header --------------------------------------------------------


@respx.mock
async def test_authorization_header_from_static_token():
    """Test that the Authorization header carries the static bearer token."""
    route = respx.get(f"{_BASE_URL}/api/v3/x").mock(return_value=httpx.Response(200, json={}))
    session = AsyncAlbertSession(base_url=_BASE_URL, token="abc123")

    await session.get("/api/v3/x")

    assert route.calls.last.request.headers["Authorization"] == "Bearer abc123"


@respx.mock
async def test_authorization_header_from_auth_manager():
    """Test that the Authorization header is refreshed from the auth manager each call."""
    route = respx.get(f"{_BASE_URL}/api/v3/x").mock(return_value=httpx.Response(200, json={}))
    manager = _FakeAuthManager("manager-token")
    session = AsyncAlbertSession(base_url=_BASE_URL, auth_manager=manager)

    await session.get("/api/v3/x")

    assert route.calls.last.request.headers["Authorization"] == "Bearer manager-token"


@respx.mock
async def test_caller_supplied_authorization_header_cannot_override():
    """Test that a caller-passed Authorization header is replaced, not kept."""
    route = respx.get(f"{_BASE_URL}/api/v3/x").mock(return_value=httpx.Response(200, json={}))
    session = AsyncAlbertSession(base_url=_BASE_URL, token="real-token")

    await session.get("/api/v3/x", headers={"Authorization": "Bearer spoofed"})

    assert route.calls.last.request.headers["Authorization"] == "Bearer real-token"


# --- HTTP verbs dispatch through _request -----------------------------------------


@respx.mock
async def test_post_sends_post_request_with_json_body():
    """Test that post() issues a POST with the given JSON body."""
    route = respx.post(f"{_BASE_URL}/api/v3/x").mock(
        return_value=httpx.Response(201, json={"id": "X1"})
    )

    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")
    response = await session.post("/api/v3/x", json={"name": "widget"})

    assert route.called
    assert route.calls.last.request.method == "POST"
    assert response.json() == {"id": "X1"}


@respx.mock
async def test_patch_sends_patch_request():
    """Test that patch() issues a PATCH request."""
    route = respx.patch(f"{_BASE_URL}/api/v3/x/1").mock(return_value=httpx.Response(200, json={}))

    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")
    await session.patch("/api/v3/x/1", json={"name": "new"})

    assert route.called
    assert route.calls.last.request.method == "PATCH"


@respx.mock
async def test_delete_sends_delete_request():
    """Test that delete() issues a DELETE request."""
    route = respx.delete(f"{_BASE_URL}/api/v3/x/1").mock(return_value=httpx.Response(204))

    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")
    await session.delete("/api/v3/x/1")

    assert route.called
    assert route.calls.last.request.method == "DELETE"


# --- status code -> exception mapping ---------------------------------------------


@pytest.mark.parametrize(
    "status,exc_cls",
    [
        (400, BadRequestError),
        (401, UnauthorizedError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (409, AlbertClientError),
        (500, InternalServerError),
        (502, BadGateway),
        (503, AlbertServerError),
    ],
)
@respx.mock
async def test_status_code_maps_to_expected_exception(status, exc_cls):
    """Test that each HTTP error status raises the corresponding SDK exception class."""
    respx.get(f"{_BASE_URL}/api/v3/x").mock(
        return_value=httpx.Response(status, json={"errors": "boom"})
    )
    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")

    with pytest.raises(exc_cls):
        await session.get("/api/v3/x")


@respx.mock
async def test_successful_response_is_returned_without_raising():
    """Test that a 2xx response is returned normally, with no exception raised."""
    respx.get(f"{_BASE_URL}/api/v3/x").mock(return_value=httpx.Response(200, json={"ok": True}))
    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")

    response = await session.get("/api/v3/x")

    assert response.json() == {"ok": True}


# --- lifecycle ----------------------------------------------------------------------


async def test_aclose_closes_the_underlying_client():
    """Test that aclose() closes the underlying httpx.AsyncClient."""
    session = AsyncAlbertSession(base_url=_BASE_URL, token="t")

    await session.aclose()

    assert session._client.is_closed


async def test_async_context_manager_closes_client_on_exit():
    """Test that using the session as an async context manager closes it on exit."""
    async with AsyncAlbertSession(base_url=_BASE_URL, token="t") as session:
        assert isinstance(session, AsyncAlbertSession)
        assert not session._client.is_closed

    assert session._client.is_closed
