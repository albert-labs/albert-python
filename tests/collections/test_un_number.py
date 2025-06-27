from albert.client import Albert
from albert.collections.un_numbers import UnNumber


def assert_un_number_items(returned_list):
    for i, u in enumerate(returned_list):
        if i == 100:
            break
        assert isinstance(u, UnNumber)
        assert isinstance(u.un_number, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("UNN")


def test_simple_un_number_list(client: Albert):
    simple_list = client.un_numbers.get_all()
    assert_un_number_items(simple_list)


def test_advanced_un_number_list(client: Albert):
    adv_list = client.un_numbers.get_all(name="56", exact_match=False)
    assert_un_number_items(adv_list)


# TO FIX! Need to have at least one UN Number loaded to the test environment.
# def test_un_number_get_by(client: Albert):
# found_un = client.un_numbers.get_by_name(name="UN9006")
# assert isinstance(found_un, UnNumber)
# found_by_id = client.un_numbers.get_by_id(un_number_id=found_un.id)
# assert isinstance(found_by_id, UnNumber)
# assert found_by_id.un_number == found_un.un_number
# assert found_by_id.id == found_un.id
