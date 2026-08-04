from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import AttributeId, DataColumnId, ParameterId, UnitId
from albert.core.shared.models.base import BaseResource, EntityLink, EntityLinkWithName
from albert.resources.parameter_groups import DataType, EnumValidationValue, Operator


class AttributeCategory(str, Enum):
    """Category of an inventory reference attribute.

    ``Property``: inventory reference properties tied to a data column (e.g.
    viscosity, pH) for use in worksheets and inventory details.
    """

    PROPERTY = "Property"


class AttributeScope(str, Enum):
    """Scope for reading or deleting reference values on a parent entity.

    Used with [`get_values`][albert.collections.attributes.AttributeCollection.get_values],
    [`delete_values`][albert.collections.attributes.AttributeCollection.delete_values],
    and [`clear_values`][albert.collections.attributes.AttributeCollection.clear_values].
    Inventory-level values are the source of truth for worksheet lookups; lot-level
    values support lot-specific overrides where enabled.

    ``SELF``: only the given ``parent_id``.
    ``LOT``: lots under an inventory ``parent_id`` (inventory parents only).
    ``ALL``: the parent and all of its child lots.
    """

    SELF = "SELF"
    LOT = "LOT"
    ALL = "ALL"


class ValidationItem(BaseAlbertModel):
    """Typed validation rule for an attribute definition.

    Declares the allowed datatype (`number`, `string`, or `enum`) and optional
    constraints. Numeric attributes may include min/max and an operator; enum
    attributes list allowed options in ``value``. Values assigned via
    [`add_values`][albert.collections.attributes.AttributeCollection.add_values]
    must conform to these rules.
    """

    datatype: DataType | None = None
    """Allowed value type: ``number``, ``string``, or ``enum``."""

    min: float | None = None
    """Minimum allowed numeric value (with ``between`` or range operators)."""

    max: float | None = None
    """Maximum allowed numeric value (with ``between`` or range operators)."""

    value: float | list[EnumValidationValue] | None = None
    """Enum allowed options, or a scalar constraint depending on ``datatype``."""

    operator: Operator | None = None
    """Comparison operator for numeric validation (e.g. ``between``)."""

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
    """A parameter setpoint embedded in an attribute definition.

    Parameter setpoints distinguish otherwise similar properties (e.g.
    Temperature = 25°C for "Viscosity @ 25°C"). Together with the data column
    and unit, they form the uniqueness key for an attribute definition.
    """

    id: ParameterId
    """Parameter ID."""

    name: str | None = None
    """Parameter display name."""

    category: str | None = None
    """Parameter category."""

    value: str | dict | None = None
    """Setpoint value for this parameter."""

    unit: EntityLinkWithName | None = None
    """Unit for the setpoint, when applicable."""

    unit_id: UnitId | None = Field(None, alias="unitId")
    """Unit ID for the setpoint."""


class Attribute(BaseResource):
    """An inventory reference attribute definition.

    Defines a reusable property template (e.g. "Viscosity @ 25°C") that can be
    assigned to many inventory items and lots. Each definition links a
    [`DataColumn`][albert.resources.data_columns.DataColumn], optional parameter
    setpoints, an optional unit, and typed validation. This is separate from a
    *reference value*: the per-parent measurement stored with
    [`add_values`][albert.collections.attributes.AttributeCollection.add_values].

    Replaces inline property definitions from the deprecated Inventory Specs API.
    Attributes are identified by Attribute ID (format ``ATR...``).
    """

    id: AttributeId | None = Field(None, alias="albertId")
    """Attribute ID (format ``ATR...``)."""

    reference_name: str | None = Field(None, alias="referenceName")
    """Unique display name. Default pattern: ``{DataColumn} | {parameter setpoints}``."""

    full_name: str | None = Field(None, alias="fullName")
    """Localized full name for display."""

    name_override: bool | None = Field(None, alias="nameOverride")
    """Whether ``reference_name`` was manually set instead of the default pattern."""

    datacolumn: EntityLinkWithName | None = None
    """Linked data column (the property being referenced, e.g. Viscosity)."""

    datacolumn_id: DataColumnId | None = Field(None, alias="datacolumnId")
    """Data column ID when creating an attribute."""

    unit: EntityLinkWithName | None = None
    """Unit for numeric reference values (e.g. cP). Immutable after first assignment."""

    unit_id: UnitId | None = Field(None, alias="unitId")
    """Unit ID when creating an attribute."""

    workflow: EntityLink | None = None
    """Workflow derived from parameter setpoints (order-agnostic)."""

    validation: list[ValidationItem] | None = None
    """Datatype and constraints for values assigned to this attribute."""

    category: AttributeCategory | None = None
    """Attribute category (currently ``Property`` for inventory references)."""

    parameters: list[AttributeParameterItem] | None = None
    """Parameter setpoints that define measurement conditions for this attribute."""

    @field_validator("parameters", mode="before")
    @classmethod
    def coerce_parameters(cls, v: Any) -> Any:
        if isinstance(v, dict) and "values" in v:
            return v["values"]
        return v


