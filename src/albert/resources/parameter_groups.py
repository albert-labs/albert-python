from enum import Enum
from typing import Any

from pydantic import Field, PrivateAttr

from albert.resources.base import AuditFields, BaseEntityLink, BaseResource, SecurityClass
from albert.resources.inventory import InventoryItem
from albert.resources.parameters import Parameter
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.units import Unit
from albert.resources.users import User
from albert.utils.exceptions import AlbertException


class PGType(str, Enum):
    """The type of a parameter group"""

    GENERAL = "general"
    BATCH = "batch"
    PROPERTY = "property"


class PGMetadata(BaseResource):
    """The metadata of a parameter group"""

    standards: list[BaseEntityLink] = Field(alias="Standards")


class ParameterValue(BaseResource):
    """The valie of a parameter in a parameter group.

    Attributes
    ----------
    parameter : Parameter
        The Parameter resource this value is associated with. Provide either an id or a parameter keyword argument.
    id : str | None
        The Albert ID of the Parameter resource this value is associated with. Provide either an id or a parameter keyword argument.
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
    _name = PrivateAttr(default=None)
    short_name: str | None = Field(alias="shortName", default=None)
    value: str | None | SerializeAsEntityLink[InventoryItem] = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(alias="Unit", default=None)
    _sequence: int | None = PrivateAttr(default=None)
    added: AuditFields | None = Field(alias="Added", default=None)

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "name" in data:
            self._name = data["name"]
        if "sequence" in data:
            self._sequence = data["sequence"]
        if "parameter" in data:
            if "albertId" in data or "id" in data:
                AlbertException("Please provide either an id or an parameter object, not both.")
            else:
                param_id = (
                    data["parameter"].get("albertId", None)
                    if isinstance(data["parameter"], dict)
                    else data["parameter"].id
                )
                if param_id is None:
                    param_id = data["parameter"].get("id", None)
                if param_id is None:
                    raise AlbertException(
                        "You must first create the parameter before creating a parameter value. Your parameter object must have an id."
                    )
                data["albertId"] = param_id
                data["name"] = (
                    data["parameter"]["name"]
                    if isinstance(data["parameter"], dict)
                    else data["parameter"].name
                )
        elif "id" not in data and not data["parameter"]:
            AlbertException("Please provide either an id or an parameter object.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def sequence(self) -> int:
        return self._sequence


class ParameterGroup(BaseResource):
    id: str | None = Field(None, alias="albertId")
    name: str
    description: str | None = Field(default=None)
    type: PGType
    security_class: SecurityClass = Field(default=SecurityClass.RESTRICTED, alias="class")
    _verified: bool = PrivateAttr(default=False)
    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="ACL")
    metadata: PGMetadata | None = Field(alias="Metadata", default=None)
    _documents: list[BaseEntityLink] = PrivateAttr(default_factory=list)
    parameters: list[ParameterValue] = Field(alias="Parameters")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "verified" in data:
            self._verified = bool(data["verified"])
        if "Documents" in data:
            self._documents = data["Documents"]

    @property
    def verified(self) -> bool:
        return self._verified

    @property
    def documents(self) -> list[BaseEntityLink]:
        return self._documents
