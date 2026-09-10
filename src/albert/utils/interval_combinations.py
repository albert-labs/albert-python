from __future__ import annotations

import math
from collections.abc import Sequence
from enum import Enum
from typing import Any, Literal

from albert.exceptions import AlbertException
from albert.resources.interval_combinations import (
    CombinationLeaf,
    CombinationOverride,
    CombinationParameter,
    CombinationParameterGroup,
    ExclusionRule,
    IntervalCombinationPayload,
    RuleCondition,
)
from albert.resources.workflows import ParameterGroupSetpoints, Workflow

MAX_RESULTS = 2000


def _to_number(val: Any) -> float | None:
    """Parse a value into a float using JavaScript Number() coercion semantics.

    Returns None for values that would coerce to NaN or are empty/invalid.
    Specifically matches the JavaScript frontend coercion table:
    - "0x10" -> 16.0
    - "1_0" -> None (Python float allows underscores, JS Number() returns NaN)
    - "0b11" -> 3.0
    - "" -> None (guarded out before conversion)
    - "Infinity" -> inf
    - "-Infinity" -> -inf
    """
    if val is None:
        return None

    if isinstance(val, bool):
        return None

    if isinstance(val, (int, float)):
        if math.isnan(val):
            return None
        return float(val)

    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        if "_" in s:
            # JavaScript Number() does not accept numeric underscores
            return None
        if s.lower() == "nan":
            return None
        if s in ("Infinity", "+Infinity"):
            return float("inf")
        if s == "-Infinity":
            return float("-inf")
        if s.startswith(("0x", "0X")):
            try:
                return float(int(s, 16))
            except ValueError:
                return None
        if s.startswith(("0b", "0B")):
            try:
                return float(int(s, 2))
            except ValueError:
                return None
        if s.startswith(("0o", "0O")):
            try:
                return float(int(s, 8))
            except ValueError:
                return None
        try:
            return float(s)
        except ValueError:
            return None

    return None


def _to_str(val: Any) -> str:
    """Extract a normalized string value from a raw parameter or condition value."""
    if val is None:
        return ""
    if isinstance(val, dict):
        if "value" in val and val["value"] is not None:
            return str(val["value"])
        if "id" in val and val["id"] is not None:
            return str(val["id"])
        if "name" in val and val["name"] is not None:
            return str(val["name"])
        return str(val)
    if hasattr(val, "id") and getattr(val, "id", None) is not None:
        return str(val.id)
    return str(val)


def _get_unit_id(unit: Any) -> str:
    """Extract unit ID string from an entity link, dict, or string."""
    if not unit:
        return ""
    if isinstance(unit, dict):
        return str(unit.get("id") or "")
    if hasattr(unit, "id") and getattr(unit, "id", None) is not None:
        return str(unit.id)
    return str(unit)


def override_key_to_interval_row_key(key: str) -> str:
    """Convert a compound override key to the legacy interval row key format.

    Extracts the interval row ID from each segment of a compound key and joins
    them with ``"X"``.

    !!! example
        ```python
        override_key_to_interval_row_key("PRG1#PRM100#ROW4-PRG1#PRM200#ROW9")
        # 'ROW4XROW9'
        ```

    Parameters
    ----------
    key : str
        The compound override key (format ``"{groupId}#{paramId}#{rowId}-..."``).

    Returns
    -------
    str
        The legacy interval row key (format ``"ROW#XROW#..."``).
    """
    segments = key.split("-")
    row_ids = [seg.split("#")[-1] for seg in segments if "#" in seg]
    return "X".join(row_ids)


