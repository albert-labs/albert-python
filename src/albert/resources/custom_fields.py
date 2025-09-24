from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class FieldType(str, Enum):
    """The type (list or string) of the custom field"""

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


class ListDefaultValue(BaseAlbertModel):
    id: str = Field(alias="albertId")
    name: str


class StringDefault(BaseAlbertModel):
    type: Literal[FieldType.STRING] = FieldType.STRING
    value: str


class NumberDefault(BaseAlbertModel):
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
    """A custom field for an entity in Albert.

    Returns
    -------
    CustomField
        A CustomField that can be used to attach Metadata to an entity in Albert.
    Attributes
    ------
    name : str
        The name of the custom field. Cannot contain spaces.
    id : str | None
        The Albert ID of the custom field.
    field_type : FieldType
        The type of the custom field. Allowed values are `list` and `string`. String fields cannot be searchable and are used to set uncontrolled metadata. List fields can be searchable and are used to set controlled metadata.
    display_name : str
        The display name of the custom field. Can contain spaces.
    searchable : bool | None
        Whether the custom field is searchable, optional. Defaults to False.
    service : ServiceType
        The service type the custom field is associated with.
    hidden : bool | None
        Whether the custom field is hidden, optional. Defaults to False.
    lookup_column : bool | None
        Whether the custom field is a lookup column, optional. Defaults to False. Only allowed for inventories.
    lookup_row : bool | None
        Whether the custom field is a lookup row, optional. Defaults to False. Only allowed for formulas in inventories.
    category : FieldCategory | None
        The category of the custom field, optional. Defaults to None. Required for list fields. Allowed values are `businessDefined` and `userDefined`.
    min : int | None
        The minimum value of the custom field, optional. Defaults to None.
    max : int | None
        The maximum value of the custom field, optional. Defaults to None.
    entity_categories : list[EntityCategory] | None
        The entity categories of the custom field, optional. Defaults to None. Required for lookup row fields. Allowed values are `Formulas`, `RawMaterials`, `Consumables`, `Equipment`, `Property`, `Batch`, and `General`.
    ui_components : list[UIComponent] | None
        The UI components available to the custom field, optional. Defaults to None. Allowed values are `create` and `details`.
    default: Default | None
        The default value of the custom field, optional. Defaults to None.
    editable: Default | None
        Decides whether the field should be editable on UI or not.
    """

    name: str
    id: str | None = Field(default=None, alias="albertId")
    field_type: FieldType = Field(alias="type")
    display_name: str = Field(alias="labelName")
    searchable: bool | None = Field(default=None, alias="search")
    service: ServiceType
    hidden: bool | None = Field(default=None)
    lookup_column: bool | None = Field(default=None, alias="lkpColumn")
    lookup_row: bool | None = Field(default=None, alias="lkpRow")
    category: FieldCategory | None = Field(default=None)
    min: int | None = Field(default=None)
    max: int | None = Field(default=None)
    entity_categories: list[EntityCategory] | None = Field(default=None, alias="entityCategory")
    ui_components: list[UIComponent] | None = Field(default=None, alias="ui_components")
    required: bool | None = Field(default=None)
    multiselect: bool | None = Field(default=None)
    pattern: str | None = Field(default=None)
    default: Default | None = Field(default=None)
    editable: bool | None = Field(default=None)

    @model_validator(mode="after")
    def confirm_field_compatability(self) -> "CustomField":
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
