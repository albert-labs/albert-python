"""Unit tests for Python version support warnings."""

import importlib
import sys
import warnings

import pytest

import albert

_EXPECTED_MESSAGE = (
    "Python 3.10 reached end of life in October 2026. The Albert Python SDK will stop "
    "supporting it in releases after 2027-02-28. Upgrade to Python 3.11 or later to keep "
    "receiving updates."
)


def test_python_310_deprecation_warns_from_the_importing_file(monkeypatch):
    """Test that Python 3.10 warns customers from their import statement."""
    monkeypatch.setattr(sys, "version_info", (3, 10, 22))

    with pytest.warns(FutureWarning) as record:
        importlib.reload(albert)

    assert len(record) == 1
    assert str(record[0].message) == _EXPECTED_MESSAGE
    assert record[0].filename == __file__


@pytest.mark.parametrize("version_info", [(3, 11, 0), (3, 12, 0), (3, 13, 0), (3, 14, 0)])
def test_supported_python_versions_do_not_warn(monkeypatch, version_info):
    """Test that supported Python versions do not emit the 3.10 warning."""
    monkeypatch.setattr(sys, "version_info", version_info)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        importlib.reload(albert)

    assert [item for item in record if item.category is FutureWarning] == []
