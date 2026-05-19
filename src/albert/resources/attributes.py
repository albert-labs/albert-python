from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import AttributeId, DataColumnId, ParameterId, UnitId
from albert.core.shared.models.base import BaseResource, EntityLink, EntityLinkWithName
from albert.resources.parameter_groups import DataType, EnumValidationValue, Operator


class AttributeCategory(str, Enum):
    """Category of an attribute."""

    PROPERTY = "Property"


class AttributeScope(str, Enum):
    """Scope used when fetching or deleting attribute values."""

    SELF = "SELF"
    LOT = "LOT"
    ALL = "ALL"


class ValidationItem(BaseAlbertModel):
    """A validation rule for an attribute.

    Uses the same DataType and Operator enums as parameter groups, but min/max
    are float (not str) because the attributes API sends numeric values.
    """

    datatype: DataType | None = None
    min: float | None = None
    max: float | None = None
    value: float | list[EnumValidationValue] | None = None
    operator: Operator | None = None

    @field_validator("datatype", mode="before")
    @classmethod
    def normalize_datatype(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return DataType(v.lower())
            except ValueError:
                return None
        return v


class AttributeParameterItem(BaseAlbertModel):
    """A parameter reference within an attribute definition."""

    id: ParameterId
    name: str | None = None
    category: str | None = None
    value: str | dict | None = None
    unit: EntityLinkWithName | None = None
    unit_id: UnitId | None = Field(None, alias="unitId")


class Attribute(BaseResource):
    """Represents a centralized attribute definition."""

    id: AttributeId | None = Field(None, alias="albertId")
    reference_name: str | None = Field(None, alias="referenceName")
    full_name: str | None = Field(None, alias="fullName")
    name_override: bool | None = Field(None, alias="nameOverride")
    datacolumn: EntityLinkWithName | None = None
    datacolumn_id: DataColumnId | None = Field(None, alias="datacolumnId")
    unit: EntityLinkWithName | None = None
    unit_id: UnitId | None = Field(None, alias="unitId")
    workflow: EntityLink | None = None
    validation: list[ValidationItem] | None = None
    category: AttributeCategory | None = None
    parameters: list[AttributeParameterItem] | None = None

    @field_validator("parameters", mode="before")
    @classmethod
    def coerce_parameters(cls, v: Any) -> Any:
        if isinstance(v, dict) and "values" in v:
            return v["values"]
        return v


class AttributeSearchItem(BaseAlbertModel):
    """A lightweight attribute result returned by the search endpoint."""

    id: AttributeId = Field(alias="albertId")
    name: str | None = None
    datacolumn_id: str | None = Field(None, alias="datacolumnId")
    datacolumn_name: str | None = Field(None, alias="datacolumnName")
    unit_name: str | None = Field(None, alias="unitName")
    parameters: list[dict] | None = None


# --- Attribute value models ---


class AttributeValueRange(BaseAlbertModel):
    """A numeric range constraint for a reference value."""

    min: float | None = None
    max: float | None = None
    comparison_operator: str | None = Field(None, alias="comparisonOperator")


class AttributeValue(BaseAlbertModel):
    """A reference value to assign to a parent entity for a given attribute."""

    attribute_id: AttributeId = Field(alias="attributeId")
    reference_value: str | float | None = Field(None, alias="referenceValue")
    range: AttributeValueRange | None = None


class AttributeDefinition(BaseAlbertModel):
    """Read-only embed of attribute metadata within a values response.

    Distinct from Attribute: uses ``name`` (not ``referenceName``) and
    ``prmCount`` (count only, not the full parameters list).
    """

    name: str
    full_name: str = Field(alias="fullName")
    datacolumn: EntityLinkWithName
    category: AttributeCategory
    unit: EntityLinkWithName | None = None
    workflow: EntityLink
    validation: list[ValidationItem]
    prm_count: int = Field(alias="prmCount")


class AttributeValuesResponseItem(BaseAlbertModel):
    """A single attribute value entry within a values response."""

    id: AttributeId = Field(alias="albertId")
    attribute_definition: AttributeDefinition = Field(alias="attributeDefinition")
    reference_value: str | float | None = Field(None, alias="referenceValue")
    range: AttributeValueRange | None = None


class AttributeValuesResponse(BaseAlbertModel):
    """Attribute values for a single parent entity."""

    parent_id: str = Field(alias="parentId")
    attributes: list[AttributeValuesResponseItem]
