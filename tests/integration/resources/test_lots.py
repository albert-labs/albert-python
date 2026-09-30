import pytest

from albert.resources.lots import Lot, LotVolumeUnit

pytestmark = pytest.mark.xdist_group("inventory")


def test_private_attrs(seeded_lots: list[Lot]):
    for l in seeded_lots:
        # assert l.metadata.cogs is None
        # assert l.metadata.raw_cost is None
        assert l.barcode_id is not None
        assert l.has_attachments is None
        assert l.has_notes is None


def test_seeded_volume_lot(seeded_lots: list[Lot]):
    volume_lot = seeded_lots[3]
    assert volume_lot.inventory_on_hand_l is not None
    assert volume_lot.inventory_on_hand_l == pytest.approx(127.39)
    assert volume_lot.entry_unit == LotVolumeUnit.LITER
    assert volume_lot.density is not None
    assert volume_lot.density.value == pytest.approx(0.785)
