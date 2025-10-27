from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.shared.identifiers import CustomFieldId, EntityTypeId, RuleId
from albert.core.shared.models.base import BaseAlbertModel, BaseResource, EntityLink


class EntityCategory(str, Enum):
    """Categories that an entity type should be based on.
    Attributes
    ----------
    PROPERTY : str
        Property category.
    BATCH : str
        Batch category.
    GENERAL : str
        General category.
    """

    PROPERTY = "Property"
    BATCH = "Batch"
    GENERAL = "General"


class EntityServiceType(str, Enum):
    """Types of services that an entity type can be associated with.
    Attributes
    ----------
    TASKS : str
        Tasks service type.
    """

    TASKS = "tasks"


class EntityTypeType(str, Enum):
    """Types of entity types. Used to determine if an entity type is custom or system.
    Attributes
    ----------
    CUSTOM : str
        Custom entity type.
    SYSTEM : str
        System entity type.
    """

    CUSTOM = "custom"
    SYSTEM = "system"


class FieldSection(str, Enum):
    """Sections where a field can be displayed in the UI. Only Fields in the top section can be used in EntityTypeSearchQueryStrings.
    Attributes
    ----------
    TOP : str
        Top section of the form.
    BOTTOM : str
        Bottom section of the form.
    """

    TOP = "top"
    BOTTOM = "bottom"


class EntityCustomField(BaseAlbertModel):
    """Custom fields associated with an entity type.
    Attributes
    ----------
    id : CustomFieldId
        The ID of the custom field.
    section : FieldSection
        The section where the field should be displayed (i.e., top or bottom).
    hidden : bool
        Whether the field should be hidden.
    default : str | float | EntityLink | None, optional
        The default value for the field.
    """

    id: CustomFieldId
    section: FieldSection
    hidden: bool
    default: str | float | EntityLink | None = None
    required: bool | None = None


class EntityTypeStandardFieldVisibility(BaseAlbertModel):
    """Visibility settings for standard fields in an entity type.
    Attributes
    ----------
    notes : bool
        Whether the notes field should be visible.
    tags : bool
        Whether the tags field should be visible.
    due_date : bool
        Whether the due date field should be visible.
    """

    notes: bool = Field(alias="Notes")
    tags: bool = Field(alias="Tags")
    due_date: bool = Field(alias="DueDate")


class EntityTypeSearchQueryStrings(BaseAlbertModel):
    """Search query strings for different entity type views.
    These strings define how to construct search queries for different selectable entities within the entity type. They can include placeholders for custom fields that
    will be replaced with actual values.
    Attributes
    ----------
    DAT : str | None, optional
        Search query string for the data view.
    PRG : str | None, optional
        Search query string for the program view.
    Examples
    --------
    ```python
    # In this example, the name of the custom fields are the same on the Task and the Data Templates + Parameter Groups.
    search_strings = EntityTypeSearchQueryStrings(
        DAT="customField1={customField1}&customField2={customField2}",
        PRG="customField1={customField1}&customField2={customField2}"
    )
    ```
    """

    DAT: str | None = None
    PRG: str | None = None


class EntityType(BaseResource):
    """An entity type in the Albert system.
    Entity types define the structure and behavior of entities in the system.
    They can be custom or system types, and can have associated custom fields
    and rules.
    Attributes
    ----------
    id : EntityTypeId
        The unique identifier for the entity type.
    category : EntityCategory
        The category the entity type belongs to.
    custom_category : str
        A custom category name for the entity type.
    label : str
        The display label for the entity type.
    service : EntityServiceType
        The service type associated with this entity type.
    type : EntityTypeType
        The type of entity type (custom or system).
    prefix : str
        The prefix used for IDs of this entity type.
    standard_field_visibility : EntityTypeStandardFieldVisibility
        Visibility settings for standard fields.
    template_based : bool | None, optional
        Whether this entity type is template-based. If True, users can only instantiate this entity type from a template.
    locked_template : bool | None, optional
        Whether the template is locked. If True, users cannot edit the template.
    """

    id: EntityTypeId | None = Field(alias="albertId", default=None)
    category: EntityCategory
    custom_category: str = Field(max_length=100, min_length=1, alias="customCategory")
    label: str
    service: EntityServiceType
    type: EntityTypeType = Field(default=EntityTypeType.CUSTOM)
    prefix: str = Field(max_length=3)
    custom_fields: list[EntityCustomField] | None = Field(default=None, alias="customFields")
    standard_field_visibility: EntityTypeStandardFieldVisibility | None = Field(
        alias="standardFieldVisibility", default=None
    )
    template_based: bool | None = Field(alias="templateBased", default=None)
    locked_template: bool | None = Field(alias="lockedTemplate", default=None)
    search_query_string: EntityTypeSearchQueryStrings | None = Field(
        alias="searchQueryString", default=None
    )


