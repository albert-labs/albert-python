from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class FieldType(str, Enum):
    """The value type stored by a custom field.

    Attributes
    ----------
    LIST : str
        A value (or values) chosen from a predefined list.
    STRING : str
        A free-text string value.
    NUMBER : str
        A numeric value.
    DATE : str
        A calendar date value.
    TIMESTAMP : str
        A date-and-time value.
    """

    LIST = "list"
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    TIMESTAMP = "timestamp"


class ServiceType(str, Enum):
    """The Albert entity a custom field is attached to.

    Attributes
    ----------
    INVENTORIES : str
        Field applies to Inventory Items.
    LOTS : str
        Field applies to Lots.
    PROJECTS : str
        Field applies to Projects.
    TASKS : str
        Field applies to Tasks.
    USERS : str
        Field applies to Users.
    PARAMETERS : str
        Field applies to Parameters.
    DATA_COLUMNS : str
        Field applies to Data Columns.
    DATA_TEMPLATES : str
        Field applies to Data Templates.
    PARAMETER_GROUPS : str
        Field applies to Parameter Groups.
    CAS : str
        Field applies to CAS records.
    SUBSTANCES : str
        Field applies to Substances.
    """

    INVENTORIES = "inventories"
    LOTS = "lots"
    PROJECTS = "projects"
    TASKS = "tasks"
    USERS = "users"
    PARAMETERS = "parameters"
    DATA_COLUMNS = "datacolumns"
    DATA_TEMPLATES = "datatemplates"
    PARAMETER_GROUPS = "parametergroups"
    CAS = "cas"
    SUBSTANCES = "substances"


class FieldCategory(str, Enum):
    """Who is allowed to add new items to a list custom field.

    Attributes
    ----------
    BUSINESS_DEFINED : str
        Only admins can add new allowed items to the list.
    USER_DEFINED : str
        General users can add new allowed items to the list.
    """

    BUSINESS_DEFINED = "businessDefined"
    USER_DEFINED = "userDefined"


class EntityCategory(str, Enum):
    """An entity category a custom field can apply to.

    Only some categories are valid for a given service.

    Attributes
    ----------
    FORMULAS : str
        Formulas inventory category.
    RAW_MATERIALS : str
        Raw materials inventory category.
    CONSUMABLES : str
        Consumables inventory category.
    EQUIPMENT : str
        Equipment inventory category.
    PROPERTY : str
        Property (measurement) category.
    BATCH : str
        Batch (formulation) category.
    GENERAL : str
        General category.
    """

    FORMULAS = "Formulas"
    RAW_MATERIALS = "RawMaterials"
    CONSUMABLES = "Consumables"
    EQUIPMENT = "Equipment"
    PROPERTY = "Property"
    BATCH = "Batch"
    GENERAL = "General"


class UIComponent(str, Enum):
    """Where in the UI a custom field is surfaced.

    Attributes
    ----------
    CREATE : str
        Shown on the entity's creation form.
    DETAILS : str
        Shown on the entity's details view.
    """

    CREATE = "create"
    DETAILS = "details"


class CustomFieldApiMethod(str, Enum):
    """HTTP method used to fetch values for an API-backed custom field.

    Attributes
    ----------
    GET : str
        Values are fetched with an HTTP GET request.
    """

    GET = "GET"


class CustomFieldAPI(BaseAlbertModel):
    """Configuration for a custom field whose values come from a remote API.

    Attributes
    ----------
    endpoint : str or None
        The URL the field's values are fetched from.
    method : CustomFieldApiMethod or None
        The HTTP method used to fetch values.
    query_params_field : list[str] or None
        Names of other fields whose values are passed as query parameters.
    """

    endpoint: str | None = Field(default=None)
    method: CustomFieldApiMethod | None = Field(default=None)
    query_params_field: list[str] | None = Field(default=None, alias="queryParamsField")


class ListDefaultValue(BaseAlbertModel):
    """A single allowed item used as a default for a list custom field.

    Attributes
    ----------
    id : str
        The ID of the list item.
    name : str
        The display name of the list item.
    """

    id: str = Field(alias="albertId")
    name: str


class StringDefault(BaseAlbertModel):
    """The default value for a string custom field.

    Attributes
    ----------
    type : FieldType
        Always ``FieldType.STRING``.
    value : str
        The default string value.
    """

    type: Literal[FieldType.STRING] = FieldType.STRING
    value: str


class NumberDefault(BaseAlbertModel):
    """The default value for a number custom field.

    Attributes
    ----------
    type : FieldType
        Always ``FieldType.NUMBER``.
    value : int or float
        The default numeric value.
    """

    type: Literal[FieldType.NUMBER] = FieldType.NUMBER
    value: int | float


class ListDefault(BaseAlbertModel):
    """The default value for a list custom field.

    Attributes
    ----------
    type : FieldType
        Always ``FieldType.LIST``.
    value : ListDefaultValue or list[ListDefaultValue]
        The default list item(s).

    Notes
    -----
    For multi-select custom fields, ``value`` must be a ``list[ListDefaultValue]``.
    """

    type: Literal[FieldType.LIST] = FieldType.LIST
    value: ListDefaultValue | list[ListDefaultValue]


Default = Annotated[
    StringDefault | NumberDefault | ListDefault,
    Field(discriminator="type"),
]


