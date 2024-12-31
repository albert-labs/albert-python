from albert.albert import Albert
from albert.resources.lots import Lot


def _list_asserts(returned_list):
    found = False
    for i, c in enumerate(returned_list):
        if i == 100:
            break
        found = True
        assert isinstance(c, Lot)
        assert isinstance(c.id, str)
        assert c.id.startswith("LOT")
    assert found


def test_simple_lot_list(
    client: Albert,
    seeded_lots,  # PUT on lots currently broken, so we can't seed lots
):
    simple_list = client.lots.list()
    _list_asserts(simple_list)


def test_get_by_id(client: Albert, seeded_lots: list[Lot]):
    got_lot = client.lots.get_by_id(id=seeded_lots[0].id)
    assert got_lot.id == seeded_lots[0].id
    assert got_lot.external_barcode_id == seeded_lots[0].external_barcode_id


def test_get_by_ids(client: Albert, seeded_lots: list[Lot]):
    got_lots = client.lots.get_by_ids(ids=[l.id for l in seeded_lots])
    assert len(got_lots) == len(seeded_lots)
    seeded_ids = [l.id for l in seeded_lots]
    for l in got_lots:
        assert l.id in seeded_ids
