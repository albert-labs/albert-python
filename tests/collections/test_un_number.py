from albert.client import Albert
from albert.collections.un_numbers import UnNumber


def assert_valid_un_number_items(returned_list):
    for u in returned_list[:10]:
        assert isinstance(u, UnNumber)
        assert isinstance(u.un_number, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("UNN")


def test_un_number_get_all_with_pagination(client: Albert):
    """Test UNNumber.get_all supports pagination and returns expected items."""
    paginated = list(client.un_numbers.get_all(max_items=10))
    assert_valid_un_number_items(paginated)


def test_un_number_get_all_with_filters(client: Albert):
    """Test UNNumber.get_all supports filters like name + exact_match."""
    filtered = list(client.un_numbers.get_all(name="56", exact_match=False, max_items=10))
    assert_valid_un_number_items(filtered)


# TO FIX! Need to have at least one UN Number loaded to the test environment.
# def test_un_number_get_by(client: Albert):
# found_un = client.un_numbers.get_by_name(name="UN9006")
# assert isinstance(found_un, UnNumber)
# found_by_id = client.un_numbers.get_by_id(un_number_id=found_un.id)
# assert isinstance(found_by_id, UnNumber)
# assert found_by_id.un_number == found_un.un_number
# assert found_by_id.id == found_un.id
