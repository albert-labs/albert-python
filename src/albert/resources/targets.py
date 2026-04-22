from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DataColumnId,
    DataTemplateId,
    ParameterGroupId,
    ParameterId,
    UnitId,
)
from albert.core.shared.models.base import BaseResource
from albert.resources.parameter_groups import ParameterCategory


class TargetType(str, Enum):
    """
    Enumeration of target types.

    Attributes
    ----------
    PERFORMANCE : str
        A performance target.
    """

    PERFORMANCE = "performance"


class TargetOperator(str, Enum):
    """
    Enumeration of target value comparison operators.

    Attributes
    ----------
    EQ : str
        Equal to.
    GTE : str
        Greater than or equal to.
    LTE : str
        Less than or equal to.
    BETWEEN : str
        Between a range.
    IN_SET : str
        In a set of values.
    """

    EQ = "eq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    BETWEEN = "between"
    IN_SET = "in-set"


class TargetParameter(BaseAlbertModel):
    """
    Represents a parameter value at which a target is measured.

    Attributes
    ----------
    id : str
        The parameter ID.
    parameter_group_id : str | None
        The parameter group ID.
    category : ParameterCategory
        The parameter category.
    unit_id : str | None
        The unit ID for this parameter.
    value : str | float | None
        The parameter value.
    sequence : str
        The parameter sequence.
    """

    id: ParameterId
    parameter_group_id: ParameterGroupId | None = Field(default=None, alias="parameterGroupId")
    category: ParameterCategory
    unit_id: UnitId | None = Field(default=None, alias="unitId")
    value: str | float | None = Field(default=None)
    sequence: str


class TargetRangeValue(BaseAlbertModel):
    """
    Represents a range value for a target (used with the 'between' operator).

    Attributes
    ----------
    min : float
        The minimum value.
    max : float
        The maximum value.
    """

    min: float
    max: float


class TargetValue(BaseAlbertModel):
    """
    Represents the target value constraint.

    Attributes
    ----------
    operator : TargetOperator
        The comparison operator.
    value : TargetRangeValue | str | float | list
        The target value. Can be a range, single value, or list of values.
    """

    operator: TargetOperator
    value: TargetRangeValue | str | float | list


class Target(BaseResource):
    """
    Represents a target entity.

    Attributes
    ----------
    id : str | None
        The unique identifier of the target. Set when retrieved from Albert.
    name : str
        The name of the target.
    type : TargetType
        The type of target.
    data_template_id : str
        The ID of the associated data template.
    data_column_id : str
        The ID of the associated data column.
    unit_id : str | None
        The unit ID for this target.
    parameters : list[TargetParameter] | None
        Parameter mappings for the target.
    validation : list[dict] | None
        Validation rules for the target value.
    target_value : TargetValue
        The target value constraint.
    is_required : bool
        Whether this target is required.
    validation : list[dict] | None
        Validation rules for the target.
    """

    id: str | None = Field(default=None)
    name: str
    type: TargetType
    data_template_id: DataTemplateId = Field(alias="dataTemplateId")
    data_column_id: DataColumnId = Field(alias="dataColumnId")
    unit_id: UnitId | None = Field(default=None, alias="unitId")
    parameters: list[TargetParameter] | None = Field(default=None)
    target_value: TargetValue = Field(alias="targetValue")
    is_required: bool = Field(alias="isRequired")
    validation: list[dict] | None = Field(default=None)


class AggregateBy(str, Enum):
    """Aggregation dimension for target line data queries.

    Attributes
    ----------
    MEASUREMENT : str
        Aggregate by individual measurement.
    WORKFLOW : str
        Aggregate by workflow run.
    INVENTORY : str
        Aggregate by inventory item.
    LOT : str
        Aggregate by lot.
    """

    MEASUREMENT = "measurement"
    WORKFLOW = "workflow"
    INVENTORY = "inventory"
    LOT = "lot"


class TargetLineBetweenValue(BaseAlbertModel):
    """Target value for a 'between' range constraint.

    Attributes
    ----------
    operator : Literal["between"]
        The comparison operator.
    min : float
        Lower bound of the range.
    max : float
        Upper bound of the range.
    """

    operator: Literal["between"]
    min: float
    max: float


class TargetLineScalarValue(BaseAlbertModel):
    """Target value for a scalar comparison constraint.

    Attributes
    ----------
    operator : Literal["lt", "lte", "gt", "gte", "eq"]
        The comparison operator.
    value : float
        The scalar threshold.
    """

    operator: Literal["lt", "lte", "gt", "gte", "eq"]
    value: float


class TargetLineSetValue(BaseAlbertModel):
    """Target value for an in-set constraint.

    Attributes
    ----------
    operator : Literal["in-set"]
        The comparison operator.
    values : list[str | float]
        The set of allowed values.
    """

    operator: Literal["in-set"]
    values: list[str | float]


TargetLineValue = Annotated[
    TargetLineBetweenValue | TargetLineScalarValue | TargetLineSetValue,
    Field(discriminator="operator"),
]
"""Discriminated union of target line value shapes, keyed on ``operator``."""


class TargetLineData(BaseAlbertModel):
    """Response payload for a target line data request.

    Attributes
    ----------
    target_id : str
        The target ID.
    target_value : TargetLineValue
        The target constraint and its operator.
    data_points : list[float]
        The data points associated with this target.
    """

    target_id: str = Field(alias="targetId")
    target_value: TargetLineValue = Field(alias="targetValue")
    data_points: list[float] = Field(alias="dataPoints")
