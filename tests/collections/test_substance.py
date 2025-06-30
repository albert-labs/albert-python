from albert.client import Albert
from albert.resources.substance import SubstanceInfo


def test_get_by_ids(client: Albert):
    cas_ids = [
        "134180-76-0",
        "26530-20-1",
        "68515-48-0",
        "8050-31-5",
        "9003-11-6",
        "1330-20-7",
        "100-41-4",
        "68951-99-5",
        "7732-18-5",
        "117-81-7",
        "77-90-7",
        "2634-33-5",
        "1310-73-2",
        "25067-95-2",
        "1310-58-3",
        "61790-50-9",
    ]
    substances = client.substances.get_by_ids(cas_ids=cas_ids)
    assert isinstance(substances, list)
    assert len(substances) == len(cas_ids)
    for substance in substances:
        assert isinstance(substance, SubstanceInfo)


def test_get_by_id(client: Albert):
    substance = client.substances.get_by_id(cas_id="134180-76-0")
    assert substance is not None
    assert isinstance(substance, SubstanceInfo)
    assert substance.cas_id == "134180-76-0"


def test_get_by_id_bad_cas_id(client: Albert):
    substance = client.substances.get_by_id(cas_id="not-a-cas-id")
    assert not substance.is_known


def test_get_multiple_ids_with_unknown_substances(client: Albert):
    substances = client.substances.get_by_ids(cas_ids=["1310-73-2", "not-a-cas-id", "134180-76-0"])
    assert len(substances) == 3

    # For some reason the API returns the substances in no particular order, so we need to check explicitly
    # that for the given cas IDs we get the correct substance type back
    for substance in substances:
        if substance.cas_id in ["134180-76-0", "1310-73-2"]:
            assert substance.is_known
        else:
            assert not substance.is_known


def test_get_by_id_with_region(client: Albert):
    substance = client.substances.get_by_id(cas_id="134180-76-0", region="EU")
    assert substance is not None
    assert substance.cas_id == "134180-76-0"
