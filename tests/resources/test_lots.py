import pytest

from albert.resources.lots import Lot

pytestmark = pytest.mark.xdist_group("inventory")


def test_private_attrs(seeded_lots: list[Lot]):
    for l in seeded_lots:
        # assert l.metadata.cogs is None
        # assert l.metadata.raw_cost is None
        assert l.barcode_id is not None
        assert l.has_attachments is None
        assert l.has_notes is None
