from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class FieldType(str, Enum):
    """The type of the custom field."""

    LIST = "list"
    STRING = "string"
    NUMBER = "number"


class ServiceType(str, Enum):
    """The service type the custom field is associated with"""

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
    """The ACL level of the custom field"""

    BUSINESS_DEFINED = "businessDefined"
    USER_DEFINED = "userDefined"


class EntityCategory(str, Enum):
    """The entity category of the custom field. Only some categories are allowed for certain services"""

    FORMULAS = "Formulas"
    RAW_MATERIALS = "RawMaterials"
    CONSUMABLES = "Consumables"
    EQUIPMENT = "Equipment"
    PROPERTY = "Property"
    BATCH = "Batch"
    GENERAL = "General"


class UIComponent(str, Enum):
    """The UI component available to the custom field"""

    CREATE = "create"
    DETAILS = "details"


class CustomFieldApiMethod(str, Enum):
    """HTTP methods supported by API-driven custom fields."""

    GET = "GET"


class CustomFieldAPI(BaseAlbertModel):
    """Configuration for API-backed custom fields."""

    endpoint: str | None = Field(default=None)
    method: CustomFieldApiMethod | None = Field(default=None)
    query_params_field: list[str] | None = Field(default=None, alias="queryParamsField")


class ListDefaultValue(BaseAlbertModel):
    """An item from a list-type custom field used as a default value.

    Attributes
    ----------
    id : str
        The Albert ID of the list item.
    name : str
        The display name of the list item.
    """

    id: str = Field(alias="albertId")
    name: str


class StringDefault(BaseAlbertModel):
    """A default value for a string-type custom field.

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
    """A default value for a number-type custom field.

    Attributes
    ----------
    type : FieldType
        Always ``FieldType.NUMBER``.
    value : int | float
        The default numeric value.
    """

    type: Literal[FieldType.NUMBER] = FieldType.NUMBER
    value: int | float


class ListDefault(BaseAlbertModel):
    """
    !!! note
        For multi-select custom fields, `value` must be `list[ListDefaultValue]`.
    """

    type: Literal[FieldType.LIST] = FieldType.LIST
    value: ListDefaultValue | list[ListDefaultValue]


Default = Annotated[
    StringDefault | NumberDefault | ListDefault,
    Field(discriminator="type"),
]


class CustomField(BaseResource):
    """A custom field that can be attached as metadata to an entity in Albert.

    Attributes
    ----------
    name : str
        The internal name of the custom field. Cannot contain spaces.
    id : str | None
        The Albert ID of the custom field.
    field_type : FieldType
        The data type of the field. Allowed values are ``list``, ``string``, and ``number``.
        ``string`` and ``list`` fields are searchable; ``number`` fields are not.
    display_name : str
        The human-readable label for the field. Can contain spaces (max 40 chars).
    searchable : bool | None
        Whether the field is searchable. Supported for ``list`` and ``string`` fields only.
    service : ServiceType
        The entity type this field is associated with (e.g. inventories, lots, tasks).
    hidden : bool | None
        Whether the field is hidden in the UI.
    lookup_column : bool | None
        Whether the field is a lookup column. Only allowed for inventories.
    lookup_row : bool | None
        Whether the field is a lookup row. Only allowed for formula inventories.
    category : FieldCategory | None
        The ACL category of the field. Required for ``list`` fields.
    min : int | float | None
        The minimum allowed value for number fields.
    max : int | float | None
        The maximum allowed value for number fields.
    entity_categories : list[EntityCategory] | None
        The entity categories where this field applies. Required for lookup row fields.
    custom_entity_categories : list[str] | None
        Custom entity category names where the field is valid.
    ui_components : list[UIComponent] | None
        The UI contexts where this field appears (e.g. ``create``, ``details``).
    required : bool | None
        Whether the field is required when creating an entity.
    multiselect : bool | None
        Whether multiple values can be selected for list fields.
    editable : bool | None
        Whether the field is editable in the UI.
    pattern : str | None
        A validation regex pattern for string fields.
    default : Default | None
        The default value for the field.
    api : CustomFieldAPI | None
        API configuration for fields backed by remote data sources.
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
    """Metadata describing custom fields exposed to search."""

    label: str
    type: str
    is_sortable: bool | None = Field(default=None, alias="isSortable")
    sort_by_param: str | None = Field(default=None, alias="sortByParam")
    is_custom: bool = Field(alias="isCustom")
