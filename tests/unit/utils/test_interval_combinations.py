import pytest

from albert.exceptions import AlbertException
from albert.resources.interval_combinations import (
    CombinationOverride,
    ExclusionRule,
    IntervalCombinationPayload,
    OverrideAction,
    RuleCondition,
    RuleOperator,
)
from albert.resources.workflows import (
    Interval,
    ParameterGroupSetpoints,
    ParameterSetpoint,
    Workflow,
)
from albert.utils.interval_combinations import (
    _to_number,
    condition_matches_param,
    generate_interval_combinations,
    override_key_to_interval_row_key,
)


def test_to_number_javascript_coercion_table():
    """Verify JavaScript Number() coercion table from the specification."""
    # From plan table:
    assert _to_number("0x10") == 16.0
    assert _to_number("1_0") is None
    assert _to_number("0b11") == 3.0
    assert _to_number("") is None
    assert _to_number("Infinity") == float("inf")
    assert _to_number("-Infinity") == float("-inf")

    # Additional standard inputs:
    assert _to_number("25") == 25.0
    assert _to_number("  123.45  ") == 123.45
    assert _to_number("-42.5") == -42.5
    assert _to_number("0o17") == 15.0
    assert _to_number("1e3") == 1000.0

    # Non-numeric inputs returning None:
    assert _to_number(None) is None
    assert _to_number(True) is None
    assert _to_number(False) is None
    assert _to_number("abc") is None
    assert _to_number("12a") is None
    assert _to_number("NaN") is None


def test_override_key_to_interval_row_key():
    """Test converting compound override keys to legacy ROW chains."""
    assert override_key_to_interval_row_key("PRG1#PRM100#ROW4-PRG1#PRM200#ROW9") == "ROW4XROW9"
    assert override_key_to_interval_row_key("PRG1#PRM100#ROW1") == "ROW1"
    assert (
        override_key_to_interval_row_key("PRG1#PRM1#ROW2-PRG2#PRM2#ROW5-PRG3#PRM3#ROW8")
        == "ROW2XROW5XROW8"
    )


def test_condition_matches_param_numeric_operators():
    """Test numeric operator comparisons (gt, gte, lt, lte, eq, ne)."""
    param = {"id": "PRM1", "rowId": "ROW1", "value": "100", "Unit": {"id": "UNI1"}}

    # GT
    assert condition_matches_param(
        param,
        RuleCondition(
            parameter_group_id="PRG1",
            parameter_id="PRM1",
            operator=RuleOperator.GT,
            value=90,
        ),
    )
    assert not condition_matches_param(
        param,
        RuleCondition(
            parameter_group_id="PRG1",
            parameter_id="PRM1",
            operator=RuleOperator.GT,
            value=100,
        ),
    )

    # GTE
    assert condition_matches_param(
        param,
        RuleCondition(
            parameter_group_id="PRG1",
            parameter_id="PRM1",
            operator=RuleOperator.GTE,
            value=100,
        ),
    )

    # LT
    assert condition_matches_param(
        param,
        RuleCondition(
            parameter_group_id="PRG1",
            parameter_id="PRM1",
            operator=RuleOperator.LT,
            value=150,
        ),
    )

    # Ordered operators on non-numeric strings return False
    str_param = {"id": "PRM1", "rowId": "ROW1", "value": "abc"}
    assert not condition_matches_param(
        str_param,
        RuleCondition(
            parameter_group_id="PRG1",
            parameter_id="PRM1",
            operator=RuleOperator.GT,
            value=10,
        ),
    )


def test_condition_matches_param_unit_handling():
    """Test that a unit mismatch trivially satisfies 'ne' and fails all other operators."""
    param_kg = {"id": "PRM1", "rowId": "ROW1", "value": "100", "Unit": {"id": "UNI_KG"}}

    # Same numeric value, different unit: 'ne' must match!
    cond_lb_ne = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.NE,
        value="100",
        unit_id="UNI_LB",
    )
    assert condition_matches_param(param_kg, cond_lb_ne)

    # Same numeric value, different unit: 'eq' must NOT match!
    cond_lb_eq = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.EQ,
        value="100",
        unit_id="UNI_LB",
    )
    assert not condition_matches_param(param_kg, cond_lb_eq)

    # Same numeric value, same unit: 'eq' matches, 'ne' does not
    cond_kg_eq = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.EQ,
        value="100",
        unit_id="UNI_KG",
    )
    cond_kg_ne = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.NE,
        value="100",
        unit_id="UNI_KG",
    )
    assert condition_matches_param(param_kg, cond_kg_eq)
    assert not condition_matches_param(param_kg, cond_kg_ne)


