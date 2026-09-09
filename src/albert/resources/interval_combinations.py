from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.resources.worker_jobs import WorkerJob


# TODO: GET /tasks/{id}/blocks/{blockId}/combinations also returns
# parentWorkflowId on the response envelope (not per item). Expose it
# if that id is not already available from the task/block read path.
class IntervalCombinationItem(BaseAlbertModel):
    """One child-workflow interval combination on a task block.

    Returned by
    [`get_block_combinations`][albert.collections.tasks.TaskCollection.get_block_combinations].
    Use that method rather than any combinations array embedded on a task or block:
    the embedded array is empty once the block has 500 or more combinations.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        combo = next(
            client.tasks.get_block_combinations(task_id="TASFOR1", block_id="BLK1", max_items=1)
        )
        combo.id
        # 'WFL999'
        combo.interval_barcode
        # 'OhI8ap0HY'
        ```
    """

    id: str | None = None
    """The child workflow id for this combination (format ``WFL...``)."""

    name: str | None = None
    """Display name of the combination (parameter names and values)."""

    interval_barcode: str | None = Field(default=None, alias="intervalBarcode")
    """Case-sensitive barcode for the combination. Serialized as ``intervalBarcode``."""

    interval_row_key: str | None = Field(default=None, alias="intervalRowKey")
    """Legacy ROW-chain key (e.g. ``ROW3XROW7``). Serialized as ``intervalRowKey``."""


class RuleOperator(str, Enum):
    """Comparison operator used to evaluate a rule condition against a parameter value.

    Note: Distinct from `parameter_groups.Operator` (which uses ``neq`` and has
    ``between``) and `targets.ComparisonOperator` (which lacks ``ne`` and has
    ``in_set``). Defined resource-specifically per AGENTS.md exact-match rule.
    """

    GT = "gt"
    LT = "lt"
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"
    NE = "ne"


class OverrideAction(str, Enum):
    """Action to apply for a combination override."""

    SKIP = "skip"
    UNSKIP = "unskip"


class RuleCondition(BaseAlbertModel):
    """A single condition within an exclusion rule.

    References a parameter group or data template, a parameter, a parameter row,
    and a comparison operator and threshold value.
    """

    parameter_group_id: str = Field(alias="prgId")
    """Parameter group or data template ID (format ``PRG...`` or ``DAT...``)."""

    parameter_id: str = Field(alias="prmId")
    """Parameter ID (format ``PRM...``)."""

    row_id: str | None = Field(default=None, alias="rowId")
    """Parameter row ID within the workflow (format ``ROW...``)."""

    operator: RuleOperator
    """Comparison operator used to evaluate this condition."""

    value: str | float | int | None = Field(default=None, alias="value")
    """Threshold value to compare against."""

    unit_id: str | None = Field(default=None, alias="unitId")
    """Unit ID for the threshold value (format ``UNI...``)."""

    name: str | None = None
    """Display name of the parameter."""


class ExclusionRule(BaseAlbertModel):
    """An exclusion rule composed of one or more conditions.

    All conditions within a rule must match (AND) for the rule to trigger.
    A combination is excluded if any rule matches (OR).
    """

    id: str | None = None
    """Server-assigned rule ID (UUID). Assigned when persisted."""

    name: str | None = None
    """Human-readable label for the rule."""

    conditions: list[RuleCondition] = Field(default_factory=list)
    """List of conditions that must all be satisfied for this rule to trigger."""


Rule = ExclusionRule
"""Alias for [`ExclusionRule`][albert.resources.interval_combinations.ExclusionRule]."""


class CombinationOverride(BaseAlbertModel):
    """A manual skip or unskip override for a specific combination condition.

    Keyed by the compound override key (format ``{groupId}#{paramId}#{rowId}-...``),
    which can be generated using [`Workflow.get_override_key`][albert.resources.workflows.Workflow.get_override_key].
    """

    id: str | None = None
    """Server-assigned override ID (UUID). Assigned when persisted."""

    key: str
    """Compound key identifying the parameter-row pair(s) being overridden."""

    action: OverrideAction
    """Action to apply (``OverrideAction.SKIP`` or ``OverrideAction.UNSKIP``)."""

    is_manual: bool | None = Field(default=None, alias="isManual")
    """Whether the override was manually added."""


class BlockRules(BaseAlbertModel):
    """Combination rules and overrides for a task block.

    Returned by [`get_block_rules`][albert.collections.tasks.TaskCollection.get_block_rules]
    and [`set_block_rules`][albert.collections.tasks.TaskCollection.set_block_rules].
    """

    task_id: str = Field(alias="taskId")
    """The task ID (format ``TAS...``)."""

    block_id: str = Field(alias="blockId")
    """The block ID (format ``BLK...``)."""

    rules: list[ExclusionRule] = Field(default_factory=list)
    """Combination rules configured on this block."""

    overrides: list[CombinationOverride] = Field(default_factory=list)
    """Combination overrides configured on this block."""

    job: WorkerJob | None = Field(default=None, exclude=True)
    """Background worker job when combinations are regenerated during [`set_block_rules`][albert.collections.tasks.TaskCollection.set_block_rules]."""

    @model_validator(mode="before")
    @classmethod
    def _unwrap_rules(cls, data: Any) -> Any:
        if isinstance(data, dict):
            rules = data.get("rules")
            if isinstance(rules, dict) and "items" in rules:
                data = dict(data)
                data["rules"] = rules["items"]
        return data


class CombinationParameter(BaseAlbertModel):
    """A single parameter within a generated combination parameter group."""

    id: str
    """Parameter ID (format ``PRM...``)."""

    prg_prm_row_id: str | None = Field(default=None, alias="prgPrmRowId")
    """The parameter sequence row ID within the group."""

    row_id: str = Field(alias="rowId")
    """The parameter setpoint row ID from the workflow."""

    category: str = Field(default="Normal")
    """Category of the parameter (``"Normal"`` or ``"Special"``)."""

    short_name: str | None = Field(default=None, alias="shortName")
    """Short name for the parameter, used for special parameters."""

    required: bool = Field(default=False)
    """Whether the parameter is required."""

    interval_row_id: str | None = Field(default=None, alias="intervalRowId")
    """The interval setpoint row ID (format ``ROW...``), or ``None`` if fixed."""

    name: str
    """Display name of the parameter."""

    value: Any = Field(default=None)
    """Realized value for this combination."""

    unit: dict[str, Any] | None = Field(default=None, alias="Unit")
    """Unit definition for the value, if any."""

    is_interval: bool = Field(default=False, alias="isInterval")
    """Whether this parameter is intervalized in this combination."""


class CombinationParameterGroup(BaseAlbertModel):
    """A parameter group within a generated combination."""

    id: str
    """Parameter group ID (format ``PRG...`` or ``DAT...``)."""

    prg_sequence: int | None = Field(default=None, alias="prgSequence")
    """Position sequence of the parameter group in the workflow."""

    row_id: str = Field(alias="rowId")
    """The group setpoint row ID on the parent workflow."""

    parameters: list[CombinationParameter] = Field(alias="Parameters")
    """Parameters in this group for this combination."""


class CombinationLeaf(BaseAlbertModel):
    """One realized combination containing its configured parameter groups."""

    parameter_groups: list[CombinationParameterGroup] = Field(alias="ParameterGroups")
    """The parameter groups defining this combination."""


class IntervalCombinationPayload(BaseAlbertModel):
    """Payload containing generated combination definitions for a task block."""

    combinations: list[CombinationLeaf]
    """The list of combination definitions."""
