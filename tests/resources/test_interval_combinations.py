import pytest

from albert.exceptions import AlbertException
from albert.resources.interval_combinations import (
    BlockRules,
    CombinationOverride,
    ExclusionRule,
    OverrideAction,
    RuleCondition,
    RuleOperator,
)
from albert.resources.tasks import Block
from albert.resources.workflows import (
    Interval,
    ParameterGroupSetpoints,
    ParameterSetpoint,
    Workflow,
)


def test_rule_condition_serialization():
    """Test RuleCondition serialization to camelCase wire format."""
    condition = RuleCondition(
        parameter_group_id="PRG247776",
        parameter_id="PRM100",
        row_id="ROW2",
        operator=RuleOperator.GTE,
        value="90",
        unit_id="UNI1",
        name="Temperature",
    )
    wire = condition.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert wire == {
        "prgId": "PRG247776",
        "prmId": "PRM100",
        "rowId": "ROW2",
        "operator": "gte",
        "value": "90",
        "unitId": "UNI1",
        "name": "Temperature",
    }


def test_rule_condition_deserialization():
    """Test RuleCondition deserialization from wire camelCase format."""
    wire = {
        "prgId": "PRG247776",
        "prmId": "PRM100",
        "rowId": "ROW2",
        "operator": "gte",
        "value": 90,
    }
    condition = RuleCondition.model_validate(wire)
    assert condition.parameter_group_id == "PRG247776"
    assert condition.parameter_id == "PRM100"
    assert condition.row_id == "ROW2"
    assert condition.operator == RuleOperator.GTE
    assert condition.value == 90
    assert condition.unit_id is None


def test_combination_override_serialization():
    """Test CombinationOverride serialization."""
    override = CombinationOverride(
        key="PRG247776#PRM100#ROW4-PRG247776#PRM200#ROW9",
        action=OverrideAction.SKIP,
    )
    wire = override.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert wire == {
        "key": "PRG247776#PRM100#ROW4-PRG247776#PRM200#ROW9",
        "action": "skip",
    }


def test_block_rules_unwrap_response():
    """Test BlockRules unwraps paginated rules envelope."""
    payload = {
        "taskId": "TASFOR123",
        "blockId": "BLK1",
        "rules": {
            "items": [
                {
                    "id": "rule-uuid-1",
                    "name": "High temp cutoff",
                    "conditions": [
                        {
                            "prgId": "PRG1",
                            "prmId": "PRM1",
                            "rowId": "ROW2",
                            "operator": "gt",
                            "value": 100,
                        }
                    ],
                }
            ],
            "lastKey": None,
        },
        "overrides": [
            {
                "id": "override-uuid-1",
                "key": "PRG1#PRM1#ROW2",
                "action": "unskip",
            }
        ],
    }
    block_rules = BlockRules.model_validate(payload)
    assert block_rules.task_id == "TASFOR123"
    assert block_rules.block_id == "BLK1"
    assert len(block_rules.rules) == 1
    assert block_rules.rules[0].id == "rule-uuid-1"
    assert block_rules.rules[0].name == "High temp cutoff"
    assert len(block_rules.rules[0].conditions) == 1
    assert block_rules.rules[0].conditions[0].parameter_group_id == "PRG1"
    assert len(block_rules.overrides) == 1
    assert block_rules.overrides[0].id == "override-uuid-1"
    assert block_rules.overrides[0].action == OverrideAction.UNSKIP


def test_workflow_get_override_key():
    """Test Workflow.get_override_key builds compound keys in canonical order."""
    wf = Workflow(
        name="Screening Workflow",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG247776",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM100",
                        short_name="Temp",
                        intervals=[
                            Interval(value="25", unit={"id": "UNI1"}, row_id="ROW4"),
                            Interval(value="60", unit={"id": "UNI1"}, row_id="ROW5"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM200",
                        short_name="Speed",
                        intervals=[
                            Interval(value="500", unit={"id": "UNI2"}, row_id="ROW8"),
                            Interval(value="1500", unit={"id": "UNI2"}, row_id="ROW9"),
                        ],
                    ),
                ],
            )
        ],
    )

    # Normal order
    key1 = wf.get_override_key({"Temp": 25, "Speed": 500})
    assert key1 == "PRG247776#PRM100#ROW4-PRG247776#PRM200#ROW8"

    # Inverted caller arg order -> same canonical order in key
    key2 = wf.get_override_key({"Speed": 1500, "Temp": 60})
    assert key2 == "PRG247776#PRM100#ROW5-PRG247776#PRM200#ROW9"

    # Missing interval raises AlbertException
    with pytest.raises(AlbertException, match="No matching interval found"):
        wf.get_override_key({"Temp": 999})


