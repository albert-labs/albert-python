import uuid

import pytest

from albert.albert import Albert
from albert.collections.base import OrderBy
from albert.exceptions import AlbertHTTPError
from albert.resources.cas import Cas


def _list_asserts(returned_list):
    found = False
    for i, c in enumerate(returned_list):
        if i == 30:
            break
        assert isinstance(c, Cas)
        assert isinstance(c.number, str)
        if c.name:
            assert isinstance(c.name, str)
        assert c.id.startswith("CAS")
        found = True
    assert found


def test_simple_cas_list(client: Albert):
    simple_list = client.cas_numbers.list()
    _list_asserts(simple_list)


def test_cas_not_found(client: Albert):
    with pytest.raises(AlbertHTTPError):
        client.cas_numbers.get_by_id(id="foo bar")


def test_advanced_cas_list(client: Albert, seeded_cas: list[Cas]):
    number = seeded_cas[0].number
    adv_list = client.cas_numbers.list(number=number, order_by=OrderBy.DESCENDING)
    adv_list = list(adv_list)
    _list_asserts(adv_list)

    assert adv_list[0].number == number

    adv_list2 = client.cas_numbers.list(id=seeded_cas[0].id)
    _list_asserts(adv_list2)

    small_page = client.cas_numbers.list(limit=2)
    _list_asserts(small_page)


def test_cas_exists(client: Albert, seeded_cas: list[Cas]):
    # Check if CAS exists for a seeded CAS number
    cas_number = seeded_cas[0].number
    assert client.cas_numbers.cas_exists(number=cas_number)

    # Check if CAS does not exist for a non-existent CAS number
    assert not client.cas_numbers.cas_exists(number=f"{uuid.uuid4()}")


def test_update_cas(client: Albert, seed_prefix: str, seeded_cas: list[Cas]):
    # Update the description of a seeded CAS entry
    cas_to_update = seeded_cas[0]
    updated_description = f"{seed_prefix} - A new description"
    cas_to_update.description = updated_description

    updated_cas = client.cas_numbers.update(updated_object=cas_to_update)

    assert updated_cas.description == updated_description


def test_get_by_number(client: Albert, seeded_cas: list[Cas]):
    returned_cas = client.cas_numbers.get_by_number(number=seeded_cas[0].number, exact_match=True)
    assert returned_cas.id == seeded_cas[0].id
    assert returned_cas.number == seeded_cas[0].number
