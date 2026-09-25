"""Tests for AlbertSSOClient: URL building, token exchange, refresh, and validation.

``authenticate()`` itself binds a real local socket and blocks on an incoming
loopback connection (``server.handle_request()``); the offline network guard
blocks any real ``connect``, and feeding it a real request would require one.
So here ``local_http_server`` is replaced with a fake context manager that
hands back a server whose ``token`` is preset, exercising the surrounding
login/token-exchange logic without a real socket. The listener's own request
handling is covered directly in ``test_listener.py``.
"""

import contextlib
import json
from datetime import datetime, timedelta, timezone

import pytest
import requests
import responses

from albert.core.auth._manager import OAuthTokenInfo
from albert.core.auth.sso import AlbertSSOClient
from albert.exceptions import AlbertAuthError, UnauthorizedError
from tests.unit.conftest import UNIT_BASE_URL

_LOGIN_URL = f"{UNIT_BASE_URL}/api/v3/login"
_REFRESH_URL = f"{UNIT_BASE_URL}/api/v3/login/refresh"


def _client(**kwargs) -> AlbertSSOClient:
    return AlbertSSOClient(email="user@example.com", base_url=UNIT_BASE_URL, **kwargs)


class _FakeLocalServer:
    """Stand-in for the real HTTPServer: no socket, no blocking handle_request()."""

    def __init__(self, token: str | None) -> None:
        self.token = token

    def handle_request(self) -> None:
        pass


def _fake_local_http_server(token: str | None):
    """Build a drop-in replacement for ``local_http_server`` yielding a preset token."""

    @contextlib.contextmanager
    def _fake(*, minimum_port, maximum_port=None, timeout):
        yield _FakeLocalServer(token), minimum_port

    return _fake


# --- URL building (pure) ---------------------------------------------------------


def test_refresh_token_url_joins_base_url():
    """Test that refresh_token_url appends the refresh path to base_url."""
    client = _client()

    assert client.refresh_token_url == _REFRESH_URL


def test_build_login_url_without_tenant():
    """Test that the login URL omits tenantId when no tenant is given."""
    client = _client()

    url = client._build_login_url(port=5000, tenant_id=None)

    assert url == f"{_LOGIN_URL}?source=sdk&email=user%40example.com&port=5000"


def test_build_login_url_with_tenant():
    """Test that the login URL includes tenantId when a tenant is given."""
    client = _client()

    url = client._build_login_url(port=5000, tenant_id="acme")

    assert url == f"{_LOGIN_URL}?source=sdk&email=user%40example.com&port=5000&tenantId=acme"


# --- _validate_email --------------------------------------------------------------


@responses.activate
def test_validate_email_returns_none_on_redirect():
    """Test that a 302 (user has access) is treated as success with no return value."""
    client = _client()
    responses.get(_LOGIN_URL, status=302)

    assert client._validate_email(email=client.email, tenant_id=None) is None


@responses.activate
def test_validate_email_raises_on_not_found():
    """Test that a 404 response raises 'user not found or access denied'."""
    client = _client()
    responses.get(_LOGIN_URL, status=404)

    with pytest.raises(AlbertAuthError, match="User not found or access denied"):
        client._validate_email(email=client.email, tenant_id=None)


@responses.activate
def test_validate_email_raises_on_unexpected_status():
    """Test that any other status raises an 'unexpected response' error."""
    client = _client()
    responses.get(_LOGIN_URL, status=500)

    with pytest.raises(AlbertAuthError, match="Unexpected response"):
        client._validate_email(email=client.email, tenant_id=None)


@responses.activate
def test_validate_email_wraps_connection_error():
    """Test that a network-level request exception is wrapped in AlbertAuthError."""
    client = _client()
    responses.get(_LOGIN_URL, body=requests.exceptions.ConnectionError("boom"))

    with pytest.raises(AlbertAuthError, match="SSO Login failed"):
        client._validate_email(email=client.email, tenant_id=None)


# --- _request_access_token (refresh-token exchange) --------------------------------


