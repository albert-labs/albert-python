import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import NotFoundError
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.custom_templates import (
    Block,
    CustomTemplate,
    CustomTemplateSearchItem,
    CustomTemplateSearchItemData,
    GeneralData,
    Priority,
    PropertyData,
    TemplateCategory,
    Workflow,
    WorkflowCombination,
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


def _combination_grid() -> list[WorkflowCombination]:
    """Build a 2 x 3 interval-combination grid, all cells enabled."""
    return [
        WorkflowCombination(
            index=index,
            interval_params=f"INT{value1}XINT{value2}",
            heading="Temperature",
            val=str(value1),
            unit_name="C",
            heading2="Stir Rate",
            val2=str(value2),
            unit_name2="RPM",
            is_checked=True,
        )
        for index, (value1, value2) in enumerate([(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)])
    ]


def test_custom_template_update_workflow_combination(client: Albert, seed_prefix: str):
    """Test creating and updating a Property template's workflow combination grid."""
    workflow_hits = list(client.workflows.search(max_items=1))
    if not workflow_hits:
        pytest.skip("No workflows available to reference from a template")
    name = f"{seed_prefix}-combinations"
    created: list[CustomTemplate] = []
    try:
        created = client.custom_templates.create(
            custom_template=CustomTemplate(
                name=name,
                category=TemplateCategory.PROPERTY,
                data=PropertyData(
                    name=name,
                    priority=Priority.LOW,
                    blocks=[
                        Block(
                            workflow=[
                                Workflow(
                                    id=workflow_hits[0].id,
                                    combination=_combination_grid(),
                                )
                            ]
                        )
                    ],
                ),
            )
        )
        fetched = client.custom_templates.get_by_id(id=created[0].id)
        assert isinstance(fetched.data, PropertyData)
        grid = fetched.data.blocks[0].workflow[0].combination
        assert grid is not None
        assert [cell.is_checked for cell in grid] == [True] * 6

        fetched.data.blocks[0].workflow[0].combination[2].is_checked = False
        updated = client.custom_templates.update(custom_template=fetched)
        assert isinstance(updated.data, PropertyData)
        grid = updated.data.blocks[0].workflow[0].combination
        assert grid is not None
        assert [cell.is_checked for cell in grid] == [
            True,
            True,
            False,
            True,
            True,
            True,
        ]
    finally:
        for template in created:
            with suppress(NotFoundError):
                client.custom_templates.delete(id=template.id)


def test_custom_template_update_name_and_locked(
    client: Albert,
    seeded_custom_templates: list[CustomTemplate],
):
    """Test updating a template's name and locked flag."""
    seeded_template = seeded_custom_templates[0]
    fetched = client.custom_templates.get_by_id(id=seeded_template.id)
    new_name = f"{fetched.name}-updated"

    fetched.name = new_name
    fetched.locked = True
    updated = client.custom_templates.update(custom_template=fetched)

    assert updated.name == new_name
    assert updated.locked is True


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

        data_ids = [t.id for t in template.data.tags or []]
        assert len(data_ids) == 3
        assert len(set(data_ids)) == 3
        assert existing_tag.id in data_ids

        # Top-level tags fold into the data section on create and surface on read.
        top_ids = [t.id for t in template.tags or []]
        assert set(top_ids) == set(data_ids)
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