def condition_matches_param(
    param: CombinationParameter | dict[str, Any],
    cond: RuleCondition,
) -> bool:
    """Evaluate whether a single rule condition matches a combination parameter.

    Implements the exact matching semantics from the frontend engine:
    - row ID must match if condition specifies a row ID.
    - If condition does not specify row ID, parameter ID and group ID are checked.
    - Unit mismatch trivially satisfies ``ne`` (different unit means not equal).
    - Unit mismatch fails all other comparison operators.
    - Ordered comparisons (``gt``, ``gte``, ``lt``, ``lte``) require both sides to be numeric.
    - Empty condition values match empty parameter values for ``eq`` / ``ne``.
    """
    prm_id = param.id if isinstance(param, CombinationParameter) else str(param.get("id", ""))
    prm_row_id = (
        param.row_id if isinstance(param, CombinationParameter) else str(param.get("rowId", ""))
    )
    prm_val = param.value if isinstance(param, CombinationParameter) else param.get("value")
    prm_unit = param.unit if isinstance(param, CombinationParameter) else param.get("Unit")

    # Match parameter identity
    if (
        cond.row_id
        and prm_row_id != cond.row_id
        or not cond.row_id
        and cond.parameter_id
        and prm_id != cond.parameter_id
    ):
        return False

    op_val = cond.operator.value if isinstance(cond.operator, Enum) else str(cond.operator).lower()

    is_cond_empty = cond.value in (None, "")
    is_prm_empty = prm_val in (None, "")

    prm_unit_id = _get_unit_id(prm_unit)
    cond_unit_id = str(cond.unit_id) if cond.unit_id else ""
    has_unit_constraint = bool(cond.unit_id and not is_prm_empty and not is_cond_empty)
    unit_mismatch = has_unit_constraint and (prm_unit_id != cond_unit_id)

    # A unit mismatch trivially satisfies 'ne'
    if op_val == "ne" and unit_mismatch:
        return True

    # Empty condition value handling
    if is_cond_empty:
        unit_matches = not cond.unit_id or (prm_unit_id == cond_unit_id)
        if op_val == "eq":
            return is_prm_empty and unit_matches
        if op_val == "ne":
            if cond.unit_id:
                return not (is_prm_empty and unit_matches)
            return not is_prm_empty
        return False

    # Non-empty condition vs empty parameter
    if is_prm_empty:
        if op_val == "ne":
            unit_matches = not cond.unit_id or (prm_unit_id == cond_unit_id)
            return unit_matches
        return False

    # Normal comparison: non-empty condition and non-empty parameter
    prm_str = _to_str(prm_val)
    cond_str = _to_str(cond.value)

    prm_num = _to_number(prm_str)
    cond_num = _to_number(cond_str)
    both_numeric = prm_num is not None and cond_num is not None

    matched = False
    if op_val == "eq":
        matched = prm_num == cond_num if both_numeric else prm_str == cond_str
    elif op_val == "ne":
        matched = prm_num != cond_num if both_numeric else prm_str != cond_str
    elif op_val == "gt":
        matched = both_numeric and prm_num > cond_num
    elif op_val == "gte":
        matched = both_numeric and prm_num >= cond_num
    elif op_val == "lt":
        matched = both_numeric and prm_num < cond_num
    elif op_val == "lte":
        matched = both_numeric and prm_num <= cond_num

    if not matched:
        return False
    return not unit_mismatch


def rule_matches_leaf(leaf: CombinationLeaf, rule: ExclusionRule) -> bool:
    """Evaluate whether all conditions in a rule match any parameter in the leaf (AND)."""
    if not rule.conditions:
        return False

    # Flatten all parameters in the leaf
    all_params: list[CombinationParameter] = []
    for group in leaf.parameter_groups:
        all_params.extend(group.parameters)

    for cond in rule.conditions:
        condition_met = any(condition_matches_param(p, cond) for p in all_params)
        if not condition_met:
            return False

    return True


def combination_to_override_key(leaf: CombinationLeaf) -> str:
    """Build the compound override key for a realized combination leaf."""
    segments: list[str] = []
    for group in leaf.parameter_groups:
        for p in group.parameters:
            if p.is_interval and p.interval_row_id:
                segments.append(f"{group.id}#{p.id}#{p.interval_row_id}")
    return "-".join(segments)


