from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from albert.resources.base import AuditFields, BaseEntityLink, BaseResource, SecurityClass
from albert.resources.inventory import InventoryItem
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.tagged_base import BaseTaggedEntity
from albert.resources.units import Unit
from albert.resources.users import User
from albert.utils.types import BaseAlbertModel


class PGType(str, Enum):
    """The type of a parameter group"""

    GENERAL = "general"
    BATCH = "batch"
    PROPERTY = "property"


class PGMetadata(BaseResource):
    """The metadata of a parameter group"""

    standards: list[BaseEntityLink] = Field(alias="Standards")


class ParameterValue(BaseAlbertModel):
    """The value of a parameter in a parameter group.

    Attributes
    ----------
    parameter : Parameter
        The Parameter resource this value is associated with. Provide either an id or a parameter keyword argument.
    id : str | None
        The Albert ID of the Parameter resource this value is associated with. Provide either an id or a parameter keyword argument.
    category: ParameterCategory
        The category of the parameter.
    short_name : str | None
        The short name of the parameter value.
    value : str | None
        The value of the parameter. Can be a string or an InventoryItem (if, for example, the parameter is an instrumnt choice).
    unit : Unit | None
        The unit of measure for the provided parameter value.
    name : str
        The name of the parameter. Read-only.
    sequence : int
        The sequence of the parameter. Read-only.
    """

    parameter: Parameter = Field(default=None, exclude=True)
    id: str | None = Field(default=None)
    category: ParameterCategory | None = Field(default=None)
    short_name: str | None = Field(alias="shortName", default=None)
    value: str | SerializeAsEntityLink[InventoryItem] | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(alias="Unit", default=None)
    added: AuditFields | None = Field(alias="Added", default=None)

    # Read-only fields
    name: str | None = Field(default=None, exclude=True, frozen=True)
    sequence: str | None = Field(default=None, exclude=True, frozen=True)

    @field_validator("value", mode="before")
    @classmethod
    def validate_empty_value_dict(cls, value: Any) -> Any:
        if isinstance(value, dict) and not value:
            return None
        return value

    @model_validator(mode="after")
    def set_parameter_fields(self) -> "ParameterValue":
        if self.parameter is None and self.id is None:
            raise ValueError("Please provide either an id or an parameter object.")

        if self.parameter is not None:
            object.__setattr__(self, "id", self.parameter.id)
            object.__setattr__(self, "category", self.parameter.category)
            object.__setattr__(self, "name", self.parameter.name)

        return self


class ParameterGroup(BaseTaggedEntity):
    name: str
    type: PGType
    id: str | None = Field(None, alias="albertId")
    description: str | None = Field(default=None)
    security_class: SecurityClass = Field(default=SecurityClass.RESTRICTED, alias="class")
    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="ACL")
    metadata: PGMetadata | None = Field(alias="Metadata", default=None)
    parameters: list[ParameterValue] = Field(default_factory=list, alias="Parameters")

    # Read-only fields
    verified: bool = Field(default=False, exclude=True, frozen=True)
    documents: list[BaseEntityLink] = Field(default_factory=list, exclude=True, frozen=True)
