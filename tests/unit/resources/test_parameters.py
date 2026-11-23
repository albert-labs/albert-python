from albert.resources.parameters import ParameterSearchItem


def test_parameter_search_item_accepts_lowercase_metadata():
    """Test that search results accept lower-case metadata."""
    item = ParameterSearchItem.model_validate({"metadata": {"batchCode": "B-100"}})

    assert item.metadata == {"batchCode": "B-100"}


def test_parameter_search_item_preserves_unmodeled_selected_fields():
    """Test that explicitly selected fields remain accessible on search results."""
    item = ParameterSearchItem.model_validate({"name": "Temperature", "customField": "value"})

    assert item.model_extra == {"customField": "value"}
