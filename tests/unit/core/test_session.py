"""Tests for ``AlbertSession``: URL joining, query encoding, timeout, auth, retries.

These exercise the real ``requests.Session`` request path with ``responses`` faking
the transport, so behavior (headers sent, URL built, exceptions raised) is verified
against what actually goes over the wire rather than against a hand-rolled stub.
"""

import pytest
import requests
import responses

from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
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
from tests.unit.conftest import UNIT_BASE_URL


class _FakeAuthManager:
    """Minimal duck-typed auth manager exposing only what AlbertSession needs."""

    def __init__(self, token: str) -> None:
        self._token = token
        self.calls = 0

    def get_access_token(self) -> str:
        self.calls += 1
        return self._token


# --- construction -----------------------------------------------------------


def test_requires_token_or_auth_manager():
    """Test that omitting both token and auth_manager raises ValueError."""
    with pytest.raises(ValueError):
        AlbertSession(base_url=UNIT_BASE_URL)


def test_static_token_used_when_no_auth_manager():
    """Test that the access token comes from the static token by default."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="static-token")

    assert session._access_token == "static-token"


def test_auth_manager_overrides_static_token():
    """Test that an auth_manager takes priority over a provided static token."""
    manager = _FakeAuthManager("manager-token")
    session = AlbertSession(base_url=UNIT_BASE_URL, token="static-token", auth_manager=manager)

    assert session._access_token == "manager-token"
    assert manager.calls == 1


# --- URL joining -------------------------------------------------------------


@responses.activate
def test_relative_path_is_joined_with_base_url():
    """Test that a relative path is appended to the session's base_url."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x/1", json={})

    session.get("/api/v3/x/1")

    assert responses.calls[0].request.url == f"{UNIT_BASE_URL}/api/v3/x/1"


@responses.activate
def test_absolute_url_path_bypasses_base_url():
    """Test that a path already starting with http is used as-is, ignoring base_url."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get("https://other.example/api/v3/x/1", json={})

    session.get("https://other.example/api/v3/x/1")

    assert responses.calls[0].request.url == "https://other.example/api/v3/x/1"


@responses.activate
def test_leading_slash_path_resets_to_base_url_root():
    """Test the urljoin gotcha: a leading-slash path drops any base_url subpath.

    ``urljoin`` treats a path beginning with "/" as rooted at the host, discarding
    whatever path segments the base_url carried.
    """
    session = AlbertSession(base_url=f"{UNIT_BASE_URL}/tenant/sub/", token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x")

    assert responses.calls[0].request.url == f"{UNIT_BASE_URL}/api/v3/x"


@responses.activate
def test_base_url_without_trailing_slash_still_joins_relative_path():
    """Test that a base_url with no trailing slash still joins a relative path correctly."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x")

    assert responses.calls[0].request.url == f"{UNIT_BASE_URL}/api/v3/x"


# --- _encode_query_params ----------------------------------------------------


def test_encode_query_params_converts_bool_to_lowercase_json():
    """Test that booleans are encoded as lowercase JSON literals, not Python str()."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    result = session._encode_query_params({"active": True, "archived": False})

    assert result == {"active": "true", "archived": "false"}


def test_encode_query_params_converts_enum_to_value():
    """Test that a bare Enum value is replaced with its underlying value."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    result = session._encode_query_params({"order": OrderBy.DESCENDING})

    assert result == {"order": "desc"}


def test_encode_query_params_converts_list_of_enums():
    """Test that a list containing only Enum members is converted element-wise."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    result = session._encode_query_params({"orders": [OrderBy.ASCENDING, OrderBy.DESCENDING]})

    assert result == {"orders": ["asc", "desc"]}


def test_encode_query_params_leaves_mixed_list_unconverted():
    """Test that a list mixing Enum and non-Enum items is passed through unchanged.

    The conversion only fires when every item in the list is an Enum member.
    """
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    result = session._encode_query_params({"mixed": [1, OrderBy.ASCENDING]})

    assert result == {"mixed": [1, OrderBy.ASCENDING]}


def test_encode_query_params_drops_none_values():
    """Test that keys whose value is None are dropped entirely, not sent as empty."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    result = session._encode_query_params({"keep": "x", "drop": None})

    assert result == {"keep": "x"}


def test_encode_query_params_passes_through_plain_values():
    """Test that ordinary scalar values are returned unchanged."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    result = session._encode_query_params({"limit": 25, "text": "water"})

    assert result == {"limit": 25, "text": "water"}


# --- query string on the wire -------------------------------------------------


@responses.activate
def test_query_params_are_quoted_with_space_not_plus():
    """Test that query values use %20 for spaces (quote), not + (quote_plus).

    The SDK encodes manually via ``quote`` because ``requests``' default
    ``quote_plus`` breaks CAS pagination.
    """
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x", params={"text": "hello world"})

    assert responses.calls[0].request.url == f"{UNIT_BASE_URL}/api/v3/x?text=hello%20world"


@responses.activate
def test_list_query_param_is_repeated_not_comma_joined():
    """Test that a list-valued query param is sent as repeated key=value pairs."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x", params={"ids": ["a", "b"]})

    assert responses.calls[0].request.url == f"{UNIT_BASE_URL}/api/v3/x?ids=a&ids=b"


