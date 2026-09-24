import pytest

from albert.core.shared.models.base import EntityLink
from albert.resources.inventory import InventoryDensity
from albert.resources.lots import Lot, LotVolumeUnit

pytestmark = pytest.mark.xdist_group("inventory")


def test_private_attrs(seeded_lots: list[Lot]):
    for l in seeded_lots:
        # assert l.metadata.cogs is None
        # assert l.metadata.raw_cost is None
        assert l.barcode_id is not None
        assert l.has_attachments is None
        assert l.has_notes is None


def test_lot_volume_coercion_and_serialization():
    lot = Lot(
        inventory_id="INVA123",
        storage_location=EntityLink(id="STL123"),
        initial_quantity=100.0,
        inventory_on_hand=100.0,
        initial_quantity_l=127.39,
        entry_unit=LotVolumeUnit.LITER,
        cost=80.0,
        cost_l=62.8,
        density="0.785",
    )
    assert isinstance(lot.density, InventoryDensity)
    assert lot.density.value == pytest.approx(0.785)
    assert lot.entry_unit == LotVolumeUnit.LITER

    dumped = lot.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["density"] == "0.785"
    assert dumped["initialQuantityL"] == "127.39"
    assert dumped["costL"] == "62.8"
    assert dumped["entryUnit"] == "L"


def test_seeded_volume_lot(seeded_lots: list[Lot]):
    volume_lot = seeded_lots[3]
    assert volume_lot.inventory_on_hand_l is not None
    assert volume_lot.inventory_on_hand_l == pytest.approx(127.39)
    assert volume_lot.entry_unit == LotVolumeUnit.LITER
    assert volume_lot.density is not None
    assert volume_lot.density.value == pytest.approx(0.785)
