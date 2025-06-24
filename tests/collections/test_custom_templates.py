from collections.abc import Iterator
from itertools import islice

from albert.client import Albert
from albert.resources.custom_templates import (
    CustomTemplate,
    CustomTemplateSearchItem,
    CustomTemplateSearchItemData,
    _CustomTemplateDataUnion,
)


def assert_template_items(
    list_iterator: Iterator[CustomTemplate | CustomTemplateSearchItem],
    *,
    expected_type: type,
    expected_data_type: type,
):
    """Assert all items and their data are of expected types."""
    assert isinstance(list_iterator, Iterator), "Expected an Iterator"

    found = False
    for i, item in enumerate(list_iterator):
        if i == 50:
            break

        assert isinstance(item, expected_type), (
            f"Expected {expected_type.__name__}, got {type(item).__name__}"
        )
        found = True

        if expected_data_type and getattr(item, "data", None) is not None:
            assert isinstance(item.data, expected_data_type), (
                f"Expected {expected_data_type.__name__}, got {type(item.data).__name__}"
            )

    assert found, f"No {expected_type.__name__} items found in iterator"


def test_get_all(client: Albert):
    """Test get_all returns hydrated CustomTemplate items."""
    list_response = client.custom_templates.get_all()
    assert_template_items(
        list_iterator=list_response,
        expected_type=CustomTemplate,
        expected_data_type=_CustomTemplateDataUnion,
    )


def test_search(client: Albert):
    """Test search returns unhydrated CustomTemplateSearchItem results."""
    search_response = client.custom_templates.search()
    assert_template_items(
        list_iterator=search_response,
        expected_type=CustomTemplateSearchItem,
        expected_data_type=CustomTemplateSearchItemData,
    )


def test_hydrate_custom_template(client: Albert):
    custom_templates = list(islice(client.custom_templates.search(), 5))
    assert custom_templates, "Expected at least one custom_template in search results"

    for custom_template in custom_templates:
        hydrated = custom_template.hydrate()

        # identity checks
        assert hydrated.id == custom_template.id
        assert hydrated.name == custom_template.name
