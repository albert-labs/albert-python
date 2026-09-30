import pytest
from pydantic import ValidationError

from albert.resources.storage_locations import StorageLocation, StorageLocationFilter


def test_storage_location_create_type_still_requires_location():
    """Test that StorageLocation (the create/update type) still requires a parent Location."""
    with pytest.raises(ValidationError):
        StorageLocation(name="No Parent")


def test_storage_location_filter_is_name_only():
    """Test that the search filter type validates with a name only (no parent Location)."""
    f = StorageLocationFilter(name="Freezer A")
    assert f.model_dump() == {"name": "Freezer A"}
