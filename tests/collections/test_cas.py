import uuid

import pytest

from albert.client import Albert
from albert.core.shared.enums import OrderBy
from albert.exceptions import AlbertHTTPError
from albert.resources.cas import Cas


def assert_valid_cas_items(items: list[Cas]):
    assert items, "Expected at least one CAS result"
    for c in items[:10]:
        assert isinstance(c, Cas)
        assert isinstance(c.number, str)
        assert not c.name or isinstance(c.name, str)
        assert c.id.startswith("CAS")


def test_cas_get_all_with_pagination(client: Albert):
    """Test that CAS get_all() respects pagination via max_items."""
    simple_list = list(client.cas_numbers.get_all(max_items=10))
    assert_valid_cas_items(simple_list)
    assert len(simple_list) <= 10


def test_cas_get_all_with_filters(client: Albert, seeded_cas: list[Cas]):
    """Test CAS get_all() with number and id filters."""
    number = seeded_cas[0].number

    adv_list = list(
        client.cas_numbers.get_all(
            number=number,
            order_by=OrderBy.DESCENDING,
            max_items=10,
        )
    )
    assert_valid_cas_items(adv_list)
    assert adv_list[0].number == number

    adv_list2 = list(
        client.cas_numbers.get_all(
            id=seeded_cas[0].id,
            max_items=10,
        )
    )
    assert adv_list[0].id == seeded_cas[0].id
    assert_valid_cas_items(adv_list2)

    cas_nums = [seeded_cas[0].number, seeded_cas[1].number]
    multi_cas = list(client.cas_numbers.get_all(cas=cas_nums))
    assert_valid_cas_items(multi_cas)


def test_cas_not_found(client: Albert):
    """Test that requesting a CAS by invalid ID raises an error."""
    with pytest.raises(AlbertHTTPError):
        client.cas_numbers.get_by_id(id="foo bar")


def test_cas_exists(client: Albert, seeded_cas: list[Cas]):
    """Test that exists() returns True for known CAS and False for unknown CAS."""
    cas_number = seeded_cas[0].number
    assert client.cas_numbers.exists(number=cas_number)
    assert not client.cas_numbers.exists(number=f"{uuid.uuid4()}")


def test_update_cas(client: Albert, seed_prefix: str, seeded_cas: list[Cas]):
    """Test that updating a CAS object reflects changes."""
    cas_to_update = seeded_cas[0]
    updated_description = f"{seed_prefix} - A new description"
    cas_to_update.description = updated_description

    updated_cas = client.cas_numbers.update(updated_object=cas_to_update)

    assert updated_cas.description == updated_description


def test_get_by_number(client: Albert, seeded_cas: list[Cas]):
    """Test get_by_number() returns the correct CAS using exact match."""
    returned_cas = client.cas_numbers.get_by_number(number=seeded_cas[0].number, exact_match=True)
    assert returned_cas.id == seeded_cas[0].id
    assert returned_cas.number == seeded_cas[0].number


def test_get_or_create_cas(client: Albert, seeded_cas: list[Cas]):
    """Test get or create returns existing CAS."""
    cas_number = seeded_cas[0].number
    cas = client.cas_numbers.get_or_create(cas=cas_number)
    assert cas.id == seeded_cas[0].id
