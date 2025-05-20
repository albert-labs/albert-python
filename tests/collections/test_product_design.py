from albert import Albert
from albert.resources.inventory import InventoryItem
from albert.resources.product_design import UnpackedProductDesign


def test_get_unpacked(client: Albert, seeded_products: list[InventoryItem]):
    ids = [p.id for p in seeded_products]
    unpacked = client.product_design.get_unpacked_products(inventory_ids=ids)
    assert len(unpacked) == len(seeded_products)
    for u in unpacked:
        assert isinstance(u, UnpackedProductDesign)
        inv_list_ids = [x.row_inventory_id for x in u.inventory_list]
        assert all([x.row_inventory_id in inv_list_ids for x in u.inventories])
