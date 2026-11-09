"""Quantity descriptors shared by design resources.

A descriptor names a quantity inline (an ingredient amount, a label fraction, a
parameter value, or a property aggregation), and is shared by design resources such as
the feature masks of design model configs.

The descriptor models are strict, so what a caller sends (and any schema generated from
it) names exactly the fields and kinds the service accepts. Records read back from the service
parse through the lenient variants instead (``QuantityOperandRead``), which keep fields
and kinds a newer service version adds.
"""

import sys
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_serializer

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import InventoryId

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class AggregationBasis(StrEnum):
    """How an aggregation combines the member values of its scope."""

    MEAN = "mean"
    SUM = "sum"


class TypedDesignModel(BaseAlbertModel):
    """Base for ``type``-discriminated models, keeping ``type`` when unset fields are dropped.

    Requests are serialized with ``exclude_unset=True``, which would drop a defaulted
    ``type`` discriminator, and the service cannot read an entry that does not say which
    kind it is. Re-adding it here covers an entry nested in an operation.
    """

    model_config = ConfigDict(extra="forbid")

    @model_serializer(mode="wrap")
    def _keep_type_discriminator(self, handler):
        """Re-add the defaulted ``type`` field after standard serialization."""
        return {"type": self.type, **handler(self)}


class IngredientAmountOperand(TypedDesignModel):
    """The amount of one ingredient in the formulation."""

    type: Literal["ingredientAmount"] = "ingredientAmount"
    """Descriptor kind; fixed to ``ingredientAmount``."""

    ingredient: InventoryId
    """The inventory ID (format ``INV...``) of the ingredient."""


class LabelFractionOperand(TypedDesignModel):
    """The summed fraction of a label's member ingredients."""

    type: Literal["labelFraction"] = "labelFraction"
    """Descriptor kind; fixed to ``labelFraction``."""

    label: str
    """A platform tag (format ``TAG...``) or a local label key (``local:...``)."""


class ParameterOperand(TypedDesignModel):
    """The value of one parameter, addressed by its composite key."""

    type: Literal["parameter"] = "parameter"
    """Descriptor kind; fixed to ``parameter``."""

    parameter: str
    """The composite parameter key, ``{DAT|PRG}#PRM[#UNI]``."""


class PropertyAggregationOperand(TypedDesignModel):
    """An aggregation of one inventory property over a scope of ingredients."""

    type: Literal["propertyAggregation"] = "propertyAggregation"
    """Descriptor kind; fixed to ``propertyAggregation``."""

    basis: AggregationBasis
    """How the member values combine: ``mean`` or ``sum``."""

    property: str
    """Name of the aggregated inventory property."""

    label: str | None = Field(default=None)
    """Restrict the aggregation to a label's members. Omit to scope to all ingredients."""

    impute: bool | float | None = Field(default=None)
    """How missing property values are handled: ``True`` fills the column mean, a number
    fills that constant, ``False`` fails on a sparse table. Omit to leave it unstated."""


QuantityOperand = Annotated[
    IngredientAmountOperand | LabelFractionOperand | ParameterOperand | PropertyAggregationOperand,
    Field(discriminator="type"),
]
"""A quantity descriptor: an ingredient amount, a label fraction, a parameter, or a
property aggregation."""


class UnknownDescriptor(BaseAlbertModel):
    """A descriptor or mask entry of a kind this SDK version does not know yet.

    Only appears in records read from the service. An entry written by a newer service
    version parses into this model instead of failing, and keeps every key it carried.
    Requests never accept it.
    """

    model_config = ConfigDict(extra="allow")

    type: str
    """The kind the service reported."""


class _ReadIngredientAmountOperand(IngredientAmountOperand):
    """An ingredient-amount descriptor read from the service, keeping unknown fields."""

    model_config = ConfigDict(extra="allow")


class _ReadLabelFractionOperand(LabelFractionOperand):
    """A label-fraction descriptor read from the service, keeping unknown fields."""

    model_config = ConfigDict(extra="allow")


class _ReadParameterOperand(ParameterOperand):
    """A parameter descriptor read from the service, keeping unknown fields."""

    model_config = ConfigDict(extra="allow")


class _ReadPropertyAggregationOperand(PropertyAggregationOperand):
    """A property-aggregation descriptor read from the service, keeping unknown fields."""

    model_config = ConfigDict(extra="allow")


QuantityOperandRead = Annotated[
    Annotated[
        _ReadIngredientAmountOperand
        | _ReadLabelFractionOperand
        | _ReadParameterOperand
        | _ReadPropertyAggregationOperand,
        Field(discriminator="type"),
    ]
    | UnknownDescriptor,
    Field(union_mode="left_to_right"),
]
"""A quantity descriptor as read from the service. A known kind parses to its descriptor
model (an instance of ``IngredientAmountOperand``, ``LabelFractionOperand``,
``ParameterOperand`` or ``PropertyAggregationOperand``) and keeps fields this version
does not model; an unknown kind parses to ``UnknownDescriptor``."""
