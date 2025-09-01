from albert.client import Albert
from albert.resources.custom_templates import (
    CustomTemplate,
    CustomTemplateSearchItem,
    CustomTemplateSearchItemData,
    _CustomTemplateDataUnion,
)


def assert_template_items(
    list_iterator: list[CustomTemplate | CustomTemplateSearchItem],
    *,
    expected_type: type,
    expected_data_type: type,
):
    """Assert all items and their data are of expected types."""
    assert list_iterator, f"No {expected_type.__name__} items found in iterator"

    for item in list_iterator[:10]:
        assert isinstance(item, expected_type), (
            f"Expected {expected_type.__name__}, got {type(item).__name__}"
        )
        if expected_data_type and getattr(item, "data", None) is not None:
            assert isinstance(item.data, expected_data_type), (
                f"Expected {expected_data_type.__name__}, got {type(item.data).__name__}"
            )


def test_custom_template_get_all(client: Albert):
    """Test get_all returns hydrated CustomTemplate items."""
    results = list(client.custom_templates.get_all(max_items=10))
    assert_template_items(
        list_iterator=results,
        expected_type=CustomTemplate,
        expected_data_type=_CustomTemplateDataUnion,
    )
    assert len(results) <= 10


def test_custom_template_search(client: Albert):
    """Test search returns unhydrated CustomTemplateSearchItem results."""
    results = list(client.custom_templates.search(max_items=10))
    assert_template_items(
        list_iterator=results,
        expected_type=CustomTemplateSearchItem,
        expected_data_type=CustomTemplateSearchItemData,
    )
    assert len(results) <= 10


def test_hydrate_custom_template(client: Albert):
    custom_templates = list(client.custom_templates.search(max_items=5))
    assert custom_templates, "Expected at least one custom_template in search results"

    for custom_template in custom_templates:
        hydrated = custom_template.hydrate()

        # identity checks
        assert hydrated.id == custom_template.id
        assert hydrated.name == custom_template.name


def test_create_custom_template_from_seed(
    caplog,
    client: Albert,
    seed_prefix: str,
    seeded_custom_templates: list[CustomTemplate],
):
    """Test creating a new custom template."""
    seed = seeded_custom_templates[0]

    new_template = CustomTemplate(
        name=seed_prefix,
        category=seed.category,
        data=(
            seed.data.model_copy(update={"name": seed_prefix}, deep=True)
            if getattr(seed, "data", None) is not None
            else None
        ),
    )

    created = client.custom_templates.create(custom_template=new_template)

    assert isinstance(created, CustomTemplate)
    assert created.name == new_template.name
    assert created.category == new_template.category
    if new_template.data is not None and hasattr(new_template.data, "name"):
        assert getattr(created.data, "name", None) == new_template.data.name
