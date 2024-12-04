import uuid

from albert import Albert
from albert.resources.inventory import InventoryItem
from albert.resources.locations import Location
from albert.resources.pricings import Pricing


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
    pricing = seeded_pricings[0]
    updated_description = f"TEST - {uuid.uuid4()}"
    pricing.description = updated_description
    pricing.location = seeded_locations[1]
    assert client.pricings.update(pricing=pricing)
    updated = client.pricings.get_by_id(id=pricing.id)
    assert updated.description == updated_description
    assert updated.location.id == seeded_locations[1].id
