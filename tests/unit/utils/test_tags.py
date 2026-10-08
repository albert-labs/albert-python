"""Unit tests for the pure tag-deduplication helper in ``albert.utils.tags``.

``resolve_tags`` wraps ``TagCollection.get_or_create`` (network I/O) and is covered by
integration tests instead; see ``tests/integration/collections/test_inventory.py``.
"""

from albert.resources.tags import Tag
from albert.utils.tags import unique_tags


def test_unique_tags_dedupes_by_id():
    """Test that tags sharing an ID collapse to a single entry."""
    tags = [Tag(id="TAG1", tag="alpha"), Tag(id="TAG1", tag="alpha"), Tag(id="TAG2", tag="beta")]

    assert unique_tags(tags) == [Tag(id="TAG1", tag="alpha"), Tag(id="TAG2", tag="beta")]


def test_unique_tags_dedupes_by_casefolded_name_when_id_is_unset():
    """Test that name-only tags are matched case-insensitively."""
    tags = [Tag(tag="Resin"), Tag(tag="resin"), Tag(tag="RESIN"), Tag(tag="Epoxy")]

    assert unique_tags(tags) == [Tag(tag="Resin"), Tag(tag="Epoxy")]


def test_unique_tags_preserves_first_seen_order():
    """Test that the first occurrence's spelling and position win."""
    tags = [Tag(tag="b"), Tag(tag="a"), Tag(tag="b"), Tag(tag="c")]

    assert [t.tag for t in unique_tags(tags)] == ["b", "a", "c"]


def test_unique_tags_id_and_name_only_tags_are_independent():
    """Test that an ID-bearing tag and a differently-named unsaved tag both survive."""
    tags = [Tag(id="TAG1", tag="alpha"), Tag(tag="alpha")]

    assert unique_tags(tags) == [Tag(id="TAG1", tag="alpha"), Tag(tag="alpha")]


def test_unique_tags_empty_list():
    """Test that an empty input returns an empty list."""
    assert unique_tags([]) == []
