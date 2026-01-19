from albert.client import Albert
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.custom_templates import (
    CustomTemplate,
    CustomTemplateSearchItem,
    CustomTemplateSearchItemData,
    _CustomTemplateDataUnion,
)
from albert.resources.users import User


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


def test_custom_template_get_all(client: Albert, seeded_custom_templates: list[CustomTemplate]):
    """Test get_all returns hydrated CustomTemplate items."""
    seeded_template = seeded_custom_templates[0]
    results = list(client.custom_templates.get_all(name=seeded_template.name, max_items=10))
    assert_template_items(
        list_iterator=results,
        expected_type=CustomTemplate,
        expected_data_type=_CustomTemplateDataUnion,
    )
    assert len(results) <= 10
    assert any(result.id == seeded_template.id for result in results)


def test_custom_template_search(client: Albert, seeded_custom_templates: list[CustomTemplate]):
    """Test search returns unhydrated CustomTemplateSearchItem results."""
    seeded_template = seeded_custom_templates[0]
    results = list(client.custom_templates.search(text=seeded_template.name, max_items=10))
    assert_template_items(
        list_iterator=results,
        expected_type=CustomTemplateSearchItem,
        expected_data_type=CustomTemplateSearchItemData,
    )
    assert len(results) <= 10
    assert any(result.id == seeded_template.id for result in results)


def test_custom_template_get_by_id(client: Albert, seeded_custom_templates: list[CustomTemplate]):
    """Test get_by_id returns a hydrated CustomTemplate."""
    seeded_template = seeded_custom_templates[0]
    fetched = client.custom_templates.get_by_id(id=seeded_template.id)
    assert fetched.id == seeded_template.id
    assert fetched.name == seeded_template.name


def test_custom_template_update_acl(
    client: Albert,
    seeded_custom_templates: list[CustomTemplate],
    static_user: User,
):
    """Test updating a custom template's ACL returns an updated template."""
    seeded_template = seeded_custom_templates[0]
    updated = client.custom_templates.update_acl(
        custom_template_id=seeded_template.id,
        acls=[ACL(id=static_user.id, fgc=AccessControlLevel.CUSTOM_TEMPLATE_OWNER)],
    )
    assert updated.id == seeded_template.id
    assert updated.name == seeded_template.name
    assert updated.acl is not None
    assert updated.acl.fgclist is not None
    assert any(entry.id == static_user.id for entry in updated.acl.fgclist)


def test_hydrate_custom_template(client: Albert, seeded_custom_templates: list[CustomTemplate]):
    seeded_template = seeded_custom_templates[0]
    custom_templates = list(client.custom_templates.search(text=seeded_template.name, max_items=5))
    assert custom_templates, "Expected at least one custom_template in search results"

    for custom_template in custom_templates:
        hydrated = custom_template.hydrate()

        # identity checks
        assert hydrated.id == custom_template.id
        assert hydrated.name == custom_template.name
