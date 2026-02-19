from __future__ import annotations

from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


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


class ParameterCategory(str, Enum):
    """
    Enumeration of target parameter categories.

    Attributes
    ----------
    NORMAL : str
        A normal parameter.
    SPECIAL : str
        A special parameter (Equipment, Consumeable, etc.).
    """

    NORMAL = "normal"
    SPECIAL = "special"


class TargetParameter(BaseAlbertModel):
    """
    Represents a parameter mapping for a target.

    Attributes
    ----------
    id : str
        The parameter ID.
    category : ParameterCategory
        The parameter category.
    unit_id : str | None
        The unit ID for this parameter.
    value : str | float | None
        The parameter value.
    sequence : str
        The parameter sequence.
    """

    id: str
    category: ParameterCategory
    unit_id: str | None = Field(default=None, alias="unitId")
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
    data_template_id : str
        The ID of the associated data template.
    data_column_id : str
        The ID of the associated data column.
    name : str
        The name of the target.
    type : TargetType
        The type of target.
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
    """

    id: str | None = Field(default=None)
    data_template_id: str = Field(alias="dataTemplateId")
    data_column_id: str = Field(alias="dataColumnId")
    name: str
    type: TargetType
    unit_id: str | None = Field(default=None, alias="unitId")
    parameters: list[TargetParameter] | None = Field(default=None)
    validation: list[dict] | None = Field(default=None)
    target_value: TargetValue = Field(alias="targetValue")
    is_required: bool = Field(alias="isRequired")
