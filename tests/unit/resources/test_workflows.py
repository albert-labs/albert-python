import pytest
from pydantic import ValidationError

from albert.resources.parameter_groups import ParameterGroup
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.workflows import (
    Interval,
    ParameterGroupSetpoints,
    ParameterSetpoint,
)


def test_interval_rejects_unit_without_id():
    """Test that an Interval's Unit must include an id."""
    with pytest.raises(ValidationError, match="Unit.id"):
        Interval(value="25", Unit={"name": "Celsius"})


def test_interval_accepts_unit_with_id():
    """Test that an Interval accepts a Unit that has an id."""
    interval = Interval(value="25", Unit={"id": "UNI1"})
    assert interval.unit.id == "UNI1"


def test_interval_accepts_no_unit():
    """Test that an Interval without a Unit is valid."""
    interval = Interval(value="25")
    assert interval.unit is None


def test_parameter_setpoint_requires_parameter_or_id():
    """Test that a ParameterSetpoint must be given a parameter or parameter_id."""
    with pytest.raises(ValidationError, match="parameter or parameter_id"):
        ParameterSetpoint(value="25")


def test_parameter_setpoint_populates_from_parameter():
    """Test that supplying a parameter object fills parameter_id and name."""
    parameter = Parameter(name="Temperature", albertId="PRM1", category="Normal")
    setpoint = ParameterSetpoint(parameter=parameter, value="25")
    assert setpoint.parameter_id == "PRM1"
    assert setpoint.name == "Temperature"


def test_parameter_setpoint_keeps_explicit_name_when_parameter_given():
    """Test that an explicitly provided name is not overwritten by the parameter's name."""
    parameter = Parameter(name="Temperature", albertId="PRM1", category="Normal")
    setpoint = ParameterSetpoint(parameter=parameter, value="25", name="Custom Name")
    assert setpoint.name == "Custom Name"


def test_parameter_setpoint_rejects_mismatched_parameter_id():
    """Test that a parameter_id conflicting with parameter.id is rejected."""
    parameter = Parameter(name="Temperature", albertId="PRM1", category="Normal")
    with pytest.raises(ValidationError, match="does not match"):
        ParameterSetpoint(parameter=parameter, id="PRM2", value="25")


def test_parameter_setpoint_special_intervals_skip_value_check():
    """Test that a Special parameter with intervals does not require a value id."""
    setpoint = ParameterSetpoint(
        parameter_id="PRM1",
        category=ParameterCategory.SPECIAL,
        intervals=[{"value": "INV1"}],
    )
    assert setpoint.intervals[0].value == "INV1"


def test_parameter_setpoint_special_none_value_allowed():
    """Test that a Special parameter with no value is allowed (presence-only)."""
    setpoint = ParameterSetpoint(parameter_id="PRM1", category=ParameterCategory.SPECIAL)
    assert setpoint.value is None


def test_parameter_setpoint_special_value_without_id_rejected():
    """Test that a Special parameter's object value must include an id."""
    with pytest.raises(ValidationError, match="require an object value with an 'id'"):
        ParameterSetpoint(
            parameter_id="PRM1", category=ParameterCategory.SPECIAL, value={"name": "Oven"}
        )


def test_parameter_setpoint_special_non_mapping_value_without_id_attr_rejected():
    """Test that a Special parameter's non-mapping value with no id attribute is rejected."""
    with pytest.raises(ValidationError, match="require an object value with an 'id'"):
        ParameterSetpoint(
            parameter_id="PRM1", category=ParameterCategory.SPECIAL, value="oven-string"
        )


def test_parameter_setpoint_special_value_with_id_accepted():
    """Test that a Special parameter's object value with an id is accepted."""
    setpoint = ParameterSetpoint(
        parameter_id="PRM1", category=ParameterCategory.SPECIAL, value={"id": "INV1"}
    )
    assert setpoint.value == {"id": "INV1"}


def test_parameter_setpoint_normal_rejects_value_and_intervals_together():
    """Test that a Normal parameter cannot have both value and intervals."""
    with pytest.raises(ValidationError, match="exactly one of"):
        ParameterSetpoint(
            parameter_id="PRM1",
            value="25",
            intervals=[{"value": "25"}],
        )


def test_parameter_setpoint_normal_mapping_value_requires_id():
    """Test that a Normal parameter's mapping-shaped value must include an id."""
    with pytest.raises(ValidationError, match="must include an 'id'"):
        ParameterSetpoint(parameter_id="PRM1", value={"name": "no-id"})


def test_parameter_setpoint_normal_string_value_accepted():
    """Test that a Normal parameter accepts a plain string value."""
    setpoint = ParameterSetpoint(parameter_id="PRM1", value="25")
    assert setpoint.value == "25"


def test_parameter_group_setpoints_requires_non_null_id_on_group():
    """Test that a parameter_group object must carry a non-null id."""

    group = ParameterGroup.model_construct(id=None, name="G")
    with pytest.raises(ValidationError, match="non-null `id`"):
        ParameterGroupSetpoints(parameter_group=group)


def test_parameter_group_setpoints_rejects_id_mismatch():
    """Test that a mismatched id and parameter_group.id is rejected."""

    group = ParameterGroup(albertId="PRG1", name="G")
    with pytest.raises(ValidationError, match="id mismatch"):
        ParameterGroupSetpoints(parameter_group=group, id="PRG2")


def test_parameter_group_setpoints_autofills_id_from_group():
    """Test that id is auto-filled from parameter_group when omitted."""

    group = ParameterGroup(albertId="PRG1", name="G")
    setpoints = ParameterGroupSetpoints(parameter_group=group)
    assert setpoints.id == "PRG1"


def test_parameter_group_setpoints_accepts_matching_id():
    """Test that a matching explicit id alongside parameter_group is accepted."""

    group = ParameterGroup(albertId="PRG1", name="G")
    setpoints = ParameterGroupSetpoints(parameter_group=group, id="PRG1")
    assert setpoints.id == "PRG1"