def test_condition_matches_param_empty_values():
    """Test matching against empty values and nulls."""
    empty_param = {"id": "PRM1", "rowId": "ROW1", "value": "", "Unit": None}

    # eq empty matches empty param
    cond_eq_empty = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.EQ,
        value=None,
    )
    assert condition_matches_param(empty_param, cond_eq_empty)

    # ne empty does not match empty param
    cond_ne_empty = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.NE,
        value="",
    )
    assert not condition_matches_param(empty_param, cond_ne_empty)

    # non-empty condition vs empty param: ne matches, eq does not
    cond_eq_val = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.EQ,
        value="50",
    )
    cond_ne_val = RuleCondition(
        parameter_group_id="PRG1",
        parameter_id="PRM1",
        operator=RuleOperator.NE,
        value="50",
    )
    assert not condition_matches_param(empty_param, cond_eq_val)
    assert condition_matches_param(empty_param, cond_ne_val)


def test_generate_combinations_no_intervals():
    """Test that a workflow with no intervals yields an empty combinations payload."""
    wf = Workflow(
        name="Fixed Workflow",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                row_id="ROW1",
                parameter_setpoints=[
                    ParameterSetpoint(parameter_id="PRM1", row_id="ROW2", value="25"),
                ],
            )
        ],
    )
    payload = generate_interval_combinations(wf)
    assert isinstance(payload, IntervalCombinationPayload)
    assert payload.combinations == []


def test_generate_combinations_dual_mode_exclude_and_include():
    """Test cartesian product with dual-mode evaluation (exclude vs include)."""
    # 2 Temp (25, 60) x 2 Speed (500, 1000) = 4 combinations
    wf = Workflow(
        name="Screen",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                row_id="ROW_G1",
                sequence=1,
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        row_id="ROW_P1",
                        short_name="Temp",
                        intervals=[
                            Interval(value="25", row_id="ROW1"),
                            Interval(value="60", row_id="ROW2"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM2",
                        row_id="ROW_P2",
                        short_name="Speed",
                        intervals=[
                            Interval(value="500", row_id="ROW3"),
                            Interval(value="1000", row_id="ROW4"),
                        ],
                    ),
                ],
            )
        ],
    )

    # Rule: Temp == 60 AND Speed == 1000
    rule = ExclusionRule(
        name="High Temp and High Speed",
        conditions=[
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM1",
                operator=RuleOperator.EQ,
                value="60",
            ),
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM2",
                operator=RuleOperator.EQ,
                value="1000",
            ),
        ],
    )

    # 1. Exclude mode ('all'): 4 total - 1 matched rule = 3 combinations
    payload_all = generate_interval_combinations(wf, rules=[rule], intervals_start_from="all")
    assert len(payload_all.combinations) == 3

    # 2. Exclude mode with UNSKIP override: unskips the rule-excluded combo -> 4 combinations
    unskip_override = CombinationOverride(
        key="PRG1#PRM1#ROW2-PRG1#PRM2#ROW4",
        action=OverrideAction.UNSKIP,
    )
    payload_all_unskip = generate_interval_combinations(
        wf, rules=[rule], overrides=[unskip_override], intervals_start_from="all"
    )
    assert len(payload_all_unskip.combinations) == 4

    # 3. Exclude mode with SKIP override on a non-rule combo: drops it -> 2 combinations
    skip_override = CombinationOverride(
        key="PRG1#PRM1#ROW1-PRG1#PRM2#ROW3",
        action=OverrideAction.SKIP,
    )
    payload_all_skip = generate_interval_combinations(
        wf,
        rules=[rule],
        overrides=[skip_override],
        intervals_start_from="all",
    )
    assert len(payload_all_skip.combinations) == 2

    # 4. Include mode ('none'): starts with 0, rule includes 1 combo
    payload_none = generate_interval_combinations(wf, rules=[rule], intervals_start_from="none")
    assert len(payload_none.combinations) == 1

    # 5. Include mode with UNSKIP override on another combo -> 2 combinations included
    payload_none_unskip = generate_interval_combinations(
        wf,
        rules=[rule],
        overrides=[unskip_override, skip_override],  # unskip (Temp 60, Speed 1000)
        intervals_start_from="none",
    )
    # The rule matches (60, 1000); unskip also targets (60, 1000); skip drops (25, 500)
    assert len(payload_none_unskip.combinations) == 1


