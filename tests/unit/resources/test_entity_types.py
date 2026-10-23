import pytest
from pydantic import ValidationError

from albert.core.shared.models.base import EntityLink
from albert.resources.entity_types import (
    EntityCategory,
    EntityLinkOption,
    EntityServiceType,
    EntityType,
    EntityTypeFieldOptions,
    EntityTypeOptionType,
    EntityTypeRuleAction,
)


@pytest.mark.parametrize("service", [EntityServiceType.TASKS, EntityServiceType.INVENTORIES])
def test_entity_type_requires_category_for_tasks_and_inventories(service):
    """Test that tasks and inventories entity types must set a category."""
    with pytest.raises(ValidationError, match="category is required"):
        EntityType(label="Stability Task", service=service)


@pytest.mark.parametrize(
    "service",
    [
        EntityServiceType.PARAMETER_GROUPS,
        EntityServiceType.DATA_TEMPLATES,
        EntityServiceType.PROJECTS,
        EntityServiceType.LOTS,
    ],
)
def test_entity_type_does_not_require_category_for_other_services(service):
    """Test that non-tasks/inventories services do not require a category."""
    entity_type = EntityType(label="Some Type", service=service)
    assert entity_type.category is None


def test_entity_type_accepts_category_for_tasks():
    """Test that a tasks entity type with a category passes validation."""
    entity_type = EntityType(
        label="Stability Task",
        service=EntityServiceType.TASKS,
        category=EntityCategory.PROPERTY,
    )
    assert entity_type.category is EntityCategory.PROPERTY


def test_entity_type_field_options_converts_entity_links_to_options():
    """Test that EntityTypeFieldOptions converts bare EntityLink values to EntityLinkOption."""
    options = EntityTypeFieldOptions(
        type=EntityTypeOptionType.LIST_CUSTOM,
        values=[EntityLink(id="LST1", name="Option A"), "plain-string"],
    )
    assert options.values[0] == EntityLinkOption(id="LST1", name="Option A")
    assert options.values[1] == "plain-string"


def test_entity_type_rule_action_converts_default_entity_link_to_option():
    """Test that EntityTypeRuleAction converts a bare EntityLink default to EntityLinkOption."""
    action = EntityTypeRuleAction(
        target_field="status", default=EntityLink(id="LST1", name="Option A")
    )
    assert action.default == EntityLinkOption(id="LST1", name="Option A")


def test_entity_type_rule_action_leaves_non_link_default_untouched():
    """Test that EntityTypeRuleAction leaves a scalar default value unmodified."""
    action = EntityTypeRuleAction(target_field="status", default="Active")
    assert action.default == "Active"


def test_entity_type_field_options_without_values_skips_conversion():
    """Test that EntityTypeFieldOptions omitting 'values' does not attempt any conversion."""
    options = EntityTypeFieldOptions(type=EntityTypeOptionType.STRING)
    assert options.values is None