def test_workflow_get_override_key_unassigned_row_id():
    """Test get_override_key raises when row IDs have not been assigned yet."""
    wf = Workflow(
        name="Unsaved Workflow",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM1",
                        name="Temp",
                        intervals=[
                            Interval(value="25"),
                        ],
                    ),
                ],
            )
        ],
    )
    with pytest.raises(AlbertException, match="not been assigned interval row IDs"):
        wf.get_override_key({"Temp": 25})


def test_block_rules_and_overrides_excluded_from_dump():
    """Test Block excludes rules and overrides from model_dump payload."""
    rule = ExclusionRule(
        conditions=[
            RuleCondition(
                parameter_group_id="PRG1",
                parameter_id="PRM1",
                row_id="ROW2",
                operator=RuleOperator.EQ,
                value="25",
            )
        ]
    )
    override = CombinationOverride(key="PRG1#PRM1#ROW2", action=OverrideAction.SKIP)
    block = Block(
        workflow=[{"id": "WFL1"}],
        data_template=[{"id": "DAT1"}],
        rules=[rule],
        overrides=[override],
    )
    assert block.rules == [rule]
    assert block.overrides == [override]

    dumped = block.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert "rules" not in dumped
    assert "overrides" not in dumped
    assert "Workflow" in dumped
    assert "Datatemplate" in dumped


def test_workflow_build_rule_condition():
    """Test Workflow.build_rule_condition resolves IDs, unit, and operator correctly."""
    wf = Workflow(
        name="Screening Workflow",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG247776",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM100",
                        short_name="Temp",
                        row_id="ROW1",
                        unit={"id": "UNI1", "name": "C"},
                        intervals=[
                            Interval(value="25", unit={"id": "UNI1"}, row_id="ROW4"),
                            Interval(value="60", unit={"id": "UNI1"}, row_id="ROW5"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM200",
                        short_name="Speed",
                        row_id="ROW2",
                        unit={"id": "UNI2", "name": "RPM"},
                        intervals=[
                            Interval(value="500", unit={"id": "UNI2"}, row_id="ROW8"),
                            Interval(value="1500", unit={"id": "UNI2"}, row_id="ROW9"),
                        ],
                    ),
                ],
            )
        ],
    )

    cond = wf.build_rule_condition("Temp", ">=", 90)
    assert cond.parameter_group_id == "PRG247776"
    assert cond.parameter_id == "PRM100"
    assert cond.row_id == "ROW1"
    assert cond.operator == RuleOperator.GTE
    assert cond.value == 90
    assert cond.unit_id == "UNI1"
    assert cond.name == "Temp"

    # Operator string variations
    assert wf.build_rule_condition("Temp", "=").operator == RuleOperator.EQ
    assert wf.build_rule_condition("Temp", "==").operator == RuleOperator.EQ
    assert wf.build_rule_condition("Temp", "!=").operator == RuleOperator.NE
    assert wf.build_rule_condition("Temp", "<").operator == RuleOperator.LT
    assert wf.build_rule_condition("Temp", "<=").operator == RuleOperator.LTE
    assert wf.build_rule_condition("Temp", ">").operator == RuleOperator.GT

    # Explicit unit override
    cond_unit = wf.build_rule_condition("Speed", ">", 1000, unit="UNI99")
    assert cond_unit.unit_id == "UNI99"

    # Invalid operator
    with pytest.raises(ValueError, match="Invalid rule operator"):
        wf.build_rule_condition("Temp", "INVALID_OP")

    # Missing parameter
    with pytest.raises(AlbertException, match="No parameter matching 'MissingParam'"):
        wf.build_rule_condition("MissingParam", "=")


def test_workflow_build_rule_condition_disambiguation_and_unsaved():
    """Test build_rule_condition disambiguation with group and error on unsaved workflow."""
    # Workflow with same param name in two groups
    wf_multi = Workflow(
        name="Multi-group Workflow",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_group_name="Group One",
                parameter_setpoints=[
                    ParameterSetpoint(parameter_id="PRM10", name="Viscosity", row_id="ROW1"),
                ],
            ),
            ParameterGroupSetpoints(
                id="PRG2",
                parameter_group_name="Group Two",
                parameter_setpoints=[
                    ParameterSetpoint(parameter_id="PRM20", name="Viscosity", row_id="ROW2"),
                ],
            ),
        ],
    )

    # Ambiguous when group not specified
    with pytest.raises(AlbertException, match="is ambiguous"):
        wf_multi.build_rule_condition("Viscosity", "=")

    # Disambiguated by group ID
    c1 = wf_multi.build_rule_condition("Viscosity", "=", 10, group="PRG1")
    assert c1.parameter_group_id == "PRG1"
    assert c1.parameter_id == "PRM10"
    assert c1.row_id == "ROW1"

    # Disambiguated by group name
    c2 = wf_multi.build_rule_condition("Viscosity", "=", 20, group="Group Two")
    assert c2.parameter_group_id == "PRG2"
    assert c2.parameter_id == "PRM20"
    assert c2.row_id == "ROW2"

    # Unsaved workflow (missing row_id on setpoint)
    wf_unsaved = Workflow(
        name="Unsaved",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG1",
                parameter_setpoints=[
                    ParameterSetpoint(parameter_id="PRM1", name="Temp"),
                ],
            )
        ],
    )
    with pytest.raises(AlbertException, match="not been assigned row IDs"):
        wf_unsaved.build_rule_condition("Temp", "=")