class CustomField(BaseResource):
    """A custom field definition in Albert.

    A custom field defines an allowed metadata field on an Albert entity. Once
    defined, its ``name`` may be used as a key in the ``metadata`` dict of the
    matching entity (Project, Inventory Item, User, Task, Lot, etc.), and its
    type and validation rules constrain the stored value. Create and manage
    custom fields through
    :class:`~albert.collections.custom_fields.CustomFieldCollection`.

    Attributes
    ----------
    name : str
        The field name (used as the metadata key). Cannot contain spaces.
    id : str or None
        The Custom Field ID (format ``CTF...``). Assigned by Albert on creation.
    field_type : FieldType
        The value type of the field (e.g. ``list``, ``string``, ``number``).
        ``string`` and ``list`` fields can be searchable; ``number`` fields
        cannot.
    display_name : str
        The human-readable label for the field. Can contain spaces. Limited to 40
        characters.
    searchable : bool or None
        Whether the field is searchable. Defaults to False. Supported for ``list``
        and ``string`` fields only.
    service : ServiceType
        The Albert entity the field is attached to.
    hidden : bool or None
        Whether the field is hidden. Defaults to False.
    lookup_column : bool or None
        Whether the field is a lookup column. Defaults to False. Only allowed for
        inventories.
    lookup_row : bool or None
        Whether the field is a lookup row. Defaults to False. Only allowed for
        formulas in inventories.
    category : FieldCategory or None
        Who may add new items to a list field. Required for ``list`` fields.
    min : int or float or None
        The minimum allowed value (or, for list fields, minimum selections).
    max : int or float or None
        The maximum allowed value (or, for list fields, maximum selections).
    entity_categories : list[EntityCategory] or None
        The entity categories the field applies to. Required for lookup row
        fields.
    custom_entity_categories : list[str] or None
        Custom entity categories that define where the field is valid.
    ui_components : list[UIComponent] or None
        Where the field is surfaced in the UI (``create`` and/or ``details``).
    required : bool or None
        Whether a value for the field is required.
    multiselect : bool or None
        For list fields, whether multiple values may be selected.
    editable : bool or None
        Whether the field can be edited in the UI.
    pattern : str or None
        A validation pattern the field's value must match.
    default : Default or None
        The default value applied to the field.
    api : CustomFieldAPI or None
        Configuration for fields whose values are backed by a remote API.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.custom_fields import (
            CustomField,
            FieldCategory,
            FieldType,
            ServiceType,
        )
        stage_gate_field = CustomField(
            name="stage_gate_status",
            display_name="Stage Gate",
            field_type=FieldType.LIST,
            service=ServiceType.PROJECTS,
            min=1,
            max=1,
            category=FieldCategory.BUSINESS_DEFINED,
        )
        ```
    """

    name: str
    id: str | None = Field(default=None, alias="albertId")
    field_type: FieldType = Field(alias="type")
    display_name: str = Field(alias="labelName", max_length=40)
    searchable: bool | None = Field(default=None, alias="search")
    service: ServiceType
    hidden: bool | None = Field(default=None)
    lookup_column: bool | None = Field(default=None, alias="lkpColumn")
    lookup_row: bool | None = Field(default=None, alias="lkpRow")
    category: FieldCategory | None = Field(default=None)
    min: int | float | None = Field(default=None)
    max: int | float | None = Field(default=None)
    entity_categories: list[EntityCategory] | None = Field(default=None, alias="entityCategory")
    custom_entity_categories: list[str] | None = Field(default=None, alias="customEntityCategory")
    ui_components: list[UIComponent] | None = Field(default=None, alias="ui_components")
    required: bool | None = Field(default=None)
    multiselect: bool | None = Field(default=None)
    editable: bool | None = Field(default=None)
    pattern: str | None = Field(default=None)
    default: Default | None = Field(default=None)
    api: CustomFieldAPI | None = Field(default=None)

    @model_validator(mode="after")
    def confirm_field_compatability(self) -> CustomField:
        if self.field_type == FieldType.LIST and self.category is None:
            raise ValueError("Category must be set for list fields")
        return self

    # TODO: Remove once API always includes 'type' in default payloads.
    # Required here because `Default` is a discriminated-union alias,
    # and Pydantic must see the discriminator to pick the correct variant.
    @field_validator("default", mode="before")
    @classmethod
    def ensure_default_has_type(cls, v: Any) -> Any:
        if v is None:
            return v

        if isinstance(v, dict) and "type" in v:
            return v

        if isinstance(v, dict) and "value" in v:
            raw_val = v["value"]

            if isinstance(raw_val, str):
                inferred_type = FieldType.STRING
            elif isinstance(raw_val, (int | float)):
                inferred_type = FieldType.NUMBER
            elif isinstance(raw_val, dict) and "albertId" in raw_val or isinstance(raw_val, list):
                inferred_type = FieldType.LIST
            else:
                raise ValueError(f"Cannot infer default type from value: {raw_val!r}")

            return {"type": inferred_type, "value": raw_val}

        return v


class SearchableCustomField(BaseAlbertModel):
    """A descriptor for a custom field that is exposed to search.

    Returned by
    :meth:`~albert.collections.custom_fields.CustomFieldCollection.get_searchable_fields`
    to describe how a field can be queried and sorted in search.

    Attributes
    ----------
    label : str
        The field's display label.
    type : str
        The field's value type.
    is_sortable : bool or None
        Whether search results can be sorted by this field.
    sort_by_param : str or None
        The parameter name to use when sorting by this field.
    is_custom : bool
        Whether the field is a custom field (as opposed to a standard field).
    """

    label: str
    type: str
    is_sortable: bool | None = Field(default=None, alias="isSortable")
    sort_by_param: str | None = Field(default=None, alias="sortByParam")
    is_custom: bool = Field(alias="isCustom")