def test_anchor_fixture_24_to_19():
    """Test the verified 24 -> 19 anchor fixture from the plan.

    Setup:
    - Temperature: 4 intervals (25, 60, 90, 120)
    - Speed: 3 intervals (500, 1000, 1500)
    - Formula: 2 intervals (FormA, FormB)
    Total combinations = 4 * 3 * 2 = 24.
    - 1 rule: Temperature >= 120 AND Speed >= 1500 (matches 2 combos: 120x1500 for FormA & FormB).
    - 3 skips:
      - (Temp 25, Speed 500, FormA)
      - (Temp 25, Speed 500, FormB)
      - (Temp 60, Speed 500, FormA)
    Result: 24 - 2 (rule) - 3 (skips) = 19 combinations.
    """
    wf = Workflow(
        name="Screening Anchor",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                row_id="ROW_G1",
                sequence=1,
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        row_id="ROW_P1",
                        short_name="Temp",
                        intervals=[
                            Interval(value="25", row_id="ROW10"),
                            Interval(value="60", row_id="ROW11"),
                            Interval(value="90", row_id="ROW12"),
                            Interval(value="120", row_id="ROW13"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM2",
                        row_id="ROW_P2",
                        short_name="Speed",
                        intervals=[
                            Interval(value="500", row_id="ROW20"),
                            Interval(value="1000", row_id="ROW21"),
                            Interval(value="1500", row_id="ROW22"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM3",
                        row_id="ROW_P3",
                        short_name="Formula",
                        intervals=[
                            Interval(value="FormA", row_id="ROW30"),
                            Interval(value="FormB", row_id="ROW31"),
                        ],
                    ),
                ],
            )
        ],
    )

    # Two-condition rule: Temp >= 120 and Speed >= 1500
    rule = ExclusionRule(
        name="Max stress exclusion",
        conditions=[
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM1",
                operator=RuleOperator.GTE,
                value=120,
            ),
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM2",
                operator=RuleOperator.GTE,
                value=1500,
            ),
        ],
    )

    # 3 skip overrides (disjoint from the rule)
    overrides = [
        CombinationOverride(
            key="PRG1#PRM1#ROW10-PRG1#PRM2#ROW20-PRG1#PRM3#ROW30",
            action=OverrideAction.SKIP,
        ),
        CombinationOverride(
            key="PRG1#PRM1#ROW10-PRG1#PRM2#ROW20-PRG1#PRM3#ROW31",
            action=OverrideAction.SKIP,
        ),
        CombinationOverride(
            key="PRG1#PRM1#ROW11-PRG1#PRM2#ROW20-PRG1#PRM3#ROW30",
            action=OverrideAction.SKIP,
        ),
    ]

    payload = generate_interval_combinations(
        wf, rules=[rule], overrides=overrides, intervals_start_from="all"
    )
    assert len(payload.combinations) == 19


def test_generate_combinations_exceeds_max_cap():
    """Test that exceeding MAX_RESULTS (2000) raises AlbertException."""
    # Build a workflow yielding 50 * 50 = 2500 combinations
    wf = Workflow(
        name="Oversized",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                row_id="ROW_G1",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        row_id="ROW_P1",
                        intervals=[
                            Interval(value=str(i), row_id=f"ROW{1000 + i}") for i in range(50)
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM2",
                        row_id="ROW_P2",
                        intervals=[
                            Interval(value=str(i), row_id=f"ROW{2000 + i}") for i in range(50)
                        ],
                    ),
                ],
            )
        ],
    )

    with pytest.raises(AlbertException, match="exceeds maximum allowed limit of 2000"):
        generate_interval_combinations(wf, intervals_start_from="all")


def test_s3_payload_serialization():
    """Test that IntervalCombinationPayload dumps into the exact wire format for S3."""
    wf = Workflow(
        name="Wire Spec",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG247776",
                row_id="ROW_G1",
                sequence=1,
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM100",
                        row_id="ROW_P1",
                        name="Temperature",
                        sequence="ROW1",
                        intervals=[
                            Interval(
                                value="25",
                                row_id="ROW4",
                                unit={"id": "UNI1", "name": "C"},
                            )
                        ],
                    )
                ],
            )
        ],
    )
    payload = generate_interval_combinations(wf)
    wire = payload.model_dump(by_alias=True, mode="json", exclude_none=True)

    assert "combinations" in wire
    assert len(wire["combinations"]) == 1
    combo = wire["combinations"][0]
    assert "ParameterGroups" in combo
    group = combo["ParameterGroups"][0]
    assert group["id"] == "PRG247776"
    assert group["rowId"] == "ROW_G1"
    assert group["prgSequence"] == 1
    prm = group["Parameters"][0]
    assert prm["id"] == "PRM100"
    assert prm["rowId"] == "ROW_P1"
    assert prm["prgPrmRowId"] == "ROW1"
    assert prm["intervalRowId"] == "ROW4"
    assert prm["name"] == "Temperature"
    assert prm["value"] == "25"
    assert prm["Unit"] == {"id": "UNI1", "name": "C"}
    assert prm["isInterval"] is True


