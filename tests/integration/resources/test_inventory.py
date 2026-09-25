import pytest
from pydantic import ValidationError

from albert.resources.inventory import (
    InventoryItem,
    InventoryMinimum,
)

pytestmark = pytest.mark.xdist_group("inventory")


def test_inventory_minimum(seeded_locations):
    with pytest.raises(ValidationError):
        InventoryMinimum(
            minimum=1,
        )

    with pytest.raises(ValidationError):
        InventoryMinimum(
            minimum=0,
            location=seeded_locations[0],
            id=seeded_locations[2].id,
        )


def test_inventory_item_private_attributes(seeded_inventory: list[InventoryItem]):
    assert seeded_inventory[0].formula_id == None
    assert seeded_inventory[0].project_id == None
