"""Unit tests for the pure tag-folding helper on CustomTemplatesCollection."""

from albert.collections.custom_templates import CustomTemplatesCollection
from albert.resources.custom_templates import CustomTemplate, GeneralData
from albert.resources.tags import Tag


def _template(**kwargs) -> CustomTemplate:
    defaults = {"name": "tpl"}
    defaults.update(kwargs)
    return CustomTemplate(**defaults)


def test_fold_tags_into_data_appends_top_level_after_data_tags() -> None:
    """Test that top-level tags are appended after existing data tags."""
    template = _template(
        tags=[Tag(id="TAG1", tag="alpha")],
        data=GeneralData(name="tpl", tags=[Tag(id="TAG2", tag="beta")]),
    )

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.data.tags] == ["TAG2", "TAG1"]


def test_fold_tags_into_data_sets_data_tags_when_only_top_level() -> None:
    """Test that top-level tags move into a data section that has none."""
    template = _template(tags=[Tag(id="TAG1", tag="alpha")], data=GeneralData(name="tpl"))

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.data.tags] == ["TAG1"]


def test_fold_tags_into_data_noops_without_top_level_tags() -> None:
    """Test that data tags are untouched when no top-level tags are set."""
    template = _template(data=GeneralData(name="tpl", tags=[Tag(id="TAG2", tag="beta")]))

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.data.tags] == ["TAG2"]


def test_fold_tags_into_data_noops_without_data_section() -> None:
    """Test that a template without a data section keeps its top-level tags."""
    template = _template(tags=[Tag(id="TAG1", tag="alpha")])

    CustomTemplatesCollection._fold_tags_into_data(template=template)

    assert [t.id for t in template.tags] == ["TAG1"]