class EntityTypeOptionType(str, Enum):
    """Types of options that can be used in entity type fields.
    Attributes
    ----------
    STRING : str
        String option type.
    LIST : str
        List option type.
    """

    STRING = "string"
    LIST = "list"


class EntityLinkOption(EntityLink):
    """Allowed options for Field Options expect a different (de)serilization than the base EntityLink. This class handles that scenario."""

    id: str = Field(alias="albertId")
    name: str | None = Field(default=None, exclude=False)


class EntityTypeFieldOptions(BaseAlbertModel):
    """Options for a field in an entity type.
    Attributes
    ----------
    option_type : EntityTypeOptionType
        The type of option (string or list).
    values : list[str | EntityLink] | None, optional
        The possible values for this option.
    """

    option_type: EntityTypeOptionType = Field(alias="type")
    values: list[str | EntityLinkOption | EntityLink] | None = None

    # on init, if the values are EntityLink, convert them to EntityLinkOption
    def __init__(self, **data: Any):
        if "values" in data and isinstance(data["values"], list):
            data["values"] = [
                EntityLinkOption(id=v.id, name=v.name) if isinstance(v, EntityLink) else v
                for v in data["values"]
            ]
        super().__init__(**data)


class EntityTypeRuleAction(BaseAlbertModel):
    """An action that can be taken when a rule is triggered.
    Attributes
    ----------
    target_field : str
        The name of the field that this action affects.
    hidden : bool | None, optional
        Whether the field should be hidden.
    required : bool | None, optional
        Whether the field should be required.
    default : str | float | EntityLink | None, optional
        The default value for the field.
    options : EntityTypeFieldOptions | None, optional
        Available options for the field.
    """

    target_field_name: str = Field(alias="target_field")
    target_field_id: CustomFieldId | None = None
    hidden: bool | None = None
    required: bool | None = None
    default: str | float | EntityLinkOption | EntityLink | None = None
    options: EntityTypeFieldOptions | None = None

    # if an entity link is provided, convert it to an entity link option
    def __init__(self, **data: Any):
        if "default" in data and isinstance(data["default"], EntityLink):
            data["default"] = EntityLinkOption(id=data["default"].id, name=data["default"].name)
        super().__init__(**data)


class EntityTypeRuleTriggerCase(BaseAlbertModel):
    """A case in a rule that defines when actions should be taken.
    Attributes
    ----------
    value : str
        The value of the triggering field that triggers this case.
    actions : list[EntityTypeRuleAction]
        The actions to take when this case is triggered.
    """

    value: str
    actions: list[EntityTypeRuleAction]


class EntityTypeRuleTrigger(BaseAlbertModel):
    """A trigger that can activate rule cases.
    Attributes
    ----------
    cases : list[EntityTypeRuleTriggerCase]
        The cases that should be evaluated when this trigger is activated.
    """

    cases: list[EntityTypeRuleTriggerCase]


class EntityTypeRule(BaseResource):
    """A rule that defines conditional behavior for entity type fields.
    Attributes
    ----------
    id : RuleId
        The unique identifier for the rule.
    custom_field_id : CustomFieldId
        The ID of the custom field this rule listens to/ triggers on.
    trigger : EntityTypeRuleTrigger
        The triggers that activate this rule.
    """

    id: RuleId | None = Field(default=None)
    custom_field_id: CustomFieldId = Field(alias="customFieldId")
    trigger: EntityTypeRuleTrigger = Field(alias="trigger")