class AttributeSearchItem(BaseAlbertModel):
    """A lightweight attribute hit from [`search`][albert.collections.attributes.AttributeCollection.search]."""

    id: AttributeId = Field(alias="albertId")
    """Attribute ID (format ``ATR...``)."""

    name: str | None = None
    """Display name of the attribute."""

    datacolumn_id: str | None = Field(None, alias="datacolumnId")
    """Linked data column ID."""

    datacolumn_name: str | None = Field(None, alias="datacolumnName")
    """Linked data column name."""

    unit_name: str | None = Field(None, alias="unitName")
    """Unit name for numeric attributes."""

    parameters: list[dict] | None = None
    """Summary of linked parameter setpoints."""


# --- Attribute value models ---


class AttributeValueRange(BaseAlbertModel):
    """Numeric min/max bounds for a reference value.

    Used when an attribute allows a target value plus an acceptable range
    (legacy Specs ``min``/``max`` semantics).
    """

    min: float | None = None
    """Minimum bound."""

    max: float | None = None
    """Maximum bound."""

    comparison_operator: str | None = Field(None, alias="comparisonOperator")
    """How ``min`` and ``max`` constrain the value."""


class AttributeValue(BaseAlbertModel):
    """A reference value to assign on a parent entity for one attribute.

    Pass to [`add_values`][albert.collections.attributes.AttributeCollection.add_values].
    The value must match the attribute datatype (numeric, enum option, or string).
    Values belong only to the given ``parent_id`` (one inventory item or lot).
    """

    attribute_id: AttributeId = Field(alias="attributeId")
    """Attribute definition to set a value for."""

    reference_value: str | float | None = Field(None, alias="referenceValue")
    """Assigned value (target for numeric types, selected option for enum)."""

    range: AttributeValueRange | None = None
    """Optional numeric min/max bounds alongside ``reference_value``."""


class AttributeDefinition(BaseAlbertModel):
    """Read-only attribute metadata embedded in a values response.

    Distinct from [`Attribute`][albert.resources.attributes.Attribute]: uses ``name``
    (not ``referenceName``) and reports ``prmCount`` instead of the full parameters list.
    """

    name: str
    """Attribute display name."""

    full_name: str = Field(alias="fullName")
    """Localized full name."""

    datacolumn: EntityLinkWithName
    """Data column this reference measures."""

    category: AttributeCategory
    """Attribute category."""

    unit: EntityLinkWithName | None = None
    """Unit for numeric values."""

    workflow: EntityLink
    """Workflow for parameter setpoints."""

    validation: list[ValidationItem]
    """Validation rules for assigned values."""

    prm_count: int = Field(alias="prmCount")
    """Number of parameter setpoints on the definition."""


class AttributeValuesResponseItem(BaseAlbertModel):
    """One attribute's reference value on a parent entity."""

    id: AttributeId = Field(alias="albertId")
    """Attribute ID."""

    attribute_definition: AttributeDefinition = Field(alias="attributeDefinition")
    """Metadata for the attribute definition."""

    reference_value: str | float | None = Field(None, alias="referenceValue")
    """Assigned reference value."""

    range: AttributeValueRange | None = None
    """Optional numeric min/max bounds."""


class AttributeValuesResponse(BaseAlbertModel):
    """Reference values for a single parent entity (inventory item, lot, etc.)."""

    parent_id: str = Field(alias="parentId")
    """Parent entity ID (e.g. ``INVA123`` or ``LOT456``)."""

    attributes: list[AttributeValuesResponseItem]
    """Reference values assigned on this parent."""
