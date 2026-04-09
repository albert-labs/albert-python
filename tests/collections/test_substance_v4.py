import pytest

from albert.client import Albert
from albert.resources.substance_v4 import (
    SubstanceV4Info,
    SubstanceV4Metadata,
    SubstanceV4SearchItem,
)

CAS_IDS = [
    "134180-76-0",
    "26530-20-1",
    "68515-48-0",
    "1330-20-7",
    "7732-18-5",
]


def test_get_by_ids(client: Albert):
    """Test retrieving multiple substances by CAS IDs."""
    substances = client.substances_v4.get_by_ids(cas_ids=CAS_IDS)
    assert isinstance(substances, list)
    assert len(substances) >= len(CAS_IDS)
    for substance in substances:
        assert isinstance(substance, SubstanceV4Info)


def test_get_by_id(client: Albert):
    """Test retrieving a single substance by CAS ID."""
    substance = client.substances_v4.get_by_id(cas_id="7732-18-5")
    assert substance is not None
    assert isinstance(substance, SubstanceV4Info)
    assert substance.cas_id == "7732-18-5"


def test_get_by_id_region(client: Albert):
    """Test retrieving a substance with a specific region."""
    substance = client.substances_v4.get_by_id(cas_id="134180-76-0", region="EU")
    assert substance is not None
    assert substance.cas_id == "134180-76-0"


def test_get_by_ids_requires_at_least_one_identifier(client: Albert):
    """Test that get_by_ids raises when no identifier is provided."""
    with pytest.raises(ValueError):
        client.substances_v4.get_by_ids()


def test_search_by_search_key(client: Albert):
    """Test searching substances by free-text search key."""
    results = list(client.substances_v4.search(search_key="test"))
    assert len(results) > 0
    for item in results:
        assert isinstance(item, SubstanceV4SearchItem)


def test_search_by_cas(client: Albert):
    """Test searching substances by CAS identifier."""
    results = list(client.substances_v4.search(cas="7732-18-5"))
    assert len(results) > 0
    assert any(item.cas_id == "7732-18-5" for item in results)


def test_search_by_name(client: Albert):
    """Test searching substances by name."""
    results = list(client.substances_v4.search(name="water"))
    assert len(results) > 0
    for item in results:
        assert isinstance(item, SubstanceV4SearchItem)


def test_search_max_items(client: Albert):
    """Test that max_items limits the number of results returned."""
    results = list(client.substances_v4.search(search_key="test", max_items=2))
    assert len(results) <= 2


def test_search_with_start_key(client: Albert):
    """Test resuming search from a non-zero start_key offset."""
    all_results = list(client.substances_v4.search(search_key="test", max_items=10))
    if len(all_results) < 4:
        pytest.skip("Not enough results to test start_key offset.")
    offset_results = list(client.substances_v4.search(search_key="test", start_key=2, max_items=2))
    assert len(offset_results) > 0


def test_update_metadata(client: Albert):
    """Test updating metadata fields on a known substance."""
    substance = client.substances_v4.get_by_id(cas_id=CAS_IDS[0])
    assert substance.substance_id is not None

    client.substances_v4.update_metadata(
        id=substance.substance_id,
        metadata=SubstanceV4Metadata(notes="sdk test note"),
    )