@responses.activate
def test_request_access_token_single_tenant_populates_token_info():
    """Test that a single-tenant refresh response populates access_token and expiry."""
    client = _client()
    client._token_info = OAuthTokenInfo(refresh_token="rt1")
    responses.post(
        _REFRESH_URL,
        json=[{"jwt": "jwt1", "exp": 3600, "refreshToken": "rt2", "tenantId": "TEN1"}],
    )

    client._request_access_token()

    assert client._token_info.access_token == "jwt1"
    assert client._token_info.expires_in == 3600
    assert client._token_info.refresh_token == "rt2"
    assert client._token_info.tenant_id == "TEN1"
    sent_body = json.loads(responses.calls[0].request.body)
    assert sent_body == {"refreshtoken": "rt1"}


@responses.activate
def test_request_access_token_multiple_tenants_defaults_to_first_and_warns(caplog):
    """Test that multiple tenants with no tenant_id default to the first, with a warning."""
    client = _client()
    client._token_info = OAuthTokenInfo(refresh_token="rt1")
    responses.post(
        _REFRESH_URL,
        json=[
            {"jwt": "jwt1", "exp": 100, "refreshToken": "rt2", "tenantId": "TEN1"},
            {"jwt": "jwt2", "exp": 200, "refreshToken": "rt3", "tenantId": "TEN2"},
        ],
    )

    with caplog.at_level("WARNING"):
        client._request_access_token()

    assert client._token_info.tenant_id == "TEN1"
    assert any("multiple tenants" in record.message for record in caplog.records)


@responses.activate
def test_request_access_token_selects_matching_tenant():
    """Test that a specified tenant_id selects the matching entry, not the first."""
    client = _client()
    client._token_info = OAuthTokenInfo(refresh_token="rt1", tenant_id="ten2")
    responses.post(
        _REFRESH_URL,
        json=[
            {"jwt": "jwt1", "exp": 100, "refreshToken": "rt2", "tenantId": "TEN1"},
            {"jwt": "jwt2", "exp": 200, "refreshToken": "rt3", "tenantId": "TEN2"},
        ],
    )

    client._request_access_token()

    assert client._token_info.access_token == "jwt2"
    assert client._token_info.tenant_id == "TEN2"


@responses.activate
def test_request_access_token_tenant_not_found_raises():
    """Test that a tenant_id absent from the response raises AlbertAuthError."""
    client = _client()
    client._token_info = OAuthTokenInfo(refresh_token="rt1", tenant_id="ten9")
    responses.post(
        _REFRESH_URL,
        json=[{"jwt": "jwt1", "exp": 100, "refreshToken": "rt2", "tenantId": "TEN1"}],
    )

    with pytest.raises(AlbertAuthError, match="User not found or access denied"):
        client._request_access_token()


@responses.activate
def test_request_access_token_sets_refresh_time_with_one_minute_buffer():
    """Test that _refresh_time is expires_in from now, minus a one-minute buffer."""
    client = _client()
    client._token_info = OAuthTokenInfo(refresh_token="rt1")
    responses.post(
        _REFRESH_URL,
        json=[{"jwt": "jwt1", "exp": 3600, "refreshToken": "rt2", "tenantId": "TEN1"}],
    )

    before = datetime.now(timezone.utc)
    client._request_access_token()
    after = datetime.now(timezone.utc)

    expected_low = before + timedelta(seconds=3600) - timedelta(minutes=1)
    expected_high = after + timedelta(seconds=3600) - timedelta(minutes=1)
    assert expected_low <= client._refresh_time <= expected_high


@responses.activate
def test_request_access_token_raises_mapped_exception_on_http_error():
    """Test that a failed refresh request raises the SDK's mapped HTTP exception."""
    client = _client()
    client._token_info = OAuthTokenInfo(refresh_token="rt1")
    responses.post(_REFRESH_URL, status=401, json={"errors": "bad refresh token"})

    with pytest.raises(UnauthorizedError):
        client._request_access_token()


# --- get_access_token ---------------------------------------------------------------


