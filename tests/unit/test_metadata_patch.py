"""Unit tests for metadata PATCH payload generation.

Allowed under the patch-builder exception in OPINIONS.md: these guard non-obvious
diff behavior in ``BaseCollection._generate_metadata_diff`` with no I/O to fake.
"""

from albert.collections.base import BaseCollection
from albert.core.shared.models.base import EntityLink
from albert.core.shared.models.patch import PatchOperation


def test_metadata_add_single_item_list_stays_a_list() -> None:
    """Test a one-item list metadata ADD keeps list cardinality.

    The API stores an ADD newValue verbatim, so collapsing a single-item list to
    a scalar corrupts the field's type on the server.
    """
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"listField": [EntityLink(id="LST1")]},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.ADD
    assert data[0].attribute == "Metadata.listField"
    assert data[0].new_value == ["LST1"]


def test_metadata_add_multi_item_list_unchanged() -> None:
    """Test a multi-item list metadata ADD still sends all ids as a list."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"listField": [EntityLink(id="LST1"), EntityLink(id="LST2")]},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.ADD
    assert data[0].new_value == ["LST1", "LST2"]


def test_metadata_add_scalar_unchanged() -> None:
    """Test a scalar metadata ADD still sends the bare value."""
    data = BaseCollection(session=None)._generate_metadata_diff(
        existing_metadata={},
        updated_metadata={"textField": "value"},
    )

    assert len(data) == 1
    assert data[0].operation == PatchOperation.ADD
    assert data[0].new_value == "value"
