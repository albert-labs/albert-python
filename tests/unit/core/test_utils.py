"""Unit tests for shared utility helpers in albert.core.utils."""

from __future__ import annotations

import importlib.util
import inspect
import json
import warnings
from pathlib import Path
from types import ModuleType

import pytest
import requests

from albert.core import utils
from albert.core.utils import ensure_list, find_stack_level, unpack_bulk_created_items
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


# ---------------------------------------------------------------------------
# find_stack_level
# ---------------------------------------------------------------------------

_FAKE_SDK_SOURCE = """
import warnings

from pydantic import validate_call

from albert.core.utils import find_stack_level


def _helper():
    warnings.warn("ignored change", UserWarning, stacklevel=find_stack_level())


@validate_call
def public_method(*, value: int):
    _helper()


def public_method_hardcoded():
    _helper_hardcoded()


def _helper_hardcoded():
    warnings.warn("hardcoded", UserWarning, stacklevel=2)
"""


@pytest.fixture
def fake_sdk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """A module that find_stack_level treats as SDK-internal, like ``src/albert``."""
    package_dir = tmp_path / "fake_sdk"
    package_dir.mkdir()
    module_path = package_dir / "collection.py"
    module_path.write_text(_FAKE_SDK_SOURCE)
    monkeypatch.setattr(
        utils, "_INTERNAL_PACKAGE_DIRS", (*utils._INTERNAL_PACKAGE_DIRS, f"{package_dir}/")
    )
    spec = importlib.util.spec_from_file_location("fake_sdk_collection", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_find_stack_level_attributes_a_direct_warning_to_the_calling_line():
    """Test that a warning raised outside the SDK is attributed to its own line."""
    with pytest.warns(UserWarning) as record:
        line = inspect.currentframe().f_lineno + 1
        warnings.warn("direct", UserWarning, stacklevel=find_stack_level())

    assert (record[0].filename, record[0].lineno) == (__file__, line)


def test_find_stack_level_skips_validate_call_and_helper_frames(fake_sdk):
    """Test that a warning from a helper behind @validate_call is attributed to the caller."""
    with pytest.warns(UserWarning, match="ignored change") as record:
        line = inspect.currentframe().f_lineno + 1
        fake_sdk.public_method(value=1)

    assert (record[0].filename, record[0].lineno) == (__file__, line)


def test_hardcoded_stacklevel_is_attributed_to_sdk_internals(fake_sdk):
    """Test that a hardcoded stacklevel lands inside the SDK, which find_stack_level avoids."""
    with pytest.warns(UserWarning, match="hardcoded") as record:
        fake_sdk.public_method_hardcoded()

    assert record[0].filename == fake_sdk.__file__
