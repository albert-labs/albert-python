import uuid

import pytest

from albert.client import Albert
from albert.core.shared.enums import OrderBy
from albert.exceptions import AlbertException
from albert.resources.tags import Tag


def assert_valid_tag_items(returned_list: list[Tag], limit=100):
    """Assert that returned items are valid Tag objects."""
    assert returned_list, "Expected at least one Tag result"
    for u in returned_list[:limit]:
        assert isinstance(u, Tag)
        assert isinstance(u.tag, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("TAG")


def test_tag_get_all_with_pagination(client: Albert):
    """Test Tag get_all paginates with max_items."""
    results = list(client.tags.get_all(max_items=10))
    assert len(results) <= 10
    assert_valid_tag_items(results)


def test_tag_get_all_with_filters(client: Albert, seeded_tags: list[Tag]):
    """Test Tag get_all with name filter and exact match."""
    name = seeded_tags[0].tag
    results = list(
        client.tags.get_all(name=name, exact_match=True, order_by=OrderBy.ASCENDING, max_items=10)
    )
    assert_valid_tag_items(results)


def test_tag_get_all_no_match(client: Albert):
    """Test Tag get_all returns no results on nonsense name."""
    no_match = list(
        client.tags.get_all(
            name="chaos tags 126485% HELLO WORLD!!!!",
            exact_match=True,
            order_by=OrderBy.ASCENDING,
            max_items=5,
        )
    )
    assert no_match == []


def test_get_tag_by(client: Albert, seeded_tags: list[Tag]):
    tag_test_str = seeded_tags[2].tag

    tag = client.tags.get_by_name(name=tag_test_str, exact_match=True)

    assert isinstance(tag, Tag)
    assert tag.tag.lower() == tag_test_str.lower()

    by_id = client.tags.get_by_id(id=tag.id)
    assert isinstance(by_id, Tag)
    assert by_id.tag.lower() == tag_test_str.lower()


def test_tag_exists(client: Albert, seeded_tags: list[Tag]):
    assert client.tags.exists(tag=seeded_tags[1].tag)
    assert not client.tags.exists(
        tag="Nonesense tag no one would ever make!893y58932y58923", exact_match=True
    )


def test_tag_update(client: Albert, seeded_tags: list[Tag]):
    test_tag = seeded_tags[3]
    new_name = f"TEST - {uuid.uuid4()}"

    assert test_tag.id is not None

    updated_tag = client.tags.rename(old_name=test_tag.tag, new_name=new_name)
    assert isinstance(updated_tag, Tag)
    assert test_tag.id == updated_tag.id
    assert updated_tag.tag == new_name

    with pytest.raises(AlbertException):
        client.tags.rename(
            old_name="y74r79ub4v9f874ebf982bTEST NONESENSEg89befbnr", new_name="Foo Bar!"
        )


def test_get_or_create_tags(caplog, client: Albert, seeded_tags: list[Tag]):
    existing = client.tags.get_or_create(
        tag=seeded_tags[0].tag
    )  # passing the string directly to test that logic

    assert f"Tag {existing.tag} already exists with id {existing.id}" in caplog.text
    assert existing.id == seeded_tags[0].id


def test_create_tag(client: Albert):
    """Test creating a new tag."""
    new_tag_name = f"TEST_TAG_{uuid.uuid4()}"
    new_tag = client.tags.create(tag=new_tag_name)

    assert isinstance(new_tag, Tag)
    assert new_tag.tag == new_tag_name
    assert new_tag.id.startswith("TAG")
