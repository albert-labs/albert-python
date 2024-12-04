import uuid

import pytest

from albert.albert import Albert
from albert.collections.base import OrderBy
from albert.exceptions import AlbertException
from albert.resources.tags import Tag


def _list_asserts(returned_list, limit=100):
    found = False
    for i, u in enumerate(returned_list):
        found = True
        # just check the first 100
        if i == limit:
            break

        assert isinstance(u, Tag)
        assert isinstance(u.tag, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("TAG")
    assert found


def test_simple_tags_list(client: Albert):
    simple_list = client.tags.list()
    simple_list = list(simple_list)
    _list_asserts(simple_list)


def test_advanced_tags_list(client: Albert, seeded_tags: list[Tag]):
    name = seeded_tags[0].tag
    adv_list = client.tags.list(
        name=name,
        exact_match=True,
        order_by=OrderBy.ASCENDING,
    )
    adv_list = list(adv_list)
    _list_asserts(adv_list)

    adv_list_no_match = client.tags.list(
        name="chaos tags 126485% HELLO WORLD!!!!",
        exact_match=True,
        order_by=OrderBy.ASCENDING,
    )
    assert next(adv_list_no_match, None) == None

    tag_short_list = client.tags.list(limit=3)
    _list_asserts(tag_short_list, limit=5)


def test_get_tag_by(client: Albert, seeded_tags: list[Tag]):
    tag_test_str = seeded_tags[2].tag

    tag = client.tags.get_by_tag(tag=tag_test_str, exact_match=True)

    assert isinstance(tag, Tag)
    assert tag.tag.lower() == tag_test_str.lower()

    by_id = client.tags.get_by_id(id=tag.id)
    assert isinstance(by_id, Tag)
    assert by_id.tag.lower() == tag_test_str.lower()


def test_tag_exists(client: Albert, seeded_tags: list[Tag]):
    assert client.tags.tag_exists(tag=seeded_tags[1].tag)
    assert not client.tags.tag_exists(
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


def test_returns_existing(caplog, client: Albert, seeded_tags: list[Tag]):
    created_tag = client.tags.create(
        tag=seeded_tags[0].tag
    )  # passing the string directly to test that logic

    # assert it returns the existing
    re_created = client.tags.create(tag=created_tag)
    assert f"Tag {re_created.tag} already exists with id {re_created.id}" in caplog.text
    assert re_created.id == seeded_tags[0].id