@responses.activate
def test_no_query_string_appended_when_params_empty():
    """Test that an empty or all-None params dict produces a bare URL with no '?'."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x", params={"drop": None})

    assert responses.calls[0].request.url == f"{UNIT_BASE_URL}/api/v3/x"


# --- Authorization header -----------------------------------------------------


@responses.activate
def test_authorization_header_from_static_token():
    """Test that the Authorization header carries the static bearer token."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="abc123")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x")

    assert responses.calls[0].request.headers["Authorization"] == "Bearer abc123"


@responses.activate
def test_authorization_header_from_auth_manager():
    """Test that the Authorization header is refreshed from the auth manager each call."""
    manager = _FakeAuthManager("manager-token")
    session = AlbertSession(base_url=UNIT_BASE_URL, auth_manager=manager)
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x")

    assert responses.calls[0].request.headers["Authorization"] == "Bearer manager-token"


@responses.activate
def test_caller_supplied_authorization_header_cannot_override():
    """Test that a caller-passed Authorization header is replaced, not merged or kept."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="real-token")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", json={})

    session.get("/api/v3/x", headers={"Authorization": "Bearer spoofed"})

    assert responses.calls[0].request.headers["Authorization"] == "Bearer real-token"


# --- timeout passthrough -------------------------------------------------------


def test_default_timeout_is_none_when_not_configured(monkeypatch: pytest.MonkeyPatch):
    """Test that requests have no timeout by default (kwargs.setdefault with None)."""
    captured = {}

    def fake_send(self, request, **kwargs):
        captured.update(kwargs)
        resp = requests.Response()
        resp.status_code = 200
        resp.request = request
        resp._content = b"{}"
        return resp

    monkeypatch.setattr(requests.Session, "send", fake_send)
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    session.get("/api/v3/x")

    assert captured["timeout"] is None


def test_session_timeout_applied_by_default(monkeypatch: pytest.MonkeyPatch):
    """Test that a session-level timeout is used when a call doesn't pass its own."""
    captured = {}

    def fake_send(self, request, **kwargs):
        captured.update(kwargs)
        resp = requests.Response()
        resp.status_code = 200
        resp.request = request
        resp._content = b"{}"
        return resp

    monkeypatch.setattr(requests.Session, "send", fake_send)
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t", timeout=7.5)

    session.get("/api/v3/x")

    assert captured["timeout"] == 7.5


def test_per_call_timeout_overrides_session_default(monkeypatch: pytest.MonkeyPatch):
    """Test that a per-call timeout takes precedence over the session default."""
    captured = {}

    def fake_send(self, request, **kwargs):
        captured.update(kwargs)
        resp = requests.Response()
        resp.status_code = 200
        resp.request = request
        resp._content = b"{}"
        return resp

    monkeypatch.setattr(requests.Session, "send", fake_send)
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t", timeout=7.5)

    session.get("/api/v3/x", timeout=2)

    assert captured["timeout"] == 2


# --- status code -> exception mapping -----------------------------------------


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
@responses.activate
def test_status_code_maps_to_expected_exception(status, exc_cls):
    """Test that each HTTP error status raises the corresponding SDK exception class."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", status=status, json={"errors": "boom"})

    with pytest.raises(exc_cls):
        session.get("/api/v3/x")


@responses.activate
def test_successful_response_is_returned_without_raising():
    """Test that a 2xx response is returned normally, with no exception raised."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")
    responses.get(f"{UNIT_BASE_URL}/api/v3/x", status=200, json={"ok": True})

    response = session.get("/api/v3/x")

    assert response.json() == {"ok": True}


# --- retry configuration on the mounted adapter -------------------------------


def test_default_retry_configuration_on_adapter():
    """Test the urllib3 Retry object mounted by default (3 retries, backoff, forcelist)."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t")

    retry = session.get_adapter(UNIT_BASE_URL).max_retries

    assert retry.total == 3
    assert retry.read == 3
    assert retry.connect == 3
    assert retry.backoff_factor == 0.3
    assert retry.status_forcelist == (500, 502, 503, 504, 403)
    assert retry.raise_on_status is False


def test_custom_retries_configures_adapter():
    """Test that a custom retries count is applied to both mounted adapters."""
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t", retries=5)

    http_retry = session.get_adapter("http://unit.test").max_retries
    https_retry = session.get_adapter("https://unit.test").max_retries

    assert http_retry.total == 5
    assert https_retry.total == 5


def test_zero_retries_is_respected_not_treated_as_falsy_default():
    """Test that retries=0 disables retries instead of falling back to the default of 3.

    The fallback is gated on ``is not None``, not on truthiness, so 0 must stick.
    """
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t", retries=0)

    retry = session.get_adapter(UNIT_BASE_URL).max_retries

    assert retry.total == 0


# --- extra headers --------------------------------------------------------------


def test_extra_headers_do_not_replace_authorization_slot():
    """Test that extra constructor headers merge over defaults but never set auth.

    Authorization is applied per-request from credentials, so it is absent from
    the session's static header dict even when other headers are supplied.
    """
    session = AlbertSession(base_url=UNIT_BASE_URL, token="t", headers={"X-Custom": "value"})

    assert session.headers["X-Custom"] == "value"
    assert "Authorization" not in session.headers
