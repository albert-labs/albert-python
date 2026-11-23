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

from pydantic import ConfigDict, Field, field_validator, model_serializer

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

    # A lenient read instance (a subclass) passed into a request is checked against this
    # strict model again, so content this version does not model is refused, not dropped.
    model_config = ConfigDict(extra="forbid", revalidate_instances="subclass-instances")

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


class PropertyAggregation(BaseAlbertModel):
    """An aggregation of one inventory property over a scope of ingredients.

    The body of a ``property`` constraint and of each side of a ``propertyRatio``
    constraint. The ``propertyAggregation`` descriptor carries the same fields.
    """

    model_config = ConfigDict(extra="forbid", revalidate_instances="subclass-instances")

    basis: AggregationBasis
    """How the member values combine: ``mean`` or ``sum``."""

    property: str
    """Name of the aggregated inventory property."""

    label: str | None = Field(default=None)
    """Restrict the aggregation to a label's members. Omit to scope to all ingredients."""

    impute: bool | float | None = Field(default=None)
    """How missing property values are handled: ``True`` fills the column mean, a number
    fills that constant, ``False`` fails on a sparse table. Omit to leave it unstated."""

    use_reciprocal: bool | None = Field(default=None, alias="useReciprocal")
    """Aggregate the reciprocal of the property instead. Omit to leave it unstated."""


class PropertyAggregationOperand(TypedDesignModel, PropertyAggregation):
    """An aggregation of one inventory property over a scope of ingredients."""

    type: Literal["propertyAggregation"] = "propertyAggregation"
    """Descriptor kind; fixed to ``propertyAggregation``."""


class LabelCountOperand(TypedDesignModel):
    """How many of a label's member ingredients a formulation contains. Constraints only."""

    type: Literal["labelCount"] = "labelCount"
    """Descriptor kind; fixed to ``labelCount``."""

    label: str | None = Field(default=None)
    """Count only this label's members (``TAG...`` or ``local:...``). Omit to count every
    ingredient."""


class PriceAggregationOperand(TypedDesignModel):
    """An aggregation of ingredient price over the formulation. Constraints only."""

    type: Literal["priceAggregation"] = "priceAggregation"
    """Descriptor kind; fixed to ``priceAggregation``."""

    basis: AggregationBasis
    """How the member prices combine. Only ``sum`` can be a weighted-sum term."""

    location: str | None = Field(default=None)
    """Pricing location. Omit for any location."""

    impute: bool | float | None = Field(default=None)
    """How missing prices are handled, as on a property aggregation."""


class ConstantOperand(TypedDesignModel):
    """A constant term of a weighted sum. Constraints only."""

    type: Literal["constant"] = "constant"
    """Descriptor kind; fixed to ``constant``."""

    value: float
    """The constant."""


QuantityOperand = Annotated[
    IngredientAmountOperand | LabelFractionOperand | ParameterOperand | PropertyAggregationOperand,
    Field(discriminator="type"),
]
"""A quantity descriptor: an ingredient amount, a label fraction, a parameter, or a
property aggregation."""


_DESCRIPTOR_KINDS = frozenset(
    model.model_fields["type"].default
    for model in (
        IngredientAmountOperand,
        LabelFractionOperand,
        ParameterOperand,
        PropertyAggregationOperand,
    )
)


class UnknownDescriptor(BaseAlbertModel):
    """A descriptor or mask entry of a kind this SDK version does not know yet.

    Only appears in records read from the service. An entry written by a newer service
    version parses into this model instead of failing, and keeps every key it carried.
    Requests never accept it.
    """

    model_config = ConfigDict(extra="allow")

    type: str
    """The kind the service reported."""

    @field_validator("type")
    @classmethod
    def _only_unknown_kinds(cls, kind: str) -> str:
        """Refuse a kind this version models: a malformed entry of it is an error."""
        if kind in _DESCRIPTOR_KINDS:
            raise ValueError(f"{kind!r} entry does not match its schema")
        return kind


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


class _ReadPropertyAggregation(PropertyAggregation):
    """A property aggregation read from the service, keeping unknown fields."""

    model_config = ConfigDict(extra="allow")


class _ReadLabelCountOperand(LabelCountOperand):
    """A label-count descriptor read from the service, keeping unknown fields."""

    model_config = ConfigDict(extra="allow")


class _ReadPriceAggregationOperand(PriceAggregationOperand):
    """A price-aggregation descriptor read from the service, keeping unknown fields."""

    model_config = ConfigDict(extra="allow")


class _ReadConstantOperand(ConstantOperand):
    """A constant descriptor read from the service, keeping unknown fields."""

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


ConstraintOperand = Annotated[
    IngredientAmountOperand
    | LabelFractionOperand
    | LabelCountOperand
    | ParameterOperand
    | PropertyAggregationOperand
    | PriceAggregationOperand
    | ConstantOperand,
    Field(discriminator="type"),
]
"""A constraint operand: any quantity descriptor, plus a label count, a price aggregation
or a constant. Which kinds a constraint accepts is checked when the constraint is
applied, and a kind the service does not support yet is refused there
(``unsupported_operand``)."""


_CONSTRAINT_OPERAND_KINDS = frozenset(
    model.model_fields["type"].default
    for model in (
        IngredientAmountOperand,
        LabelFractionOperand,
        LabelCountOperand,
        ParameterOperand,
        PropertyAggregationOperand,
        PriceAggregationOperand,
        ConstantOperand,
    )
)


class UnknownConstraintOperand(UnknownDescriptor):
    """A constraint operand of a kind this SDK version does not know yet.

    Only appears in design spaces read from the service, and keeps every key it carried.
    Requests never accept it.
    """

    @field_validator("type")
    @classmethod
    def _only_unknown_kinds(cls, kind: str) -> str:
        """Refuse a kind this version models: a malformed operand of it is an error."""
        if kind in _CONSTRAINT_OPERAND_KINDS:
            raise ValueError(f"{kind!r} operand does not match its schema")
        return kind


ConstraintOperandRead = Annotated[
    Annotated[
        _ReadIngredientAmountOperand
        | _ReadLabelFractionOperand
        | _ReadLabelCountOperand
        | _ReadParameterOperand
        | _ReadPropertyAggregationOperand
        | _ReadPriceAggregationOperand
        | _ReadConstantOperand,
        Field(discriminator="type"),
    ]
    | UnknownConstraintOperand,
    Field(union_mode="left_to_right"),
]
"""A constraint operand as read from the service. A known kind parses to its descriptor
model and keeps fields this version does not model; an unknown kind parses to
``UnknownConstraintOperand``."""


class LinearTerm(BaseAlbertModel):
    """One ``coefficient * operand`` term of a weighted sum."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="subclass-instances")

    coefficient: float
    """The weight of the operand."""

    operand: ConstraintOperand
    """The quantity the coefficient weights."""


class _ReadLinearTerm(LinearTerm):
    """A weighted-sum term read from the service, keeping unknown fields and kinds."""

    model_config = ConfigDict(extra="allow")

    operand: ConstraintOperandRead
    """The quantity the coefficient weights."""
