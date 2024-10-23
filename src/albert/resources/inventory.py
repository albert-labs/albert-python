from enum import Enum
from typing import Any

from pydantic import Field, PrivateAttr, model_validator

from albert.collections.cas import Cas
from albert.collections.companies import Company
from albert.collections.un_numbers import UnNumber
from albert.resources.acls import ACL
from albert.resources.base import (
    BaseEntityLink,
    BaseResource,
    EntityLinkConvertible,
    SecurityClass,
)
from albert.resources.locations import Location
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.tagged_base import BaseTaggedEntity
from albert.utils.exceptions import AlbertException


class InventoryCategory(str, Enum):
    RAW_MATERIALS = "RawMaterials"
    CONSUMABLES = "Consumables"
    EQUIPMENT = "Equipment"
    FORMULAS = "Formulas"


class InventoryUnitCategory(str, Enum):
    MASS = "mass"
    VOLUME = "volume"
    LENGTH = "length"
    PRESSURE = "pressure"
    UNITS = "units"


class CasAmount(BaseResource):
    """
    CasAmount is a Pydantic model representing an amount of a given CAS.

    Attributes
    ----------
    cas : Cas
        The CAS object associated with this amount. Provide either a Cas or an id.
    id : str
        The Albert id of the CAS Number Resource this amount represents. Provide either a Cas or an id.
    min : float, optional
        The minimum amount of the CAS in the formulation.
    max : float, optional
        The maximum amount of the CAS in the formulation.

    """

    id: str | None = Field(default=None)
    min: float = Field(default=None)
    max: float = Field(default=None)

    # Define a private attribute to store the Cas object
    cas: Cas = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def set_cas_private_attr(self: "CasAmount") -> "CasAmount":
        """
        Set the _cas attribute after model initialization.
        """
        if hasattr(self, "cas") and isinstance(self.cas, Cas):
            # Avoid recursion by setting the attribute directly
            object.__setattr__(self, "_cas", self.cas)  # Set the private _cas attribute
            object.__setattr__(self, "id", self.cas.id)  # Set the id to the Cas id

        return self


class InventoryMinimum(BaseResource):
    """Defined the minimum amount of an InventoryItem that must be kept in stock at a given Location.
    Attributes
    ----------
    location : Location
        The Location object associated with this InventoryMinimum. Provide either a Location or a location id.
    id : str
        The unique identifier of the Location object associated with this InventoryMinimum. Provide either a Location or a location id.
    minimum : float
        The minimum amount of the InventoryItem that must be kept in stock at the given Location.
    """

    location: Location | None = Field(exclude=True, default=None)
    id: str | None = Field(default=None)
    minimum: float = Field(ge=0, le=1000000000000000)

    @model_validator(mode="after")
    def check_id_or_location(self: "InventoryMinimum") -> "InventoryMinimum":
        """
        Ensure that either an id or a location is provided.
        """
        if self.id is None and self.location is None:
            raise AlbertException(
                "Either an id or a location must be provided for an InventoryMinimum."
            )
        if self.id and self.location and self.location.id != self.id:
            raise AlbertException(
                "Only an id or a location can be provided for an InventoryMinimum, not both."
            )

        elif self.location:
            # Avoid recursion by setting the attribute directly
            object.__setattr__(self, "id", self.location.id)
            object.__setattr__(self, "name", self.location.name)

        return self


