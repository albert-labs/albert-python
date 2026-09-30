"""Unit tests for shared utility helpers in albert.core.utils."""

from __future__ import annotations

import json

import pytest
import requests

from albert.core.utils import ensure_list, unpack_bulk_created_items
from albert.exceptions import AlbertPartialError


def _response(body, *, status_code: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(body).encode()
    return response


# ---------------------------------------------------------------------------
# ensure_list
# ---------------------------------------------------------------------------


def test_ensure_list_returns_none_for_none():
    """Test that None is preserved as None rather than wrapped in a list."""
    assert ensure_list(None) is None


def test_ensure_list_returns_same_list_instance():
    """Test that an existing list is returned unchanged, not copied."""
    value = ["a", "b"]

    assert ensure_list(value) is value


def test_ensure_list_converts_tuple_to_list():
    """Test that a tuple is converted to a list, preserving order."""
    assert ensure_list(("a", "b")) == ["a", "b"]


def test_ensure_list_converts_set_to_list():
    """Test that a set is converted to a list."""
    result = ensure_list({"a"})

    assert result == ["a"]


def test_ensure_list_wraps_a_scalar_string():
    """Test that a bare string is wrapped in a single-item list, not iterated char by char."""
    assert ensure_list("abc") == ["abc"]


def test_ensure_list_wraps_a_scalar_number():
    """Test that a bare number is wrapped in a single-item list."""
    assert ensure_list(5) == [5]


# ---------------------------------------------------------------------------
# unpack_bulk_created_items
# ---------------------------------------------------------------------------


def test_unpack_bulk_created_items_returns_bare_list_as_is():
    """Test that a plain list response body is returned unchanged."""
    response = _response([{"id": "A1"}, {"id": "A2"}])

    assert unpack_bulk_created_items(response) == [{"id": "A1"}, {"id": "A2"}]


def test_unpack_bulk_created_items_returns_created_items_when_no_failures():
    """Test that a full-success 206-shaped body returns just the created items."""
    response = _response({"CreatedItems": [{"id": "A1"}], "FailedItems": []})

    assert unpack_bulk_created_items(response) == [{"id": "A1"}]


def test_unpack_bulk_created_items_missing_keys_returns_empty_list():
    """Test that a body with neither key returns an empty list rather than raising."""
    response = _response({})

    assert unpack_bulk_created_items(response) == []


def test_unpack_bulk_created_items_raises_partial_error_on_failures():
    """Test that any failed items raise AlbertPartialError carrying both item lists."""
    response = _response(
        {
            "CreatedItems": [{"id": "A1"}],
            "FailedItems": [{"id": "A2", "error": "duplicate"}],
        }
    )

    with pytest.raises(AlbertPartialError) as exc_info:
        unpack_bulk_created_items(response)

    error = exc_info.value
    assert error.created_items == [{"id": "A1"}]
    assert error.failed_items == [{"id": "A2", "error": "duplicate"}]
    assert "1 item(s) created" in str(error)
    assert "1 item(s) failed" in str(error)


def test_unpack_bulk_created_items_partial_error_with_no_created_items():
    """Test that a total failure still raises with an empty created_items list."""
    response = _response({"CreatedItems": [], "FailedItems": [{"id": "A1", "error": "bad"}]})

    with pytest.raises(AlbertPartialError) as exc_info:
        unpack_bulk_created_items(response)

    assert exc_info.value.created_items == []
    assert exc_info.value.failed_items == [{"id": "A1", "error": "bad"}]
