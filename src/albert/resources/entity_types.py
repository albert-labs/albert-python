from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from albert.core.shared.identifiers import CustomFieldId, EntityTypeId, RuleId
from albert.core.shared.models.base import BaseAlbertModel, BaseResource, EntityLink


class EntityCategory(str, Enum):
    """The category an entity type is based on.

    For task entity types this selects the kind of task (property, batch, or
    general); for inventory entity types it selects the inventory category the
    type applies to.

    Attributes
    ----------
    PROPERTY : str
        Property (measurement) task category.
    BATCH : str
        Batch (formulation) task category.
    GENERAL : str
        General task category.
    RAW_MATERIALS : str
        Raw materials inventory category.
    CONSUMABLES : str
        Consumables inventory category.
    EQUIPMENT : str
        Equipment inventory category.
    FORMULAS : str
        Formulas inventory category.
    """

    PROPERTY = "Property"
    BATCH = "Batch"
    GENERAL = "General"
    RAW_MATERIALS = "RawMaterials"
    CONSUMABLES = "Consumables"
    EQUIPMENT = "Equipment"
    FORMULAS = "Formulas"


class EntityServiceType(str, Enum):
    """The Albert service (entity family) an entity type applies to.

    Attributes
    ----------
    TASKS : str
        Entity type applies to Tasks.
    PARAMETER_GROUPS : str
        Entity type applies to Parameter Groups.
    DATA_TEMPLATES : str
        Entity type applies to Data Templates.
    PROJECTS : str
        Entity type applies to Projects.
    LOTS : str
        Entity type applies to Lots.
    INVENTORIES : str
        Entity type applies to Inventory Items.
    """

    TASKS = "tasks"
    PARAMETER_GROUPS = "parametergroups"
    DATA_TEMPLATES = "datatemplates"
    PROJECTS = "projects"
    LOTS = "lots"
    INVENTORIES = "inventories"


class EntityTypeType(str, Enum):
    """Whether an entity type is organization-defined or built in.

    Attributes
    ----------
    CUSTOM : str
        Defined by the organization to model its own categories of work.
    SYSTEM : str
        Ships with the Albert platform and is not user-created.
    """

    CUSTOM = "custom"
    SYSTEM = "system"


