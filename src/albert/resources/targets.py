from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DataColumnId,
    DataTemplateId,
    ParameterGroupId,
    ParameterId,
    ProjectId,
    UnitId,
)
from albert.core.shared.models.base import BaseResource
from albert.resources.parameter_groups import ParameterCategory


class ComparisonOperator(str, Enum):
    """How a measured value is compared against a target value.

    Attributes
    ----------
    EQ : str
        Equal to the target value.
    GT : str
        Strictly greater than the target value.
    GTE : str
        Greater than or equal to the target value.
    LT : str
        Strictly less than the target value.
    LTE : str
        Less than or equal to the target value.
    BETWEEN : str
        Within an inclusive range; pairs with a [`NumericRange`][albert.resources.targets.NumericRange] value.
    IN_SET : str
        Among a set of allowed values; pairs with a list value.
    """

    EQ = "eq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    BETWEEN = "between"
    IN_SET = "in-set"


class NumericRange(BaseAlbertModel):
    """An inclusive numeric range, used with the ``between`` operator.

    Attributes
    ----------
    min : float
        The lower bound of the range.
    max : float
        The upper bound of the range.
    """

    min: float
    max: float


class Criterion(BaseAlbertModel):
    """A target value constraint: an operator paired with a value to compare against.

    Attributes
    ----------
    operator : ComparisonOperator
        How the measured value is compared against ``value``.
    value : NumericRange or str or float or list
        The value being compared against. Use a [`NumericRange`][albert.resources.targets.NumericRange] with the
        ``between`` operator, a list with the ``in-set`` operator, or a single
        number/string for the scalar operators.
    """

    operator: ComparisonOperator
    value: NumericRange | str | float | list


class TargetType(str, Enum):
    """The kind of target.

    Attributes
    ----------
    PERFORMANCE : str
        A performance target: a desired value or range for a measured property.
    """

    PERFORMANCE = "performance"


class TargetParameter(BaseAlbertModel):
    """A parameter condition under which a target is measured.

    Targets can be scoped to specific parameter settings (for example, "at 25 °C").
    Each ``TargetParameter`` names a parameter and, optionally, the value it must
    take for the target to apply.

    Attributes
    ----------
    id : str
        The parameter ID (format ``PRM...``).
    parameter_group_id : str or None
        The parameter group ID (format ``PRG...``) this parameter belongs to.
    category : ParameterCategory
        The category of the parameter.
    unit_id : str or None
        The unit ID (format ``UNI...``) for this parameter's value.
    value : Criterion or None
        The value condition. Accepts an operator/value pair using one of the
        operators ``eq``, ``gte``, ``lte``, ``between``, ``in-set``.
        For ``between``, the value must be ``{"min": ..., "max": ...}``.
        For ``in-set``, the value must be a list.
        Legacy bare scalars (numeric or string) are coerced on read: a numeric
        scalar becomes ``{"operator": "eq", "value": <n>}`` and a string becomes
        ``{"operator": "in-set", "value": [<s>]}``.
    sequence : str
        The ordering position of this parameter.
    """

    id: ParameterId
    parameter_group_id: ParameterGroupId | None = Field(default=None, alias="parameterGroupId")
    category: ParameterCategory
    unit_id: UnitId | None = Field(default=None, alias="unitId")
    value: Criterion | None = Field(default=None)
    sequence: str

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_legacy_value(cls, v: object) -> object:
        # Tolerant reader: legacy parameter values stored a bare scalar before the
        # operator/value-pair migration (lazy backfill may not have run yet).
        if v is None:
            return v
        if isinstance(v, dict | Criterion):
            return v
        if isinstance(v, bool):  # guard: bool is a subclass of int
            return {"operator": "in-set", "value": [v]}
        if isinstance(v, int | float):
            return {"operator": "eq", "value": v}
        if isinstance(v, str):
            return {"operator": "in-set", "value": [v]}
        return v


class Target(BaseResource):
    """A desired value or acceptable range for a measured property (🧪Beta).

    A target links a data template and data column (the property being measured)
    to a target value constraint, optionally scoped to a project and to specific
    parameter conditions. Managed through
    [`TargetCollection`][albert.collections.targets.TargetCollection] (``client.targets``).

    Attributes
    ----------
    id : str or None
        The Albert ID of the target (format ``TAR...``). Set when the target is
        retrieved from or created in Albert.
    name : str
        The name of the target.
    type : TargetType
        The kind of target (e.g. performance).
    parent_id : str or None
        The ID of the project (format ``PRO...``) this target belongs to. When
        set, the target inherits its ACL (access control) policy from that project.
    data_template_id : str
        The ID of the data template (format ``DAT...``) whose property is targeted.
    data_column_id : str
        The ID of the data column (format ``DAC...``) being targeted.
    unit_id : str or None
        The unit ID (format ``UNI...``) for the target value.
    parameters : list[TargetParameter] or None
        Parameter conditions under which the target applies.
    target_value : Criterion
        The target value constraint (operator plus value).
    is_required : bool
        Whether meeting this target is required.
    validation : list[dict] or None
        Validation rules applied to the target value.

    !!! example
        ```python
        from albert.resources.targets import (
            Target,
            TargetType,
            Criterion,
            ComparisonOperator,
        )
        target = Target(
            name="Viscosity spec",
            type=TargetType.PERFORMANCE,
            data_template_id="DAT1",
            data_column_id="DAC1",
            target_value=Criterion(operator=ComparisonOperator.BETWEEN, value={"min": 10, "max": 20}),
            is_required=True,
        )
        ```
    """

    id: str | None = Field(default=None)
    name: str
    type: TargetType
    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    data_template_id: DataTemplateId = Field(alias="dataTemplateId")
    data_column_id: DataColumnId = Field(alias="dataColumnId")
    unit_id: UnitId | None = Field(default=None, alias="unitId")
    parameters: list[TargetParameter] | None = Field(default=None)
    target_value: Criterion = Field(alias="targetValue")
    is_required: bool = Field(alias="isRequired")
    validation: list[dict] | None = Field(default=None)