def test_workflow_build_exclusion_rule():
    """Test Workflow.build_exclusion_rule handles single and multi-condition rules."""
    wf = Workflow(
        name="Screening Workflow",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG247776",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM100",
                        short_name="Temp",
                        row_id="ROW1",
                        unit={"id": "UNI1"},
                        intervals=[
                            Interval(value="25", unit={"id": "UNI1"}, row_id="ROW4"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM200",
                        short_name="Speed",
                        row_id="ROW2",
                        unit={"id": "UNI2"},
                        intervals=[
                            Interval(value="500", unit={"id": "UNI2"}, row_id="ROW8"),
                        ],
                    ),
                ],
            )
        ],
    )

    # 1. Single condition directly via kwargs
    rule1 = wf.build_exclusion_rule(
        name="Exclude cold",
        parameter="Temp",
        operator="<",
        value=15,
    )
    assert rule1.name == "Exclude cold"
    assert len(rule1.conditions) == 1
    assert rule1.conditions[0].parameter_id == "PRM100"
    assert rule1.conditions[0].operator == RuleOperator.LT
    assert rule1.conditions[0].value == 15

    # 2. Multi-condition via tuples
    rule2 = wf.build_exclusion_rule(
        name="Crosslinking risk",
        conditions=[
            ("Temp", ">=", 90),
            ("Speed", ">=", 1500),
        ],
    )
    assert rule2.name == "Crosslinking risk"
    assert len(rule2.conditions) == 2
    assert rule2.conditions[0].parameter_id == "PRM100"
    assert rule2.conditions[0].operator == RuleOperator.GTE
    assert rule2.conditions[1].parameter_id == "PRM200"
    assert rule2.conditions[1].operator == RuleOperator.GTE

    # 3. Multi-condition via RuleCondition instances
    c1 = wf.build_rule_condition("Temp", ">=", 90)
    c2 = wf.build_rule_condition("Speed", ">=", 1500)
    rule3 = wf.build_rule(name="Rule 3", conditions=[c1, c2])
    assert len(rule3.conditions) == 2

    # 4. Inclusion rule builder alias
    rule_inc = wf.build_inclusion_rule(
        name="Include low temp",
        conditions=[("Temp", "<", 30)],
    )
    assert rule_inc.name == "Include low temp"
    assert len(rule_inc.conditions) == 1
    assert rule_inc.conditions[0].operator == RuleOperator.LT

    # Error when neither conditions nor parameter/operator provided
    with pytest.raises(ValueError, match="Provide either 'conditions'"):
        wf.build_rule(name="Empty")


def test_workflow_build_override():
    """Test Workflow.build_override creates CombinationOverride with canonical key."""
    wf = Workflow(
        name="Screening Workflow",
        parameter_group_setpoints=[
            ParameterGroupSetpoints(
                id="PRG247776",
                parameter_setpoints=[
                    ParameterSetpoint(
                        parameter_id="PRM100",
                        short_name="Temp",
                        intervals=[
                            Interval(value="25", unit={"id": "UNI1"}, row_id="ROW4"),
                            Interval(value="60", unit={"id": "UNI1"}, row_id="ROW5"),
                        ],
                    ),
                    ParameterSetpoint(
                        parameter_id="PRM200",
                        short_name="Speed",
                        intervals=[
                            Interval(value="500", unit={"id": "UNI2"}, row_id="ROW8"),
                            Interval(value="1500", unit={"id": "UNI2"}, row_id="ROW9"),
                        ],
                    ),
                ],
            )
        ],
    )

    # Default action (skip)
    override_skip = wf.build_override({"Temp": 25, "Speed": 500})
    assert isinstance(override_skip, CombinationOverride)
    assert override_skip.key == "PRG247776#PRM100#ROW4-PRG247776#PRM200#ROW8"
    assert override_skip.action == OverrideAction.SKIP
    assert override_skip.is_manual is None

    # Unskip with is_manual
    override_unskip = wf.build_override(
        {"Speed": 1500, "Temp": 60},
        action="unskip",
        is_manual=True,
    )
    assert override_unskip.key == "PRG247776#PRM100#ROW5-PRG247776#PRM200#ROW9"
    assert override_unskip.action == OverrideAction.UNSKIP
    assert override_unskip.is_manual is True

    # Invalid action
    with pytest.raises(ValueError, match="Invalid override action"):
        wf.build_override({"Temp": 25, "Speed": 500}, action="invalid")