def test_get_access_token_raises_when_never_authenticated():
    """Test that get_access_token requires authenticate() to have run first."""
    client = _client()

    with pytest.raises(AlbertAuthError, match=r"Call `\.authenticate\(\)` first"):
        client.get_access_token()


def test_get_access_token_raises_when_refresh_token_missing():
    """Test that a token_info without a refresh_token is treated as unauthenticated."""
    client = _client()
    client._token_info = OAuthTokenInfo(refresh_token="")

    with pytest.raises(AlbertAuthError, match=r"Call `\.authenticate\(\)` first"):
        client.get_access_token()


def test_get_access_token_caches_until_expiry():
    """Test that a cached, unexpired token is returned without a refresh call."""
    client = _client()
    client._token_info = OAuthTokenInfo(access_token="cached", refresh_token="rt1")
    client._refresh_time = datetime.now(timezone.utc) + timedelta(hours=1)

    assert client.get_access_token() == "cached"


@responses.activate
def test_get_access_token_refreshes_when_expired():
    """Test that an expired cached token triggers a refresh and returns the new token."""
    client = _client()
    client._token_info = OAuthTokenInfo(access_token="old", refresh_token="rt1", tenant_id="TEN1")
    client._refresh_time = datetime.now(timezone.utc) - timedelta(seconds=1)
    responses.post(
        _REFRESH_URL,
        json=[{"jwt": "new-jwt", "exp": 100, "refreshToken": "rt2", "tenantId": "TEN1"}],
    )

    assert client.get_access_token() == "new-jwt"


# --- authenticate() with a faked local_http_server ------------------------------------


@responses.activate
def test_authenticate_returns_token_info_with_refresh_token(monkeypatch: pytest.MonkeyPatch):
    """Test that authenticate() validates the email, opens a browser, and captures the token."""
    client = _client()
    opened_urls: list[str] = []
    monkeypatch.setattr("albert.core.auth.sso.webbrowser.open", opened_urls.append)
    monkeypatch.setattr(
        "albert.core.auth.sso.local_http_server", _fake_local_http_server("refresh-tok")
    )
    responses.get(_LOGIN_URL, status=302)

    token_info = client.authenticate()

    assert token_info.refresh_token == "refresh-tok"
    assert len(opened_urls) == 1
    assert opened_urls[0].startswith(_LOGIN_URL)


@responses.activate
def test_authenticate_uppercases_tenant_id(monkeypatch: pytest.MonkeyPatch):
    """Test that a lowercase tenant_id passed in is stored uppercased on the token."""
    client = _client()
    monkeypatch.setattr("albert.core.auth.sso.webbrowser.open", lambda url: None)
    monkeypatch.setattr(
        "albert.core.auth.sso.local_http_server", _fake_local_http_server("refresh-tok")
    )
    responses.get(_LOGIN_URL, status=302)

    token_info = client.authenticate(tenant_id="acme")

    assert token_info.tenant_id == "ACME"


@responses.activate
def test_authenticate_raises_when_no_token_returned(monkeypatch: pytest.MonkeyPatch):
    """Test that a callback with no token raises AlbertAuthError."""
    client = _client()
    monkeypatch.setattr("albert.core.auth.sso.webbrowser.open", lambda url: None)
    monkeypatch.setattr("albert.core.auth.sso.local_http_server", _fake_local_http_server(None))
    responses.get(_LOGIN_URL, status=302)

    with pytest.raises(AlbertAuthError, match="SSO Login failed! Please try again."):
        client.authenticate()


@responses.activate
def test_authenticate_propagates_email_validation_failure(monkeypatch: pytest.MonkeyPatch):
    """Test that authenticate() fails fast if the email/tenant check fails, before opening a browser."""
    client = _client()
    opened_urls: list[str] = []
    monkeypatch.setattr("albert.core.auth.sso.webbrowser.open", opened_urls.append)
    monkeypatch.setattr(
        "albert.core.auth.sso.local_http_server", _fake_local_http_server("should-not-be-used")
    )
    responses.get(_LOGIN_URL, status=404)

    with pytest.raises(AlbertAuthError, match="User not found or access denied"):
        client.authenticate()

    assert opened_urls == []