def _get_field(obj: Any, attr: str, alias: str | None = None, default: Any = None) -> Any:
    """Safely get a field from a model or dict by attribute name or alias."""
    if hasattr(obj, attr):
        val = getattr(obj, attr)
        if val is not None:
            return val
    if alias and hasattr(obj, alias):
        val = getattr(obj, alias)
        if val is not None:
            return val
    if isinstance(obj, dict):
        if attr in obj and obj[attr] is not None:
            return obj[attr]
        if alias and alias in obj and obj[alias] is not None:
            return obj[alias]
    return default


def generate_interval_combinations(
    workflow: Workflow | Sequence[ParameterGroupSetpoints] | list[dict[str, Any]],
    rules: list[ExclusionRule] | None = None,
    overrides: list[CombinationOverride] | None = None,
    intervals_start_from: Literal["all", "none"] = "all",
) -> IntervalCombinationPayload:
    """Calculate interval combinations from a workflow and evaluate rules and overrides (🧪 Beta).

    Pure, session-free computation engine that calculates the active set of combinations:
    1. Expands parameter intervals into the full cartesian product.
    2. Builds canonical compound override keys for each combination.
    3. Evaluates direct overrides (``skip`` / ``unskip``), taking precedence over rules.
    4. Evaluates exclusion or inclusion rules depending on ``intervals_start_from``:
       - ``"all"`` (Exclude Mode): Starts with all combinations included; excludes
         combinations matching any exclusion rule.
       - ``"none"`` (Include Mode): Starts with no combinations included; includes
         combinations matching any inclusion rule.
    5. Enforces the platform safety cap of 2,000 combinations.

    This client-side computation is used internally by
    [`create_with_combinations`][albert.collections.tasks.TaskCollection.create_with_combinations]
    and [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations],
    and can also be called directly to simulate or preview combinations locally.

    !!! warning "Beta Feature!"
        Increased intervals combination support is currently in beta and behind a platform
        feature flag. Please do not use in production or without explicit guidance from
        Albert. You might otherwise have a bad experience. This feature currently falls
        outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert
        from albert.utils.interval_combinations import generate_interval_combinations

        client = Albert()
        workflow = client.workflows.get_by_id(id="WFL456")
        payload = generate_interval_combinations(
            workflow=workflow,
            intervals_start_from="all",
        )
        len(payload.combinations)
        # 12
        ```

    Parameters
    ----------
    workflow : Workflow or Sequence[ParameterGroupSetpoints] or list[dict]
        The parent workflow or parameter group setpoints containing intervals.
        Must already have assigned row IDs.
    rules : list[ExclusionRule], optional
        The combination exclusion or inclusion rules to evaluate.
    overrides : list[CombinationOverride], optional
        The combination overrides (skip/unskip) to apply.
    intervals_start_from : {"all", "none"}, default "all"
        The evaluation mode: ``"all"`` (exclude mode) or ``"none"`` (include mode).

    Returns
    -------
    IntervalCombinationPayload
        The combinations payload containing the calculated combination leaves.

    Raises
    ------
    AlbertException
        If the resulting combinations exceed 2,000 or if row IDs are unassigned.
    """
    raw_groups: list[Any]
    if isinstance(workflow, Workflow):
        raw_groups = workflow.parameter_group_setpoints or []
    elif isinstance(workflow, Sequence):
        raw_groups = list(workflow)
    else:
        raw_groups = []

    if not raw_groups:
        return IntervalCombinationPayload(combinations=[])

    # Check whether ANY parameter has intervals
    has_any_intervals = False
    for group in raw_groups:
        setpoints = _get_field(group, "parameter_setpoints", alias="Parameters", default=[])
        for sp in setpoints:
            ivs = _get_field(sp, "intervals", alias="Intervals", default=[])
            if ivs and len(ivs) > 0:
                has_any_intervals = True
                break
        if has_any_intervals:
            break

    if not has_any_intervals:
        # A block with no intervals has no combinations to generate via worker file
        return IntervalCombinationPayload(combinations=[])

    # Pre-parse overrides into skip and unskip lookup sets
    skip_set: set[str] = set()
    unskip_set: set[str] = set()
    for ov in overrides or []:
        action = ov.action.value if isinstance(ov.action, Enum) else str(ov.action).lower()
        if action == "skip":
            skip_set.add(ov.key)
        elif action == "unskip":
            unskip_set.add(ov.key)

    rules_list = rules or []

    # Step 1: Expand each group into variants
    expanded_groups: list[list[CombinationParameterGroup]] = []

    for group in raw_groups:
        grp_id = str(_get_field(group, "id", default=""))
        grp_seq = _get_field(group, "sequence", alias="prgSequence")
        grp_row_id = str(_get_field(group, "row_id", alias="rowId", default="ROW1"))

        raw_setpoints = _get_field(group, "parameter_setpoints", alias="Parameters", default=[])

        variable_params = []
        for sp in raw_setpoints:
            ivs = _get_field(sp, "intervals", alias="Intervals", default=[])
            if ivs and len(ivs) > 0:
                variable_params.append(sp)

        if not variable_params:
            # Fixed group: 1 variant with fixed parameters
            fixed_params: list[CombinationParameter] = []
            for sp in raw_setpoints:
                p_id = str(_get_field(sp, "parameter_id", default=""))
                p_row_id = str(_get_field(sp, "row_id", alias="rowId", default="ROW1"))
                p_seq = _get_field(sp, "sequence", alias="prgPrmRowId")
                p_cat_raw = _get_field(sp, "category", default="Normal")
                p_cat = (
                    p_cat_raw.value if isinstance(p_cat_raw, Enum) else str(p_cat_raw or "Normal")
                )
                p_short_name = _get_field(sp, "short_name", alias="shortName")
                p_name = _get_field(sp, "name") or p_short_name or p_id
                p_val = _get_field(sp, "value")
                p_unit = _extract_unit_dict(sp)

                fixed_params.append(
                    CombinationParameter(
                        id=p_id,
                        prg_prm_row_id=p_seq,
                        row_id=p_row_id,
                        category=p_cat,
                        short_name=p_short_name,
                        required=False,
                        interval_row_id=None,
                        name=str(p_name),
                        value=p_val,
                        unit=p_unit,
                        is_interval=False,
                    )
                )

            expanded_groups.append(
                [
                    CombinationParameterGroup(
                        id=grp_id,
                        prg_sequence=grp_seq,
                        row_id=grp_row_id,
                        parameters=fixed_params,
                    )
                ]
            )
            continue

        # Fold variable parameters (last variable parameter varies fastest)
        combos: list[dict[str, Any]] = [{}]
        for sp in variable_params:
            sp_row_id = str(_get_field(sp, "row_id", alias="rowId", default="ROW1"))
            sp_ivs = _get_field(sp, "intervals", alias="Intervals", default=[])
            next_combos: list[dict[str, Any]] = []
            for base in combos:
                for iv in sp_ivs:
                    iv_val = _get_field(iv, "value")
                    iv_row_id = _get_field(iv, "row_id", alias="rowId")
                    if not iv_row_id:
                        raise AlbertException(
                            "Workflow has not been assigned interval row IDs by the backend yet. "
                            "Save the workflow first before generating combinations."
                        )
                    iv_unit = _extract_unit_dict(iv)
                    iv_name = _get_field(iv, "name", default="")

                    new_combo = dict(base)
                    new_combo[sp_row_id] = {
                        "value": iv_val,
                        "interval_row_id": str(iv_row_id),
                        "unit": iv_unit,
                        "name": iv_name or "",
                    }
                    next_combos.append(new_combo)
            combos = next_combos

        variable_row_ids = {
            str(_get_field(sp, "row_id", alias="rowId", default="ROW1")) for sp in variable_params
        }

        # Build variants for this group
        group_variants: list[CombinationParameterGroup] = []
        for sel in combos:
            params_list: list[CombinationParameter] = []
            for sp in raw_setpoints:
                sp_p_id = str(_get_field(sp, "parameter_id", default=""))
                sp_row_id = str(_get_field(sp, "row_id", alias="rowId", default="ROW1"))
                sp_seq = _get_field(sp, "sequence", alias="prgPrmRowId")
                sp_cat_raw = _get_field(sp, "category", default="Normal")
                sp_cat = (
                    sp_cat_raw.value
                    if isinstance(sp_cat_raw, Enum)
                    else str(sp_cat_raw or "Normal")
                )
                sp_short_name = _get_field(sp, "short_name", alias="shortName")
                sp_name = _get_field(sp, "name") or sp_short_name or sp_p_id

                is_var = sp_row_id in variable_row_ids
                if is_var:
                    selected = sel[sp_row_id]
                    p_val = selected["value"]
                    p_unit = selected["unit"] or _extract_unit_dict(sp)
                    p_iv_row_id = selected["interval_row_id"]
                    is_interval = True
                else:
                    p_val = _get_field(sp, "value")
                    p_unit = _extract_unit_dict(sp)
                    p_iv_row_id = None
                    is_interval = False

                params_list.append(
                    CombinationParameter(
                        id=sp_p_id,
                        prg_prm_row_id=sp_seq,
                        row_id=sp_row_id,
                        category=sp_cat,
                        short_name=sp_short_name,
                        required=False,
                        interval_row_id=p_iv_row_id,
                        name=str(sp_name),
                        value=p_val,
                        unit=p_unit,
                        is_interval=is_interval,
                    )
                )

            group_variants.append(
                CombinationParameterGroup(
                    id=grp_id,
                    prg_sequence=grp_seq,
                    row_id=grp_row_id,
                    parameters=params_list,
                )
            )

        expanded_groups.append(group_variants)

    # Step 2: Cartesian product across groups (DFS)
    leaves: list[CombinationLeaf] = []

    def _dfs(group_idx: int, current_groups: list[CombinationParameterGroup]) -> None:
        if group_idx == len(expanded_groups):
            leaves.append(CombinationLeaf(parameter_groups=list(current_groups)))
            return

        for variant in expanded_groups[group_idx]:
            current_groups.append(variant)
            _dfs(group_idx + 1, current_groups)
            current_groups.pop()

    _dfs(0, [])

    # Step 3: Evaluate overrides and rules
    result_combinations: list[CombinationLeaf] = []

    for leaf in leaves:
        key = combination_to_override_key(leaf)

        # Overrides have top precedence
        if key in skip_set:
            continue
        if key in unskip_set:
            result_combinations.append(leaf)
            continue

        # Evaluate rules
        matched_any_rule = False
        for rule in rules_list:
            if rule_matches_leaf(leaf, rule):
                matched_any_rule = True
                break

        if intervals_start_from == "all":
            # Exclude mode: matching a rule excludes it
            if not matched_any_rule:
                result_combinations.append(leaf)
        else:
            # Include mode: matching a rule includes it
            if matched_any_rule:
                result_combinations.append(leaf)

        if len(result_combinations) > MAX_RESULTS:
            raise AlbertException(
                f"Generated combinations count exceeds maximum allowed limit of {MAX_RESULTS}. "
                "Please add exclusion rules or reduce interval setpoints."
            )

    return IntervalCombinationPayload(combinations=result_combinations)


def _extract_unit_dict(obj: Any) -> dict[str, Any] | None:
    """Extract unit as a clean dictionary."""
    unit = _get_field(obj, "unit", alias="Unit")
    if not unit:
        return None
    if isinstance(unit, dict):
        return {"id": unit.get("id"), "name": unit.get("name")}
    if hasattr(unit, "id"):
        return {
            "id": getattr(unit, "id", None),
            "name": getattr(unit, "name", None),
        }
    return {"id": str(unit)}
