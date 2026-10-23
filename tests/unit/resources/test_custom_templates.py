import pytest
from pydantic import ValidationError

from albert.resources.custom_templates import (
    CustomTemplate,
    GeneralData,
    PropertyData,
    TemplateCategory,
)


def test_custom_template_backfills_category_into_nested_data():
    """Test that a missing 'category' on nested Data is filled from the template's top-level category."""
    template = CustomTemplate.model_validate(
        {
            "name": "Standard Property Task",
            "category": "Property",
            "Data": {"name": "some task", "priority": "Low"},
        }
    )
    assert isinstance(template.data, PropertyData)
    assert template.data.category is TemplateCategory.PROPERTY


def test_custom_template_does_not_override_explicit_nested_category():
    """Test that an explicit category on nested Data is left untouched."""
    template = CustomTemplate.model_validate(
        {
            "name": "General template",
            "category": "Property",
            "Data": {"category": "General", "name": "some task"},
        }
    )
    assert isinstance(template.data, GeneralData)
    assert template.data.category is TemplateCategory.GENERAL


def test_custom_template_without_nested_data_is_unaffected():
    """Test that constructing without a 'Data' payload does not raise."""
    template = CustomTemplate(name="No data template", category=TemplateCategory.GENERAL)
    assert template.data is None


def test_custom_template_non_dict_data_payload_raises():
    """Test that a non-dict 'Data' value is left for normal field validation to reject."""
    with pytest.raises(ValidationError):
        CustomTemplate.model_validate(
            {
                "name": "raw",
                "category": "General",
                "Data": "not-a-dict",
            }
        )


def test_custom_template_non_dict_top_level_payload_raises():
    """Test that a non-dict top-level payload skips category backfill and fails validation."""
    with pytest.raises(ValidationError):
        CustomTemplate.model_validate("not-a-dict")


def test_custom_template_revalidating_an_instance_is_a_no_op():
    """Test that model_validate on an existing CustomTemplate instance does not re-run the dict-only backfill."""
    template = CustomTemplate(name="No data template", category=TemplateCategory.GENERAL)
    revalidated = CustomTemplate.model_validate(template)
    assert revalidated.data is None
    assert revalidated.name == "No data template"
