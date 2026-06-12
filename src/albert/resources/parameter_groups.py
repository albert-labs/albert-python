from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass
from albert.core.shared.models.base import AuditFields, EntityLink, LocalizedNames
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.inventory import InventoryItem
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.tags import Tag
from albert.resources.units import Unit
from albert.resources.users import User


class PGType(str, Enum):
    """The type of a parameter group"""

    GENERAL = "general"
    BATCH = "batch"
    PROPERTY = "property"


class DataType(str, Enum):
    NUMBER = "number"
    STRING = "string"
    ENUM = "enum"
    IMAGE = "image"
    CURVE = "curve"


class Operator(str, Enum):
    # We may want to abstract this out if we end up reusing on Data Templates
    BETWEEN = "between"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN_OR_EQUAL = "gte"
    GREATER_THAN = "gt"
    EQUALS = "eq"


class EnumValidationValue(BaseAlbertModel):
    """Represents a value for an enum type validation.

    Attributes
    ----------
    text : str
        The text of the enum value.
    id : str | None
        The ID of the enum value. If not provided, the ID will be generated upon creation.
    """

    text: str = Field()

    id: str | None = Field(default=None)
    # read only field
    original_text: str | None = Field(
        default=None, exclude=True, frozen=True, alias="originalText"
    )


class ValueValidation(BaseAlbertModel):
    """A validation rule applied to a parameter or data column value.

    Attributes
    ----------
    datatype : DataType
        The data type the validation applies to.
    value : str | list[EnumValidationValue] | None
        The allowed value or list of allowed enum values.
    min : str | None
        The minimum allowed value (for range validations).
    max : str | None
        The maximum allowed value (for range validations).
    operator : Operator | None
        The comparison operator for the validation rule.
    """

    # We may want to abstract this out if we end up reusing on Data Templates
    datatype: DataType = Field(...)
    value: str | list[EnumValidationValue] | None = Field(default=None)
    min: str | None = Field(default=None)
    max: str | None = Field(default=None)
    operator: Operator | None = Field(default=None)


class ParameterValue(BaseAlbertModel):
    """The value of a parameter in a parameter group.

    Attributes
    ----------
    parameter : Parameter or None
        The Parameter resource this value is associated with. Provide either an id or a parameter keyword argument.
    id : str or None
        The Albert ID of the Parameter resource this value is associated with. Provide either an id or a parameter keyword argument.
    category : ParameterCategory or None
        The category of the parameter.
    short_name : str or None
        The short name of the parameter value.
    value : str or InventoryItem or None
        The value of the parameter. Can be a plain string or an InventoryItem (e.g. when the parameter represents an instrument choice).
    unit : Unit or None
        The unit of measure for the provided parameter value.
    required : bool or None
        Whether this parameter is required. Defaults to False.
    validation : list[ValueValidation] or None
        Validation rules applied to the parameter value.
    name : str or None
        The name of the parameter. Read-only.
    sequence : str or None
        The sequence of the parameter. Read-only.
    """

    parameter: Parameter | None = Field(default=None, exclude=True)
    id: str | None = Field(default=None)
    category: ParameterCategory | None = Field(default=None)
    short_name: str | None = Field(alias="shortName", default=None)
    value: str | SerializeAsEntityLink[InventoryItem] | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(alias="Unit", default=None)
    added: AuditFields | None = Field(alias="Added", default=None, exclude=True)
    required: bool | None = Field(default=None)
    validation: list[ValueValidation] | None = Field(default_factory=list)

    # Read-only fields
    name: str | None = Field(default=None, exclude=True, frozen=True)
    sequence: str | None = Field(default=None, exclude=True)
    original_short_name: str | None = Field(
        default=None, alias="originalShortName", frozen=True, exclude=True
    )
    original_name: str | None = Field(
        default=None, alias="originalName", frozen=True, exclude=True
    )

    @field_validator("value", mode="before")
    @classmethod
    def validate_parameter_value(cls, value: Any) -> Any:
        # Bug in ParameterGroups sometimes returns incorrect JSON from batch endpoint
        # Set to None if value is a dict but no ID field
        # Reference: https://linear.app/albert-invent/issue/IN-10
        if isinstance(value, dict) and "id" not in value:
            return None
        return value

    @model_validator(mode="after")
    def set_parameter_fields(self) -> ParameterValue:
        if self.parameter is None and self.id is None:
            raise ValueError("Please provide either an id or an parameter object.")

        if self.parameter is not None:
            object.__setattr__(self, "id", self.parameter.id)
            object.__setattr__(self, "category", self.parameter.category)
            object.__setattr__(self, "name", self.parameter.name)

        return self


