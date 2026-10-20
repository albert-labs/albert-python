import pytest

from albert.resources.inventory import (
    InventoryItem,
)

pytestmark = pytest.mark.xdist_group("inventory")


def test_inventory_item_private_attributes(seeded_inventory: list[InventoryItem]):
    assert seeded_inventory[0].formula_id == None
    assert seeded_inventory[0].project_id == None
