from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from albert.collections.cas import Cas
from albert.collections.companies import Company
from albert.resources.acls import ACL
from albert.resources.base import MetadataItem, SecurityClass
from albert.resources.identifiers import InventoryId
from albert.resources.locations import Location
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.tags import Tag
from albert.utils.types import BaseAlbertModel

ALL_MERGE_MODULES = [
    "PRICING",
    "NOTES",
    "SDS",
    "PD",
    "BD",
    "LOT",
    "CAS",
    "TAS",
    "WFL",
    "PRG",
    "PTD",
]
"""All modules selectable for inventory merge."""


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


class CasAmount(BaseAlbertModel):
    """
    CasAmount is a Pydantic model representing an amount of a given CAS.

    Attributes
    ----------
    min : float
        The minimum amount of the CAS in the formulation.
    max : float
        The maximum amount of the CAS in the formulation.
    id : str | None
        The Albert ID of the CAS Number Resource this amount represents. Provide either a Cas or an ID.
    cas : Cas | None
        The CAS object associated with this amount. Provide either a Cas or an id.
    cas_smiles: str | None
        The SMILES string of the CAS Number resource. Obtained from the Cas object when provided.
    number: str | None
        The CAS number. Obtained from the Cas object when provided.
    """

    min: float
    max: float
    target: float | None = Field(default=None, alias="inventoryValue")
    id: str | None = Field(default=None)
    cas_category: str | None = Field(default=None, alias="casCategory")

    # Read-only fields
    cas: Cas | None = Field(default=None, exclude=True)
    cas_smiles: str | None = Field(default=None, alias="casSmiles", exclude=True, frozen=True)
    number: str | None = Field(default=None, exclude=True, frozen=True)

    @model_validator(mode="after")
    def set_cas_attributes(self: "CasAmount") -> "CasAmount":
        """Set attributes after model initialization from the Cas object, if provided."""
        if self.cas is not None:
            object.__setattr__(self, "id", self.cas.id)
            object.__setattr__(self, "cas_smiles", self.cas.smiles)
            object.__setattr__(self, "number", self.cas.number)
        return self


class InventoryMinimum(BaseAlbertModel):
    """Defined the minimum amount of an InventoryItem that must be kept in stock at a given Location.

    Attributes
    ----------
    id : str
        The unique identifier of the Location object associated with this InventoryMinimum.
        Provide either a Location or a location id.
    location : Location
        The Location object associated with this InventoryMinimum. Provide either a Location or a location id.
    minimum : float
        The minimum amount of the InventoryItem that must be kept in stock at the given Location.
    """

    id: str | None = Field(default=None)
    location: Location | None = Field(exclude=True, default=None)
    minimum: float = Field(ge=0, le=1000000000000000)

    @model_validator(mode="after")
    def check_id_or_location(self: "InventoryMinimum") -> "InventoryMinimum":
        """
        Ensure that either an id or a location is provided.
        """
        if self.id is None and self.location is None:
            raise ValueError(
                "Either an id or a location must be provided for an InventoryMinimum."
            )
        if self.id and self.location and self.location.id != self.id:
            raise ValueError(
                "Only an id or a location can be provided for an InventoryMinimum, not both."
            )

        elif self.location:
            # Avoid recursion by setting the attribute directly
            object.__setattr__(self, "id", self.location.id)
            object.__setattr__(self, "name", self.location.name)

        return self


