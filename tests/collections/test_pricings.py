import uuid

import pytest

from albert import Albert
from albert.resources.inventory import InventoryItem
from albert.resources.locations import Location
from albert.resources.pricings import Pricing

pytestmark = pytest.mark.xdist_group("inventory")


def test_get_by_inventory_id(
    client: Albert, seeded_inventory: list[InventoryItem], seeded_pricings: list[Pricing]
):
    found = client.pricings.get_by_inventory_id(inventory_id=seeded_inventory[0].id)
    for f in found:
        assert isinstance(f, Pricing)


def test_get_by_id(client: Albert, seeded_pricings: list[Pricing]):
    found = client.pricings.get_by_id(id=seeded_pricings[0].id)
    assert isinstance(found, Pricing)
    assert found.description == seeded_pricings[0].description
    assert found.id == seeded_pricings[0].id


def test_update(client: Albert, seeded_pricings: list[Pricing], seeded_locations: list[Location]):
    """Test update changes description, location, and default."""
    pricing = client.pricings.get_by_id(id=seeded_pricings[0].id)
    updated_description = f"TEST - {uuid.uuid4()}"
    pricing.description = updated_description
    pricing.location = seeded_locations[1]
    pricing.default = 1
    assert client.pricings.update(pricing=pricing)
    updated = client.pricings.get_by_id(id=pricing.id)
    assert updated.description == updated_description
    assert updated.location.id == seeded_locations[1].id
    assert updated.default == 1


def test_get_by_id_includes_default(client: Albert, seeded_pricings: list[Pricing]):
    """Test get_by_id exposes the default flag."""
    found = client.pricings.get_by_id(id=seeded_pricings[0].id)
    assert found.default is None or found.default in (0, 1)
