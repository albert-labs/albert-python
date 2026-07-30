import uuid
from contextlib import suppress

import pytest

from albert import Albert
from albert.exceptions import NotFoundError
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
    pricing = seeded_pricings[0]
    updated_description = f"TEST - {uuid.uuid4()}"
    pricing.description = updated_description
    pricing.location = seeded_locations[1]
    assert client.pricings.update(pricing=pricing)
    updated = client.pricings.get_by_id(id=pricing.id)
    assert updated.description == updated_description
    assert updated.location.id == seeded_locations[1].id


def test_create_with_default(
    client: Albert,
    seed_prefix: str,
    seeded_inventory: list[InventoryItem],
    seeded_locations: list[Location],
):
    """Test create accepts default=1 and returns it on get_by_id."""
    pricing = Pricing(
        inventory_id=seeded_inventory[0].id,
        company=seeded_inventory[0].company,
        location=seeded_locations[0],
        description=f"{seed_prefix} - default pricing create",
        price=99.0,
        default=1,
    )
    created = client.pricings.create(pricing=pricing)
    try:
        assert created.default == 1
        fetched = client.pricings.get_by_id(id=created.id)
        assert fetched.default == 1
    finally:
        with suppress(NotFoundError):
            client.pricings.delete(id=created.id)


def test_update_default(
    client: Albert,
    seed_prefix: str,
    seeded_inventory: list[InventoryItem],
    seeded_locations: list[Location],
):
    """Test update can set default=1 on an existing pricing."""
    pricing = Pricing(
        inventory_id=seeded_inventory[0].id,
        company=seeded_inventory[0].company,
        location=seeded_locations[0],
        description=f"{seed_prefix} - default pricing update",
        price=88.0,
    )
    created = client.pricings.create(pricing=pricing)
    try:
        created.default = 1
        updated = client.pricings.update(pricing=created)
        assert updated.default == 1
        fetched = client.pricings.get_by_id(id=created.id)
        assert fetched.default == 1
    finally:
        with suppress(NotFoundError):
            client.pricings.delete(id=created.id)