class FieldSection(str, Enum):
    """Where a field is displayed within an entity's form.

    Only fields placed in the top section can be referenced by an entity type's
    search query strings (see :class:`EntityTypeSearchQueryStrings`).

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
    """A custom field attached to an entity type.

    Links a defined :class:`~albert.resources.custom_fields.CustomField` to an
    entity type and describes how it appears on that entity's form (where it
    sits, whether it is hidden, its default value, and whether it is required).

    Attributes
    ----------
    id : CustomFieldId
        The ID of the linked custom field (format ``CTF...``).
    name : str or None
        Read-only name of the custom field.
    section : FieldSection
        Where the field is displayed on the form (top or bottom).
    hidden : bool
        Whether the field is hidden from the form.
    default : str or float or EntityLink or None
        The default value applied to the field, if any.
    required : bool or None
        Whether a value for the field is required.
    """

    id: CustomFieldId
    name: str | None = None
    section: FieldSection
    hidden: bool
    default: str | float | EntityLink | None = None
    required: bool | None = None


class EntityTypeStandardFieldVisibility(BaseAlbertModel):
    """Visibility settings for the built-in standard fields of an entity type.

    Controls whether the platform's standard Notes, Tags, and Due Date fields are
    shown on the entity's form.

    Attributes
    ----------
    notes : bool
        Whether the Notes field is visible.
    tags : bool
        Whether the Tags field is visible.
    due_date : bool
        Whether the Due Date field is visible.
    """

    notes: bool = Field(alias="Notes")
    tags: bool = Field(alias="Tags")
    due_date: bool = Field(alias="DueDate")


class EntityTypeStandardFieldRequired(BaseAlbertModel):
    """Required settings for the built-in standard fields of an entity type.

    Controls whether the platform's standard Notes, Tags, and Due Date fields
    must be filled in on the entity's form.

    Attributes
    ----------
    notes : bool
        Whether the Notes field is required.
    tags : bool
        Whether the Tags field is required.
    due_date : bool
        Whether the Due Date field is required.
    """

    notes: bool = Field(alias="Notes")
    tags: bool = Field(alias="Tags")
    due_date: bool = Field(alias="DueDate")


class EntityTypeSearchQueryStrings(BaseAlbertModel):
    """Search query strings used to find related entities within an entity type.

    These strings define how the platform builds a search query when selecting
    related Data Templates or Parameter Groups for the entity. They can include
    ``{customField}`` placeholders that are substituted with the actual values of
    the entity's custom fields.

    Attributes
    ----------
    DAT : str or None
        Query string used when selecting related Data Templates.
    PRG : str or None
        Query string used when selecting related Parameter Groups.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.entity_types import EntityTypeSearchQueryStrings
        # Here the custom field names match on the Task and on the
        # Data Templates + Parameter Groups.
        search_strings = EntityTypeSearchQueryStrings(
            DAT="customField1={customField1}&customField2={customField2}",
            PRG="customField1={customField1}&customField2={customField2}",
        )
        ```
    """

    DAT: str | None = None
    PRG: str | None = None


class EntityType(BaseResource):
    """A configurable entity type in the Albert platform.

    An entity type defines the structure and behavior of a particular kind of
    entity (a Task, Inventory Item, Project, Data Template, Parameter Group, or
    Lot): the custom category it falls under, which custom fields appear on it,
    how the standard Notes/Tags/Due Date fields behave, and how related-entity
    searches are built. Entity types can be built-in (``system``) or
    organization-defined (``custom``), and may carry conditional field rules (see
    :class:`EntityTypeRule`).

    Attributes
    ----------
    id : EntityTypeId or None
        The unique identifier for the entity type (format ``ETT...``). Assigned by
        Albert when the entity type is created.
    category : EntityCategory or None
        The category the entity type belongs to. Required for ``tasks`` and
        ``inventories`` services.
    custom_category : str or None
        A custom category name for the entity type.
    label : str
        The display label shown for the entity type.
    service : EntityServiceType
        The Albert service (entity family) this entity type applies to.
    type : EntityTypeType
        Whether the entity type is ``custom`` or ``system``. Defaults to
        ``custom``.
    prefix : str or None
        The short prefix used for the IDs of entities of this type.
    custom_fields : list[EntityCustomField] or None
        The custom fields configured on this entity type.
    standard_field_visibility : EntityTypeStandardFieldVisibility or None
        Which standard fields (Notes, Tags, Due Date) are visible.
    standard_field_required : EntityTypeStandardFieldRequired or None
        Which standard fields (Notes, Tags, Due Date) are required.
    template_based : bool or None
        Whether this entity type is template-based. If True, users can only
        instantiate it from a template.
    locked_template : bool or None
        Whether the template is locked. If True, users cannot edit the template.
    search_query_string : EntityTypeSearchQueryStrings or None
        Query strings used to find related Data Templates and Parameter Groups.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.entity_types import (
            EntityCategory,
            EntityServiceType,
            EntityType,
        )
        entity_type = EntityType(
            label="Stability Task",
            service=EntityServiceType.TASKS,
            category=EntityCategory.PROPERTY,
        )
        ```
    """

    id: EntityTypeId | None = Field(alias="albertId", default=None)
    category: EntityCategory | None = None
    custom_category: str | None = Field(
        default=None, max_length=100, min_length=1, alias="customCategory"
    )
    label: str
    service: EntityServiceType
    type: EntityTypeType = Field(default=EntityTypeType.CUSTOM)
    prefix: str | None = Field(default=None, max_length=3)
    custom_fields: list[EntityCustomField] | None = Field(default=None, alias="customFields")
    standard_field_visibility: EntityTypeStandardFieldVisibility | None = Field(
        alias="standardFieldVisibility", default=None
    )
    standard_field_required: EntityTypeStandardFieldRequired | None = Field(
        alias="standardFieldRequired", default=None
    )
    template_based: bool | None = Field(alias="templateBased", default=None)
    locked_template: bool | None = Field(alias="lockedTemplate", default=None)
    search_query_string: EntityTypeSearchQueryStrings | None = Field(
        alias="searchQueryString", default=None
    )

    @model_validator(mode="after")
    def validate_category(self) -> EntityType:
        if (
            self.service in {EntityServiceType.TASKS, EntityServiceType.INVENTORIES}
            and self.category is None
        ):
            raise ValueError("category is required for tasks and inventories entity types.")
        return self


class EntityTypeOptionType(str, Enum):
    """The kind of value a rule-driven field option holds.

    Attributes
    ----------
    STRING : str
        A free-text string value.
    LIST : str
        A value chosen from a predefined list.
    LIST_CUSTOM : str
        A custom list value, as returned by the rules endpoints.
    """

    STRING = "string"
    LIST = "list"
    LIST_CUSTOM = "list-custom"


class EntityLinkOption(EntityLink):
    """An entity link used as a selectable field option.

    Field options serialize their linked entities differently from a base
    :class:`~albert.core.shared.models.base.EntityLink`; this class handles that
    alternate (de)serialization.

    Attributes
    ----------
    id : str
        The linked entity's ID.
    name : str or None
        The linked entity's display name.
    """

    id: str = Field(alias="albertId")
    name: str | None = Field(default=None, exclude=False)


class EntityTypeFieldOptions(BaseAlbertModel):
    """The selectable options a rule can apply to a field.

    Attributes
    ----------
    option_type : EntityTypeOptionType
        The kind of option (string, list, or custom list).
    values : list[str or EntityLinkOption or EntityLink] or None
        The possible values for the option.
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
    """A change applied to a target field when a rule case is triggered.

    Attributes
    ----------
    target_field_name : str
        The name of the field this action affects.
    target_field_id : CustomFieldId or None
        The ID of the target custom field (format ``CTF...``), if known.
    hidden : bool or None
        Whether the target field is hidden.
    required : bool or None
        Whether the target field is required.
    default : str or float or EntityLinkOption or EntityLink or None
        The default value applied to the target field.
    options : EntityTypeFieldOptions or None
        The selectable options applied to the target field.
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
    """One trigger value and the actions to apply when it matches.

    Attributes
    ----------
    value : str
        The trigger field value that activates this case.
    actions : list[EntityTypeRuleAction]
        The actions to apply to target fields when this case is activated.
    """

    value: str
    actions: list[EntityTypeRuleAction]


class EntityTypeRuleTrigger(BaseAlbertModel):
    """The set of value cases evaluated for a rule.

    Attributes
    ----------
    cases : list[EntityTypeRuleTriggerCase]
        The cases evaluated against the trigger field's value; the matching case's
        actions are applied.
    """

    cases: list[EntityTypeRuleTriggerCase]


class EntityTypeRule(BaseResource):
    """A rule that makes an entity type's field behavior conditional.

    A rule watches one custom field (the trigger) and, depending on its value,
    applies actions to other fields, such as showing, hiding, requiring, or
    setting default options. Rules are read and set via
    :meth:`~albert.collections.entity_types.EntityTypeCollection.get_rules` and
    :meth:`~albert.collections.entity_types.EntityTypeCollection.set_rules`.

    Attributes
    ----------
    id : RuleId or None
        The unique identifier for the rule (format ``RUL...``).
    custom_field_id : CustomFieldId
        The ID of the trigger custom field the rule watches (format ``CTF...``).
    trigger : EntityTypeRuleTrigger
        The value cases that determine which actions are applied.
    """

    id: RuleId | None = Field(default=None)
    custom_field_id: CustomFieldId = Field(alias="customFieldId")
    trigger: EntityTypeRuleTrigger = Field(alias="trigger")
