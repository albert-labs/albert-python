import pytest

from albert import Albert
from albert.resources.inventory import InventoryItem
from albert.resources.product_design import UnpackedProductDesign
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("sheets")


def test_search(client: Albert, seed_prefix: str, seeded_products: list[InventoryItem]):
    """Test search finds the seeded formula on the product design grid."""
    seeded_ids = {p.id for p in seeded_products}
    hits = poll_until(
        lambda: [
            hit
            for hit in client.product_design.search(text=seed_prefix, max_items=50)
            if hit.id in seeded_ids
        ]
    )
    assert hits, "Expected seeded formula in product design search results"
    assert seeded_products[0].id in {hit.id for hit in hits}


def test_get_unpacked(client: Albert, seeded_products: list[InventoryItem]):
    ids = [p.id for p in seeded_products]
    unpacked = client.product_design.get_unpacked_products(inventory_ids=ids)
    assert len(unpacked) == len(seeded_products)
    for u in unpacked:
        assert isinstance(u, UnpackedProductDesign)
        inv_list_ids = [x.row_inventory_id for x in u.inventory_list]
        assert all([x.row_inventory_id in inv_list_ids for x in u.inventories])
