import pytest
from pydantic import ValidationError

from albert.core.shared.models.base import EntityLink
from albert.resources.cas import Cas
from albert.resources.inventory import (
    CasAmount,
    InventoryCategory,
    InventoryDensity,
    InventoryItem,
    InventoryUnitCategory,
)


def test_cas_amount_attributes():
    cas = Cas(number="test", smiles="CCC", id="dogs")
    amt = CasAmount(min=5, max=95, cas=cas)

    assert amt.cas is cas
    assert amt.id == "dogs"
    assert amt.number == "test"
    assert amt.cas_smiles == "CCC"

    data = amt.model_dump(exclude_none=True)
    assert set(data.keys()) == {"min", "max", "id"}

    full = amt.model_dump(exclude_none=False)
    assert set(full.keys()) == {
        "min",
        "max",
        "target",
        "id",
        "cas_category",
        "inventory_function",
        "created",
        "updated",
        "classification_type",
        "type",
        "substance_id",
    }


def test_formula_requirements():
    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test",
            description="Test",
            category=InventoryCategory.FORMULAS,
        )


def test_inventory_metadata_preserves_named_links_and_supports_id_only_links():
    item = InventoryItem(
        name="Test",
        category=InventoryCategory.RAW_MATERIALS,
        metadata={
            "named": [{"id": "LST1", "name": "United States"}],
            "id_only": [EntityLink(id="LST2")],
        },
    )

    assert item.metadata["named"][0].name == "United States"
    assert item.model_dump(mode="json", by_alias=True)["Metadata"] == {
        "named": [{"id": "LST1", "name": "United States"}],
        "id_only": [{"id": "LST2"}],
    }


def test_inventory_volume_density_coercion_and_serialization():
    item = InventoryItem(
        name="Test Volume Item",
        category=InventoryCategory.RAW_MATERIALS,
        unit_category=InventoryUnitCategory.VOLUME,
        density=0.785,
    )
    assert isinstance(item.density, InventoryDensity)
    assert item.density.value == 0.785

    dumped = item.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["density"] == 0.785
    assert isinstance(dumped["density"], (int, float))


def test_inventory_volume_density_validation():
    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test Volume Item",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.VOLUME,
        )

    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test Volume Item",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.VOLUME,
            density=0,
        )

    with pytest.raises(ValidationError):
        InventoryItem(
            name="Test Volume Item",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.VOLUME,
            density=-0.5,
        )


def test_inventory_volume_get_deserialization_without_density():
    item = InventoryItem(
        name="Existing Volume Item",
        category=InventoryCategory.RAW_MATERIALS,
        unit_category=InventoryUnitCategory.VOLUME,
        albertId="INVA12345",
    )
    assert item.id == "INVA12345"
    assert item.density is None