class InventoryItem(BaseTaggedResource):
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
    metadata : dict[str, str | list[EntityLink] | EntityLink] | None
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
    unit_category: InventoryUnitCategory | None = Field(default=None, alias="unitCategory")
    security_class: SecurityClass | None = Field(default=None, alias="class")
    company: SerializeAsEntityLink[Company] | None = Field(default=None, alias="Company")
    minimum: list[InventoryMinimum] | None = Field(default=None)  # To do
    alias: str | None = Field(default=None)
    cas: list[CasAmount] | None = Field(default=None, alias="Cas")
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    project_id: str | None = Field(default=None, alias="parentId")
    acls: list[ACL] = Field(default_factory=list, alias="ACL")

    # Read-only fields
    task_config: list[dict] | None = Field(
        default=None, alias="TaskConfig", exclude=True, frozen=True
    )
    formula_id: str | None = Field(default=None, alias="formulaId", exclude=True, frozen=True)
    symbols: list[dict] | None = Field(default=None, alias="Symbols", exclude=True, frozen=True)
    un_number: str | None = Field(default=None, alias="unNumber", exclude=True, frozen=True)
    recent_atachment_id: str | None = Field(
        default=None, alias="recentAttachmentId", exclude=True, frozen=True
    )

    @field_validator("company", mode="before")
    @classmethod
    def validate_company_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = Company(name=value)
        return value

    @field_validator("un_number", mode="before")
    @classmethod
    def validate_un_number(cls, value: Any) -> Any:
        if value == "N/A":
            value = None
        return value

    @model_validator(mode="after")
    def set_unit_category(self) -> "InventoryItem":
        """Set unit category from category if not defined."""
        if self.unit_category is None:
            if self.category in [InventoryCategory.RAW_MATERIALS, InventoryCategory.FORMULAS]:
                object.__setattr__(self, "unit_category", InventoryUnitCategory.MASS)
            elif self.category in [InventoryCategory.EQUIPMENT, InventoryCategory.CONSUMABLES]:
                object.__setattr__(self, "unit_category", InventoryUnitCategory.UNITS)
        return self

    @model_validator(mode="after")
    def validate_formula_fields(self) -> "InventoryItem":
        """Ensure required fields are present for formulas."""
        if self.category == InventoryCategory.FORMULAS and not self.project_id and not self.id:
            # Some legacy on platform formulas don't have a project_id so check if its already on platform
            raise ValueError("A project_id must be supplied for all formulas.")
        return self


class InventorySpecValue(BaseAlbertModel):
    min: str | None = Field(default=None)
    max: str | None = Field(default=None)
    reference: str | None = Field(default=None)
    comparison_operator: str | None = Field(default=None, alias="comparisonOperator")


class InventorySpec(BaseAlbertModel):
    id: str | None = Field(default=None, alias="albertId")
    name: str
    data_column_id: str = Field(..., alias="datacolumnId")
    data_column_name: str | None = Field(default=None, alias="datacolumnName")
    data_template_id: str | None = Field(default=None, alias="datatemplateId")
    data_template_name: str | None = Field(default=None, alias="datatemplateName")
    unit_id: str | None = Field(default=None, alias="unitId")
    unit_name: str | None = Field(default=None, alias="unitName")
    workflow_id: str | None = Field(default=None, alias="workflowId")
    workflow_name: str | None = Field(default=None, alias="workflowName")
    spec_config: str | None = Field(default=None, alias="specConfig")
    value: InventorySpecValue | None = Field(default=None, alias="Value")


class InventorySpecList(BaseAlbertModel):
    parent_id: str = Field(..., alias="parentId")
    specs: list[InventorySpec] = Field(..., alias="Specs")


# TODO: Find other pictogram items across the platform
# and see if this is unique to the search endpoint or a
# common resource
class InventorySearchPictogramItem(BaseAlbertModel):
    id: str
    name: str
    status: str | None = Field(default=None)


# This class is very similar to the UnNumber class,
# but the fields are not all required (and there is no Id in this one)
# if UnNumber doesn't require all fields we can
# merge these two classes together
class InventorySearchSDSItem(BaseAlbertModel):
    un_number: str | None = Field(default=None, alias="unNumber")
    storage_class_name: str | None = Field(default=None, alias="storageClassName")
    shipping_description: str | None = Field(default=None, alias="shippingDescription")
    storage_class_number: str | None = Field(default=None, alias="storageClassNumber")
    un_classification: str | None = Field(default=None, alias="unClassification")


class InventorySearchItem(BaseAlbertModel):
    id: str = Field(alias="albertId")
    name: str = Field(default="")
    description: str = Field(default="")
    category: InventoryCategory
    unit: InventoryUnitCategory
    lots: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    pictogram: list[InventorySearchPictogramItem] = Field(default_factory=list)
    # missing element implies none on hand
    inventory_on_hand: float = Field(default=0.0, alias="inventoryOnHand")
    sds: InventorySearchSDSItem | None = Field(default=None, alias="SDS")


class MergeInventory(BaseAlbertModel):
    parent_id: InventoryId = Field(alias="parentId")
    child_inventories: list[dict[str, InventoryId]] = Field(alias="ChildInventories")
    modules: list[str] | None = Field(default=None)