def test_multi_group_cartesian_product_and_key_structure():
    """Test cartesian product across multiple parameter groups."""
    wf = Workflow(
        name="Multi Group",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                row_id="ROW_G1",
                sequence=1,
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        row_id="ROW_P1",
                        intervals=[
                            Interval(value="10", row_id="ROW1"),
                            Interval(value="20", row_id="ROW2"),
                        ],
                    ),
                    # Fixed parameter in group 1
                    ParameterSetpoint(
                        parameter_id="PRM_FIXED",
                        row_id="ROW_PF",
                        value="Fixed1",
                    ),
                ],
            ),
            ParameterGroupSetpoints(
                id="PRG2",
                row_id="ROW_G2",
                sequence=2,
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM2",
                        row_id="ROW_P2",
                        intervals=[
                            Interval(value="A", row_id="ROW3"),
                            Interval(value="B", row_id="ROW4"),
                            Interval(value="C", row_id="ROW5"),
                        ],
                    ),
                ],
            ),
        ],
    )

    payload = generate_interval_combinations(wf)
    # 2 in group 1 * 3 in group 2 = 6 combinations
    assert len(payload.combinations) == 6

    # Verify that fixed parameter is present on every combination
    for combo in payload.combinations:
        g1 = combo.parameter_groups[0]
        assert len(g1.parameters) == 2
        fixed = [p for p in g1.parameters if p.id == "PRM_FIXED"][0]
        assert fixed.value == "Fixed1"
        assert fixed.is_interval is False
        assert fixed.interval_row_id is None


def test_frontend_parity_two_hyphens_different_units():
    """Parity test with frontend: eq empty+unitId excludes only that specific empty interval."""
    # Material = {80@UNI1, 100@UNI1, empty@UNI1, empty@UNI2}
    # Rule eq null + unitId UNI1 -> only Unitless/matching empty excluded -> included 3.
    wf = Workflow(
        name="Hyphen units",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                row_id="ROW_G1",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        row_id="ROW_P1",
                        intervals=[
                            Interval(value="80", row_id="ROW1", unit={"id": "UNI1"}),
                            Interval(value="100", row_id="ROW2", unit={"id": "UNI1"}),
                            Interval(value="", row_id="ROW3", unit={"id": "UNI1"}),
                            Interval(value="", row_id="ROW4", unit={"id": "UNI2"}),
                        ],
                    ),
                ],
            )
        ],
    )

    rule = ExclusionRule(
        conditions=[
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM1",
                operator=RuleOperator.EQ,
                value=None,
                unit_id="UNI1",
            )
        ]
    )

    payload = generate_interval_combinations(wf, rules=[rule], intervals_start_from="all")
    assert len(payload.combinations) == 3


def test_frontend_parity_same_value_different_units_ne():
    """Parity test with frontend: ne + unitId excludes only the differing-unit interval."""
    # Weight = {100@UNI_KG, 100@UNI_LB}
    # Rule ne 100 + unitId UNI_KG -> matches 100@UNI_LB because of unit mismatch!
    # Therefore, 100@UNI_LB is excluded, leaving 100@UNI_KG included.
    wf = Workflow(
        name="Unit NE",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                row_id="ROW_G1",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        row_id="ROW_P1",
                        intervals=[
                            Interval(value="100", row_id="ROW1", unit={"id": "UNI_KG"}),
                            Interval(value="100", row_id="ROW2", unit={"id": "UNI_LB"}),
                        ],
                    ),
                ],
            )
        ],
    )

    rule = ExclusionRule(
        conditions=[
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM1",
                operator=RuleOperator.NE,
                value="100",
                unit_id="UNI_KG",
            )
        ]
    )

    payload = generate_interval_combinations(wf, rules=[rule], intervals_start_from="all")
    assert len(payload.combinations) == 1
    remaining_param = payload.combinations[0].parameter_groups[0].parameters[0]
    assert remaining_param.unit == {"id": "UNI_KG", "name": None}
