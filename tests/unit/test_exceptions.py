import json
import pickle

import httpx
import pytest
import requests

from albert.exceptions import (
    AlbertClientError,
    AlbertHTTPError,
    AlbertPartialError,
    AlbertServerError,
    BadGateway,
    BadRequestError,
    CombinationGenerationError,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    PreconditionFailedError,
    PreconditionRequiredError,
    UnauthorizedError,
    UnsupportedMediaTypeError,
    _get_http_error_cls,
    handle_async_http_errors,
    handle_http_errors,
)
from albert.resources.tasks import PropertyTask


def _make_not_found_response() -> requests.Response:
    """Simulate a 404 returned by the Albert API for a missing project resource."""
    req = requests.PreparedRequest()
    req.method = "GET"
    req.url = "https://app.albertinvent.com/api/v3/projects/PRJ0001"
    req.body = None

    resp = requests.Response()
    resp.status_code = 404
    resp.reason = "Not Found"
    resp.request = req
    resp._content = json.dumps({"errors": "Not Found"}).encode()
    resp.encoding = "utf-8"
    return resp


def _make_response(
    *,
    status_code: int,
    reason: str = "Error",
    body: bytes = b"",
    method: str = "GET",
    url: str = "https://app.albertinvent.com/api/v3/x",
    request_body: bytes | None = None,
) -> requests.Response:
    """Build a requests.Response with a real PreparedRequest attached."""
    req = requests.PreparedRequest()
    req.method = method
    req.url = url
    req.body = request_body

    resp = requests.Response()
    resp.status_code = status_code
    resp.reason = reason
    resp.request = req
    resp._content = body
    resp.encoding = "utf-8"
    return resp


def _make_httpx_response(
    *,
    status_code: int,
    body: bytes = b"",
    method: str = "GET",
    url: str = "https://app.albertinvent.com/api/v3/x",
) -> httpx.Response:
    request = httpx.Request(method, url)
    return httpx.Response(status_code, content=body, request=request)


@pytest.mark.parametrize(
    "exc_cls",
    [
        AlbertHTTPError,
        AlbertClientError,
        BadRequestError,
        UnauthorizedError,
        ForbiddenError,
        NotFoundError,
        ConflictError,
        PreconditionFailedError,
        UnsupportedMediaTypeError,
        PreconditionRequiredError,
        AlbertServerError,
        InternalServerError,
    ],
)
def test_albert_http_error_is_picklable(exc_cls):
    """Test that AlbertHTTPError and all subclasses survive a pickle round-trip.

    Python's default exception pickling stores args and calls __init__(*args) on
    unpickle. AlbertHTTPError.__init__ expects a requests.Response, not a string,
    so the default path raises AttributeError. __reduce__ fixes this by
    reconstructing from the pre-formatted message string instead.
    """
    try:
        raise exc_cls(_make_not_found_response())
    except exc_cls as exc:
        original_message = exc.message
        restored = pickle.loads(pickle.dumps(exc))

    assert type(restored) is exc_cls
    assert restored.message == original_message


def test_pickle_preserves_message_content():
    """Test that the Albert API URL, status code, and error body survive pickling."""
    try:
        raise NotFoundError(_make_not_found_response())
    except NotFoundError as exc:
        restored = pickle.loads(pickle.dumps(exc))

    assert "404" in restored.message
    assert "Not Found" in restored.message
    assert "/api/v3/projects/PRJ0001" in restored.message


def test_pickle_sets_response_to_none():
    """Test that response is None after pickling — requests.Response is not serializable."""
    try:
        raise NotFoundError(_make_not_found_response())
    except NotFoundError as exc:
        assert exc.response is not None
        restored = pickle.loads(pickle.dumps(exc))

    assert restored.response is None


def _make_error_response(status_code: int, reason: str) -> requests.Response:
    """Simulate an error response returned by the Albert API."""
    req = requests.PreparedRequest()
    req.method = "PATCH"
    req.url = "https://app.albertinvent.com/api/v4.0/master-data/units/UNT0001"
    req.body = None

    resp = requests.Response()
    resp.status_code = status_code
    resp.reason = reason
    resp.request = req
    resp._content = json.dumps({"errors": reason}).encode()
    resp.encoding = "utf-8"
    return resp


@pytest.mark.parametrize(
    "status_code,reason,exc_cls",
    [
        (409, "Conflict", ConflictError),
        (412, "Precondition Failed", PreconditionFailedError),
        (415, "Unsupported Media Type", UnsupportedMediaTypeError),
        (428, "Precondition Required", PreconditionRequiredError),
    ],
)
def test_handle_http_errors_maps_typed_exceptions(status_code, reason, exc_cls):
    """Test that each status code maps to its typed exception carrying the response."""
    response = _make_error_response(status_code, reason)

    with pytest.raises(exc_cls) as exc_info, handle_http_errors():
        raise requests.HTTPError(response=response)

    exc = exc_info.value
    assert exc.response is response
    assert str(status_code) in exc.message
    assert reason in exc.message


