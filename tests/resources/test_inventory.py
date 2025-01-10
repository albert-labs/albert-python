import pytest
from pydantic import ValidationError

from albert.resources.cas import Cas
from albert.resources.inventory import (
    CasAmount,
    InventoryCategory,
    InventoryItem,
    InventoryMinimum,
)


def test_cas_amount_attributes():
    amt = CasAmount(min=5, max=95)
    cas = Cas(number="test", smiles="CCC", id="dogs")

    amt.cas = cas
    assert amt.cas == cas
    assert amt.id == cas.id
    assert amt.number == cas.number
    assert amt.cas_smiles == cas.smiles

    data = amt.model_dump()
    assert set(data.keys()) == {"id", "min", "max", "target", "cas_category"}


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


def test_formula_requirements():
    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test",
            description="Test",
            category=InventoryCategory.FORMULAS,
        )
