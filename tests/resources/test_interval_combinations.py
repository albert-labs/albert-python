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