def test_combination_generation_error_attributes():
    """Test that CombinationGenerationError preserves task, failed_blocks, and job_states."""
    task = PropertyTask(id="TASFOR123", name="Test Task")
    failed_blocks = ["BLK2", "BLK3"]
    job_states = {"BLK1": "successful", "BLK2": "failed", "BLK3": "failed"}

    err = CombinationGenerationError(
        "Combination generation failed for blocks: BLK2, BLK3",
        task=task,
        failed_blocks=failed_blocks,
        job_states=job_states,
    )

    assert err.task.id == "TASFOR123"
    assert err.failed_blocks == ["BLK2", "BLK3"]
    assert err.job_states == job_states
    assert "Combination generation failed" in str(err)


# --- status code -> exception class mapping -----------------------------------


@pytest.mark.parametrize(
    "status_code,expected_cls",
    [
        (400, BadRequestError),
        (401, UnauthorizedError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (409, ConflictError),
        (410, AlbertClientError),
        (412, PreconditionFailedError),
        (415, UnsupportedMediaTypeError),
        (428, PreconditionRequiredError),
        (429, AlbertClientError),
        (500, InternalServerError),
        (502, BadGateway),
        (503, AlbertServerError),
        (599, AlbertServerError),
    ],
)
def test_get_http_error_cls_maps_status_code(status_code, expected_cls):
    """Test that each status code maps to its documented exception class."""
    assert _get_http_error_cls(status_code) is expected_cls


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: _get_http_error_cls's fallback branch does `raise AlbertHTTPError` "
        "(bare class) for a status code outside 400-599, but AlbertHTTPError.__init__ "
        "requires a `response` argument, so this raises TypeError instead of a "
        "usable AlbertHTTPError (src/albert/exceptions.py:121-122)."
    ),
)
def test_get_http_error_cls_unmapped_status_code_raises_albert_http_error():
    """Test that an out-of-range status code still raises an AlbertHTTPError."""
    with pytest.raises(AlbertHTTPError):
        _get_http_error_cls(999)


# --- message extraction: different error body shapes (sync) -------------------


def test_format_message_extracts_string_errors_field():
    """Test that a JSON body with a string 'errors' field is used verbatim."""
    resp = _make_response(status_code=404, body=json.dumps({"errors": "not found"}).encode())

    message = AlbertHTTPError._format_message(resp)

    assert "Errors: not found" in message


def test_format_message_extracts_nested_errors_field():
    """Test that a JSON body with a dict 'errors' field is stringified in the message."""
    resp = _make_response(
        status_code=400,
        body=json.dumps({"errors": {"field": "name", "issue": "required"}}).encode(),
    )

    message = AlbertHTTPError._format_message(resp)

    assert "'field': 'name'" in message
    assert "'issue': 'required'" in message


def test_format_message_falls_back_to_whole_payload_without_errors_key():
    """Test that a JSON body with no 'errors' key uses the whole payload as the error."""
    resp = _make_response(status_code=400, body=json.dumps({"message": "bad input"}).encode())

    message = AlbertHTTPError._format_message(resp)

    assert "'message': 'bad input'" in message


def test_format_message_omits_errors_suffix_for_empty_payload():
    """Test that an empty JSON object produces no 'Errors:' suffix."""
    resp = _make_response(status_code=500, body=b"{}")

    message = AlbertHTTPError._format_message(resp)

    assert "Errors:" not in message
    assert "500" in message


def test_format_message_uses_response_text_for_non_json_body():
    """Test that a non-JSON body falls back to the raw response text."""
    resp = _make_response(status_code=502, body=b"upstream is down")

    message = AlbertHTTPError._format_message(resp)

    assert "Errors: upstream is down" in message


def test_format_message_omits_suffix_for_empty_non_json_body():
    """Test that an empty, non-JSON body produces no 'Errors:' suffix."""
    resp = _make_response(status_code=502, body=b"")

    message = AlbertHTTPError._format_message(resp)

    assert "Errors:" not in message


def test_bad_request_error_appends_request_body():
    """Test that BadRequestError appends the outgoing request body to the message."""
    resp = _make_response(
        status_code=400,
        body=json.dumps({"errors": "invalid"}).encode(),
        request_body=b'{"name": "widget"}',
    )

    message = BadRequestError._format_message(resp)

    assert 'Body:\nb\'{"name": "widget"}\'' in message


# --- handle_http_errors (sync context manager) ---------------------------------


def test_handle_http_errors_reraises_non_http_error():
    """Test that handle_http_errors does not swallow unrelated exceptions."""
    with pytest.raises(ValueError), handle_http_errors():
        raise ValueError("unrelated")