class InventoryItem(BaseTaggedEntity, EntityLinkConvertible):
    """An InventoryItem is a Pydantic model representing an item in the inventory. Can be a raw material, consumable, equipment, or formula.
    Note: Formulas should be registered via the Worksheet collection / Sheet resource.

    Returns
    -------
    InventoryItem
        An InventoryItem that can be used to represent an item in the inventory. Can be a raw material, consumable, equipment, or formula.

    Attributes
    ------

    name : str
        The name of the InventoryItem.
    id : str | None
        The Albert ID of the InventoryItem. Set when the InventoryItem is retrieved from Albert.
    description : str | None
        The description of the InventoryItem.
    category : InventoryCategory
        The category of the InventoryItem. Allowed values are `RawMaterials`, `Consumables`, `Equipment`, and `Formulas`.
    unit_category : InventoryUnitCategory
        The unit category of the InventoryItem. Can be mass, volume, length, pressure, or units. By default, mass is used for RawMaterials and Formulas, and units is used for Equipment and Consumables.
    security_class : SecurityClass | None
        The security class of the InventoryItem. Optional. Can be confidential, shared, or restricted.
    company : Company | str | None
        The company associated with the InventoryItem. Can be a Company object or a string. If a String is provided, a Company object with the name of the provided string will be first-or-created.
    minimum : list[InventoryMinimum] | None
        The minimum amount of the InventoryItem that must be kept in stock at a given Location. Optional.
    alias : str | None
        An alias for the InventoryItem. Optional.
    cas : list[CasAmount] | None
        The CAS numbers associated with the InventoryItem. This is how a compositional breakdown can be provided. Optional.
    metadata : dict[str, str | list[BaseEntityLink] | BaseEntityLink] | None
        Metadata associated with the InventoryItem. Optional. Allowed metadata fields can be found in the CustomFields documentation.
    project_id : str | None
        The project ID associated with the InventoryItem. Read Only. Required for Formulas.
    formula_id : str | None
        The formula ID associated with the InventoryItem. Read Only.
    tags : list[str|Tag] | None
        The tags associated with the InventoryItem. Optional. If a string is provided, a Tag object with the name of the provided string will be first-or-created.
    """

    name: str | None = None
    id: str | None = Field(None, alias="albertId")
    description: str | None = None
    category: InventoryCategory
    unit_category: InventoryUnitCategory = Field(default=None, alias="unitCategory")
    security_class: SecurityClass | None = Field(default=None, alias="class")
    company: SerializeAsEntityLink[Company] | None = Field(default=None, alias="Company")
    minimum: list[InventoryMinimum] | None = Field(default=None)  # To do
    alias: str | None = Field(default=None)
    cas: list[CasAmount] | None = Field(default=None, alias="Cas")
    metadata: dict[str, str | list[BaseEntityLink] | BaseEntityLink] | None = Field(
        alias="Metadata", default=None
    )
    project_id: str | None = Field(default=None, alias="parentId")

    _task_config: list[dict] | None = PrivateAttr(default=None)
    _formula_id: str | None = PrivateAttr(default=None)
    _symbols: list[dict] | None = PrivateAttr(default=None)  # read only: comes from attachments
    _un_number: UnNumber | None = PrivateAttr(default=None)  # Read only: Comes from attachments
    _acls: list[ACL] | None = PrivateAttr(default=None)  # read only

    def __init__(self, **data: Any):
        super().__init__(**data)
        # handle aliases on private attributes
        if "ACL" in data:
            self._acls = data["ACL"]
        if "unNumber" in data:  # pragma: no cover (We need them to seed UnNumbers for us)
            self._un_number = data["unNumber"]
        if "Symbols" in data:
            self._symbols = data["Symbols"]
        if "TaskConfig" in data:
            self._task_config = data["TaskConfig"]
        if "Minimum" in data:
            self._minimum = data["Minimum"]
        if "formulaId" in data:
            self._formula_id = data["formulaId"]

    @model_validator(
        mode="before"
    )  # Must happen before the model is created so unit_category is set
    @classmethod
    def set_unit_category(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Set the unit category based on the inventory category.

        Parameters
        ----------
        values : Dict[str, Any]
            A dictionary of field values.

        Returns
        -------
        Dict[str, Any]
            Updated field values with unit category set.
        """
        category = values.get("category")
        unit_category = values.get("unit_category")
        if unit_category is None:
            if category in (
                InventoryCategory.RAW_MATERIALS,
                InventoryCategory.RAW_MATERIALS.value,
                InventoryCategory.FORMULAS,
                InventoryCategory.FORMULAS.value,
            ):
                values["unit_category"] = InventoryUnitCategory.MASS.value
            elif category in (
                InventoryCategory.EQUIPMENT,
                InventoryCategory.EQUIPMENT.value,
                InventoryCategory.CONSUMABLES,
                InventoryCategory.CONSUMABLES.value,
            ):
                values["unit_category"] = InventoryUnitCategory.UNITS.value
        return values

    @model_validator(mode="before")  # must happen before to keep type consistency
    @classmethod
    def convert_company(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert the company field to a Company object if it is a string.

        Parameters
        ----------
        data : Dict[str, Any]
            A dictionary of field values.

        Returns
        -------
        Dict[str, Any]
            Updated field values with company converted.
        """
        company = data.get("company", data.get("Company"))
        if company:
            if isinstance(company, Company):
                data["company"] = company
            elif isinstance(company, str):
                data["company"] = Company(name=company)
            else:
                pass
                # We do not expect this else to be hit because comapanies should only be Company or str
        return data

    @model_validator(mode="after")
    def ensure_formula_fields(self: "InventoryMinimum") -> "InventoryItem":
        """
        Ensure required fields are present for formulas.

        Parameters
        ----------
        data : Dict[str, Any]
            A dictionary of field values.

        Returns
        -------
        Dict[str, Any]
            Updated field values with required fields ensured.

        Raises
        ------
        AttributeError
            If a required project_id is missing for formulas.
        """
        if self.category == "Formulas" and not self.project_id and not self.id:
            # Some legacy on platform formulas don't have a project_id so check if its already on platform
            raise AlbertException("A project_id must be supplied for all formulas.")
        return self

    @property
    def formula_id(self) -> str | None:
        return self._formula_id