class ParameterGroup(BaseTaggedResource):
    """A group of parameters defining the conditions for a measurement workflow.

    Use the ``"Standards"`` key in ``metadata`` to store associated standards.

    Attributes
    ----------
    name : str
        The name of the parameter group.
    type : PGType | None
        The type of parameter group (general, batch, or property).
    id : str | None
        The Albert ID of the parameter group.
    description : str | None
        A description of the parameter group.
    security_class : SecurityClass
        The security classification. Defaults to ``RESTRICTED``.
    acl : list[User] | None
        Users with explicit access to this parameter group.
    metadata : dict[str, MetadataItem]
        Custom metadata attached to the parameter group.
    parameters : list[ParameterValue]
        The parameter definitions and their values/intervals.
    verified : bool
        Whether the parameter group has been verified. Read-only.
    documents : list[EntityLink]
        Documents linked to this parameter group. Read-only.
    """

    name: str
    type: PGType | None = Field(default=None)
    id: str | None = Field(None, alias="albertId")
    description: str | None = Field(default=None)
    security_class: SecurityClass = Field(default=SecurityClass.RESTRICTED, alias="class")
    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="ACL")
    metadata: dict[str, MetadataItem] = Field(alias="Metadata", default_factory=dict)
    parameters: list[ParameterValue] = Field(default_factory=list, alias="Parameters")

    # Read-only fields
    verified: bool = Field(default=False, exclude=True, frozen=True)
    documents: list[EntityLink] = Field(default_factory=list, exclude=True, frozen=True)


class ParameterSearchItemParameter(BaseAlbertModel):
    """A lightweight parameter reference within a parameter group search result.

    Attributes
    ----------
    name : str | None
        The name of the parameter.
    id : str
        The Albert ID of the parameter.
    localized_names : LocalizedNames
        Localized name variants for the parameter.
    """

    name: str | None = None
    id: str
    localized_names: LocalizedNames = Field(alias="localizedNames")


class ParameterGroupSearchItem(BaseAlbertModel, HydrationMixin[ParameterGroup]):
    """Lightweight representation of a ParameterGroup returned from search.

    Attributes
    ----------
    name : str
        The name of the parameter group.
    type : PGType | None
        The type of parameter group.
    id : str | None
        The Albert ID of the parameter group.
    description : str | None
        A description of the parameter group.
    parameters : list[ParameterSearchItemParameter]
        Summary of the parameters in the group.
    owner : list[User] | None
        Owners of the parameter group.
    tags : list[User] | None
        Tags associated with the parameter group.
    acl : list[User] | None
        Users with explicit access to the parameter group.
    created_at : str | None
        ISO 8601 timestamp of when the parameter group was created.
    created_by_name : str | None
        The name of the user who created the parameter group.
    metadata : dict[str, MetadataItem] | None
        Custom metadata attached to the parameter group.
    team : list[User] | None
        Team members associated with the parameter group.
    """

    name: str
    type: PGType | None = Field(default=None)
    id: str | None = Field(None, alias="albertId")
    description: str | None = Field(default=None)
    parameters: list[ParameterSearchItemParameter] = Field(
        default_factory=list, alias="parameters"
    )
    owner: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="owner")
    tags: list[SerializeAsEntityLink[Tag]] | None = Field(default=None, alias="tags")
    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="acl")
    created_at: str | None = Field(default=None, alias="createdAt")
    created_by_name: str | None = Field(default=None, alias="createdByName")
    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="metadata")
    team: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="team")