def test_handle_http_errors_raises_mapped_exception_on_status():
    """Test that a raise_for_status() HTTPError is remapped to the SDK exception class."""
    resp = _make_response(status_code=404, body=json.dumps({"errors": "missing"}).encode())

    with pytest.raises(NotFoundError) as exc_info, handle_http_errors():
        resp.raise_for_status()

    assert "Errors: missing" in exc_info.value.message
    assert exc_info.value.response is resp


def test_handle_http_errors_does_not_raise_for_success():
    """Test that a successful response passes through handle_http_errors untouched."""
    resp = _make_response(status_code=200)

    with handle_http_errors():
        resp.raise_for_status()  # no-op for 2xx, should not raise


# --- handle_async_http_errors (async context manager) ---------------------------


async def test_handle_async_http_errors_reraises_non_http_error():
    """Test that handle_async_http_errors does not swallow unrelated exceptions."""
    with pytest.raises(ValueError):
        async with handle_async_http_errors():
            raise ValueError("unrelated")


async def test_handle_async_http_errors_raises_mapped_exception_on_status():
    """Test that an httpx raise_for_status() error is remapped to the SDK exception class."""
    resp = _make_httpx_response(status_code=404, body=json.dumps({"errors": "missing"}).encode())

    with pytest.raises(NotFoundError) as exc_info:
        async with handle_async_http_errors():
            resp.raise_for_status()

    assert "Errors: missing" in exc_info.value.message


async def test_handle_async_http_errors_uses_response_text_for_non_json_body():
    """Test that a non-JSON httpx response body falls back to raw text in the message."""
    resp = _make_httpx_response(status_code=502, body=b"gateway exploded")

    with pytest.raises(BadGateway) as exc_info:
        async with handle_async_http_errors():
            resp.raise_for_status()

    assert "Errors: gateway exploded" in exc_info.value.message


async def test_handle_async_http_errors_does_not_raise_for_success():
    """Test that a successful httpx response passes through untouched."""
    resp = _make_httpx_response(status_code=200)

    async with handle_async_http_errors():
        resp.raise_for_status()  # no-op for 2xx, should not raise


async def test_handle_async_http_errors_omits_suffix_for_empty_body():
    """Test that an async error with no body content produces no 'Errors:' suffix."""
    resp = _make_httpx_response(status_code=500, body=b"")

    with pytest.raises(InternalServerError) as exc_info:
        async with handle_async_http_errors():
            resp.raise_for_status()

    assert "Errors:" not in exc_info.value.message
    assert "500" in exc_info.value.message


# --- AlbertPartialError ----------------------------------------------------------


def test_albert_partial_error_defaults_to_empty_lists():
    """Test that omitted created_items/failed_items default to empty lists, not None."""
    err = AlbertPartialError("2 of 5 items failed")

    assert err.created_items == []
    assert err.failed_items == []
    assert str(err) == "2 of 5 items failed"


def test_albert_partial_error_preserves_items():
    """Test that AlbertPartialError preserves the created and failed item lists."""
    created = [{"id": "INV1"}]
    failed = [{"id": "INV2", "error": "duplicate"}]

    err = AlbertPartialError("partial success", created_items=created, failed_items=failed)

    assert err.created_items == created
    assert err.failed_items == failed


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: handle_async_http_errors builds its exception via "
        "Exception.__new__(error_cls, message) and never sets `.response`, unlike the "
        "sync path where AlbertHTTPError.__init__ always sets self.response "
        "(src/albert/exceptions.py:144-148). Accessing `.response` on an async-raised "
        "error raises AttributeError instead of returning the httpx.Response."
    ),
)
async def test_handle_async_http_errors_sets_response_attribute():
    """Test that an async-raised HTTP error exposes the triggering response."""
    resp = _make_httpx_response(status_code=404, body=json.dumps({"errors": "missing"}).encode())

    with pytest.raises(NotFoundError) as exc_info:
        async with handle_async_http_errors():
            resp.raise_for_status()

    assert exc_info.value.response is resp


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: handle_async_http_errors formats the message inline instead of calling "
        "error_cls._format_message(response), so BadRequestError's request-body suffix "
        "never appears on the async path even though it always appears on the sync path "
        "(src/albert/exceptions.py:72-76 vs 137-142)."
    ),
)
async def test_handle_async_http_errors_bad_request_includes_body():
    """Test that an async 400 error includes the outgoing request body, like the sync path."""
    resp = _make_httpx_response(status_code=400, body=json.dumps({"errors": "invalid"}).encode())

    with pytest.raises(BadRequestError) as exc_info:
        async with handle_async_http_errors():
            resp.raise_for_status()

    assert "Body:" in exc_info.value.message
