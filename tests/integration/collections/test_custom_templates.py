import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import NotFoundError
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.custom_templates import (
    CustomTemplate,
    CustomTemplateSearchItem,
    CustomTemplateSearchItemData,
    GeneralData,
    TemplateCategory,
    _CustomTemplateDataUnion,
)
from albert.resources.tags import Tag
from albert.resources.users import User
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("customtemplates")


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
    results = poll_until(
        lambda: [
            t
            for t in client.custom_templates.get_all(
                name=seeded_template.name, category=seeded_template.category
            )
            if t.id == seeded_template.id
        ]
    )
    if not results:
        pytest.skip("Custom template list index did not return the seeded template")
    assert_template_items(
        list_iterator=results,
        expected_type=CustomTemplate,
        expected_data_type=_CustomTemplateDataUnion,
    )
    assert len(results)


def test_custom_template_search(client: Albert, seeded_custom_templates: list[CustomTemplate]):
    """Test search returns unhydrated CustomTemplateSearchItem results."""
    seeded_template = seeded_custom_templates[0]
    results = list(client.custom_templates.search(text=seeded_template.name))
    assert_template_items(
        list_iterator=results,
        expected_type=CustomTemplateSearchItem,
        expected_data_type=CustomTemplateSearchItemData,
    )
    assert len(results)


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


def test_custom_template_create_resolves_and_deduplicates_tags(client: Albert, seed_prefix: str):
    """Test creating a task template resolves new tags and stores each tag once."""
    existing_tag = client.tags.create(tag=Tag(tag=f"TEST - {uuid.uuid4()}"))
    top_tag_name = f"TEST - {uuid.uuid4()}"
    data_tag_name = f"TEST - {uuid.uuid4()}"
    created: list[CustomTemplate] = []
    try:
        created = client.custom_templates.create(
            custom_template=CustomTemplate(
                name=f"{seed_prefix}-tags",
                category=TemplateCategory.GENERAL,
                tags=[existing_tag, existing_tag, Tag(tag=top_tag_name)],
                data=GeneralData(
                    name=f"{seed_prefix}-tags",
                    tags=[existing_tag, Tag(tag=data_tag_name), Tag(tag=data_tag_name)],
                ),
            )
        )
        template = created[0]

        top_ids = [t.id for t in template.tags or []]
        assert len(top_ids) == 2
        assert len(set(top_ids)) == 2
        assert existing_tag.id in top_ids

        data_ids = [t.id for t in template.data.tags or []]
        assert len(data_ids) == 2
        assert len(set(data_ids)) == 2
        assert existing_tag.id in data_ids
    finally:
        for template in created:
            with suppress(NotFoundError):
                client.custom_templates.delete(id=template.id)
        auto_created_ids = set()
        for template in created:
            template_tags = list(template.tags or [])
            if template.data is not None:
                template_tags += template.data.tags or []
            auto_created_ids |= {t.id for t in template_tags if t.id != existing_tag.id}
        for tag_id in auto_created_ids | {existing_tag.id}:
            with suppress(NotFoundError):
                client.tags.delete(id=tag_id)


def test_hydrate_custom_template(
    client: Albert,
    seed_prefix: str,
    seeded_custom_templates: list[CustomTemplate],
):
    """Test hydrate on search hits scoped to the seeded custom template ids."""
    seeded_ids = {t.id for t in seeded_custom_templates}
    custom_templates = poll_until(
        lambda: [
            t
            for t in client.custom_templates.search(text=seed_prefix, max_items=100)
            if t.id in seeded_ids
        ]
    )
    assert custom_templates, "Expected at least one custom_template in search results"

    for custom_template in custom_templates:
        hydrated = custom_template.hydrate()

        # identity checks
        assert hydrated.id == custom_template.id
        assert hydrated.name == custom_template.name
