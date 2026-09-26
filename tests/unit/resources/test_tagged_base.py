import logging

import pytest
from pydantic import ValidationError

from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.tags import Tag


def test_convert_tags_ignores_non_dict_input():
    """Test the tag conversion validator leaves non-dict input for downstream validation to reject."""
    with pytest.raises(ValidationError):
        BaseTaggedResource.model_validate(["not", "a", "dict"])


def test_convert_tags_defaults_to_none_when_absent():
    """Test tags default to None when the caller supplies none."""
    resource = BaseTaggedResource()
    assert resource.tags is None


def test_convert_tags_from_field_name_key_with_string_tags():
    """Test tags supplied by field name as bare strings are converted via Tag.from_string."""
    resource = BaseTaggedResource(tags=["urgent"])
    assert len(resource.tags) == 1
    assert isinstance(resource.tags[0], Tag)
    assert resource.tags[0].tag == "urgent"


def test_convert_tags_falls_back_to_alias_key():
    """Test tags are read from the 'Tags' alias key when 'tags' is absent."""
    resource = BaseTaggedResource.model_validate({"Tags": ["urgent"]})
    assert resource.tags[0].tag == "urgent"


@pytest.mark.parametrize("nested_key", ["tags", "Tags"])
def test_convert_tags_falls_back_to_nested_data_key(nested_key):
    """Test tags are read from a nested 'Data' envelope when absent at the top level."""
    resource = BaseTaggedResource.model_validate({"Data": {nested_key: ["urgent"]}})
    assert resource.tags[0].tag == "urgent"


def test_convert_tags_preserves_existing_tag_instances():
    """Test an already-constructed Tag instance is kept as-is."""
    tag = Tag(tag="existing", id="TAG1")
    resource = BaseTaggedResource(tags=[tag])
    assert resource.tags[0] is tag


def test_convert_tags_dict_requires_name_alongside_id():
    """Test a dict tag reference with only an id and no name is rejected."""
    with pytest.raises(ValidationError, match="require the tag's name alongside its id"):
        BaseTaggedResource(tags=[{"id": "TAG1"}])


@pytest.mark.parametrize("name_key", ["name", "tagName", "tag"])
def test_convert_tags_dict_with_name_key_builds_tag(name_key):
    """Test a dict tag reference with any accepted name key is accepted."""
    resource = BaseTaggedResource(tags=[{"id": "TAG1", name_key: "Priority"}])
    assert resource.tags[0].id == "TAG1"
    assert resource.tags[0].tag == "Priority"


def test_convert_tags_logs_and_skips_unexpected_type(caplog):
    """Test an unexpected tag element type is skipped with a warning instead of raising."""
    with caplog.at_level(logging.WARNING):
        resource = BaseTaggedResource(tags=[123])
    assert resource.tags == []
    assert "Unexpected value for Tag" in caplog.text


def test_convert_tags_empty_list_is_left_untouched():
    """Test an explicitly empty tags list bypasses conversion and stays empty."""
    resource = BaseTaggedResource(tags=[])
    assert resource.tags == []
