from albert.resources.parameters import ParameterSearchItem


def test_parameter_search_item_allows_missing_id():
    """Test that a partial parameter search result remains valid without an ID."""
    item = ParameterSearchItem(name="Temperature")

    assert item.id is None
    assert item.name == "Temperature"
