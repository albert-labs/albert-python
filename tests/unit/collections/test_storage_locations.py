import pytest

from albert.collections.storage_locations import StorageLocationsCollection
from albert.core.shared.models.base import EntityLink
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation


def _location(id: str = "LOC1") -> Location:
    return Location(
        id=id,
        name="Lab",
        latitude=0.0,
        longitude=0.0,
        address="1 Main St",
    )


def _storage_location(name: str = "Freezer A", location_id: str = "LOC1") -> StorageLocation:
    return StorageLocation(name=name, location=EntityLink(id=location_id))


@pytest.mark.parametrize(
    ("candidate_name", "query_name", "expected"),
    [
        pytest.param("Freezer A", "Freezer A", True, id="same-name"),
        pytest.param("Freezer A", "freezer a", True, id="case-insensitive"),
        pytest.param("Freezer B", "Freezer A", False, id="different-name"),
        pytest.param("Freezer A2", "Freezer A", False, id="partial-name"),
    ],
)
def test_matches_name_and_location_exact_match(
    candidate_name: str, query_name: str, expected: bool
):
    """Test exact matching compares names case-insensitively."""
    result = StorageLocationsCollection._matches_name_and_location(
        _storage_location(name=candidate_name),
        name=query_name,
        exact_match=True,
        location=_location(),
    )

    assert result is expected


@pytest.mark.parametrize(
    ("query_name", "expected"),
    [
        pytest.param("freezer", True, id="substring"),
        pytest.param("Cabinet", False, id="unrelated-name"),
    ],
)
def test_matches_name_and_location_substring_match(query_name: str, expected: bool):
    """Test non-exact matching accepts case-insensitive substrings only."""
    result = StorageLocationsCollection._matches_name_and_location(
        _storage_location(),
        name=query_name,
        exact_match=False,
        location=_location(),
    )

    assert result is expected


def test_matches_name_and_location_rejects_different_parent():
    """Test a matching name at another parent location is rejected."""
    result = StorageLocationsCollection._matches_name_and_location(
        _storage_location(location_id="LOC2"),
        name="Freezer A",
        exact_match=True,
        location=_location(id="LOC1"),
    )

    assert result is False
