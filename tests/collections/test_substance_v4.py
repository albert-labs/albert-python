import pytest

from albert.client import Albert
from albert.resources.substance_v4 import (
    SubstanceV4Info,
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


# TODO: search tests disabled — backend pagination bug causes duplicates and
# inconsistent page sizes. Re-enable once the backend fixes startKey/limit behaviour.
# Ticket filed with backend team.

# def test_search_by_search_key(client: Albert): ...
# def test_search_by_cas(client: Albert): ...
# def test_search_by_name(client: Albert): ...
# def test_search_max_items(client: Albert): ...
# def test_search_with_start_key(client: Albert): ...


# TODO: update_metadata test disabled — requires a tenant-owned substance.
# Global substances (from regulatory DB) return 404 on metadata patch.
# Re-enable once a tenant-specific substance fixture is available.

# def test_update_metadata(client: Albert): ...
