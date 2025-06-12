from enum import Enum

from pydantic import Field

from albert.resources.base import BaseAlbertModel, BaseResource, EntityLink
from albert.resources.identifiers import CustomFieldId, EntityTypeId, RuleId


class EntityCategory(str, Enum):
    PROPERTY = "Property"
    BATCH = "Batch"
    GENERAL = "General"


class EntityServiceType(str, Enum):
    TASKS = "tasks"


class EntityType(str, Enum):
    CUSTOM = "custom"
    SYSTEM = "system"


class FieldSection(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"


class EntityCustomFields(BaseAlbertModel):
    id: CustomFieldId
    section: FieldSection
    hidden: bool
    default: str | float | EntityLink | None = None


class EntityTypeStandardFieldVisibility(BaseAlbertModel):
    notes: bool = Field(alias="Notes")
    tags: bool = Field(alias="Tags")
    due_date: bool = Field(alias="DueDate")


class EntityTypeSearchQueryStrings(BaseAlbertModel):
    DAT: str | None = None
    PRG: str | None = None


class EntityType(BaseResource):
    id: EntityTypeId = Field(alias="albertId")
    category: EntityCategory
    custom_category: str = Field(max_length=100, min_length=1, alias="customCategory")
    label: str
    service: EntityServiceType
    type: EntityType = Field(default=EntityType.CUSTOM)
    prefix: str = Field(max_length=3)
    standard_field_visibility: EntityTypeStandardFieldVisibility = Field(
        alias="standardFieldVisibility"
    )
    template_based: bool | None = Field(alias="templateBased", default=None)
    locked_template: bool | None = Field(alias="lockedTemplate", default=None)


class EntityTypeOptionType(str, Enum):
    STRING = "string"
    LIST = "list"


class EntityTypeFieldOptions(BaseAlbertModel):
    option_type: EntityTypeOptionType = Field(alias="optionType")
    values: list[str | EntityLink] | None = None


class EntityTypeRuleAction(BaseAlbertModel):
    target_field: str
    hidden: bool | None = None
    required: bool | None = None
    default: str | float | EntityLink | None = None
    options: EntityTypeFieldOptions | None = None


class EntityTypeRuleTriggerCase(BaseAlbertModel):
    value: str
    actions: list[EntityTypeRuleAction]


class EntityTypeRuleTrigger(BaseAlbertModel):
    cases: list[EntityTypeRuleTriggerCase]


class EntityTypeRule(BaseResource):
    id: RuleId = Field(alias="albertId")
    custom_field_id: CustomFieldId = Field(alias="customFieldId")
    trigger: EntityTypeRuleTrigger = Field(alias="trigger")
