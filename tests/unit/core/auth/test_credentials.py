"""Tests for AlbertClientCredentials: token fetch shape, caching, expiry, refresh."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import pytest
import responses
from pydantic import SecretStr

from albert.core.auth._manager import OAuthTokenInfo
from albert.core.auth.credentials import AlbertClientCredentials
from albert.exceptions import UnauthorizedError
from tests.unit.conftest import UNIT_BASE_URL


def _cached_token_info() -> OAuthTokenInfo:
    return OAuthTokenInfo(access_token="cached", refresh_token="r", expires_in=3600)


_TOKEN_PATH = "/api/v3/login/oauth/token"
_TOKEN_URL = f"{UNIT_BASE_URL}{_TOKEN_PATH}"


def _creds() -> AlbertClientCredentials:
    return AlbertClientCredentials(
        id="my-client-id",
        secret=SecretStr("my-client-secret"),
        base_url=UNIT_BASE_URL,
    )


def test_oauth_token_url_joins_base_url():
    """Test that oauth_token_url appends the token path to base_url."""
    creds = _creds()

    assert creds.oauth_token_url == _TOKEN_URL


@responses.activate
def test_request_access_token_sends_client_credentials_grant():
    """Test that the token request sends a form-encoded client_credentials grant."""
    creds = _creds()
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600},
    )

    creds._request_access_token()

    sent = responses.calls[0].request
    assert sent.headers["Content-Type"] == "application/x-www-form-urlencoded"
    body = parse_qs(sent.body)
    assert body["grant_type"] == ["client_credentials"]
    assert body["client_id"] == ["my-client-id"]
    assert body["client_secret"] == ["my-client-secret"]


@responses.activate
def test_request_access_token_stores_token_info():
    """Test that a successful token response populates _token_info from the body."""
    creds = _creds()
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600},
    )

    creds._request_access_token()

    assert creds._token_info.access_token == "tok1"
    assert creds._token_info.refresh_token == "r1"
    assert creds._token_info.expires_in == 3600


@responses.activate
def test_request_access_token_sets_refresh_time_with_one_minute_buffer():
    """Test that _refresh_time is expires_in from now, minus a one-minute buffer."""
    creds = _creds()
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600},
    )

    before = datetime.now(timezone.utc)
    creds._request_access_token()
    after = datetime.now(timezone.utc)

    expected_low = before + timedelta(seconds=3600) - timedelta(minutes=1)
    expected_high = after + timedelta(seconds=3600) - timedelta(minutes=1)
    assert expected_low <= creds._refresh_time <= expected_high


@responses.activate
def test_request_access_token_raises_mapped_exception_on_http_error():
    """Test that a failed token request raises the SDK's mapped HTTP exception."""
    creds = _creds()
    responses.post(_TOKEN_URL, status=401, json={"errors": "bad credentials"})

    with pytest.raises(UnauthorizedError):
        creds._request_access_token()


@responses.activate
def test_get_access_token_fetches_on_first_call():
    """Test that get_access_token performs a token request when no token is cached."""
    creds = _creds()
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600},
    )

    token = creds.get_access_token()

    assert token == "tok1"
    assert len(responses.calls) == 1


@responses.activate
def test_get_access_token_caches_until_expiry():
    """Test that a cached, unexpired token is reused without a second request."""
    creds = _creds()
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600},
    )

    first = creds.get_access_token()
    second = creds.get_access_token()

    assert first == second == "tok1"
    assert len(responses.calls) == 1


@responses.activate
def test_get_access_token_refreshes_after_expiry():
    """Test that an expired cached token triggers a new token request."""
    creds = _creds()
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600},
    )
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok2", "refresh_token": "r2", "expires_in": 3600},
    )

    first = creds.get_access_token()
    creds._refresh_time = datetime.now(timezone.utc) - timedelta(seconds=1)
    second = creds.get_access_token()

    assert first == "tok1"
    assert second == "tok2"
    assert len(responses.calls) == 2


@responses.activate
def test_get_access_token_refreshes_when_never_fetched():
    """Test that a fresh credentials instance with no token_info always refreshes."""
    creds = _creds()
    assert creds._token_info is None
    responses.post(
        _TOKEN_URL,
        json={"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600},
    )

    token = creds.get_access_token()

    assert token == "tok1"


def test_get_access_token_skips_refresh_if_another_caller_already_did(
    monkeypatch: pytest.MonkeyPatch,
):
    """Test the double-checked lock: a refresh already done inside the lock is not repeated.

    Simulates another thread refreshing between the outer and inner
    ``_requires_refresh()`` checks in ``get_access_token``.
    """
    creds = _creds()
    creds._token_info = _cached_token_info()
    calls = {"n": 0}

    def fake_requires_refresh() -> bool:
        calls["n"] += 1
        return calls["n"] == 1  # True outside the lock, False on the inner re-check

    def fail_if_called() -> None:
        raise AssertionError("_request_access_token should not run for a fresh token")

    monkeypatch.setattr(creds, "_requires_refresh", fake_requires_refresh)
    monkeypatch.setattr(creds, "_request_access_token", fail_if_called)

    token = creds.get_access_token()

    assert token == "cached"
