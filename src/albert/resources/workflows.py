from pydantic import AliasChoices, Field, PrivateAttr, model_validator

from albert.exceptions import AlbertException
from albert.resources.base import BaseAlbertModel, BaseResource, EntityLink
from albert.resources.identifiers import IntervalId, ParameterGroupId, ParameterId, RowId
from albert.resources.parameter_groups import ParameterGroup
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.units import Unit


class IntervalParameter(BaseAlbertModel):
    """
    A class representing the interval parameter of a workflow.
    This is not a platform entity, but a helper class to make parsing
    the interval_combinations easier.

    Attributes
    ----------
    interval_param_name : str
        The name of the interval parameter.
    interval_id : IntervalId
        The id of the interval parameter.
    interval_value : str
        The value of the interval parameter.
    interval_unit : str
        The unit of the interval parameter.
    """

    interval_param_name: str | None = Field(default=None)
    interval_id: IntervalId | None = Field(default=None)
    interval_value: str | None = Field(default=None)
    interval_unit: str | None = Field(default=None)


class Interval(BaseAlbertModel):
    """A Pydantic class representing an interval.

    Attrubutes
    ----------
    value : str
        The value of the interval setpoint.
    unit : Unit
        The unit of the related value.

    """

    value: str | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    row_id: RowId | None = Field(default=None, alias="rowId")


class IntervalCombination(BaseAlbertModel):
    """A class representing the interval combinations of on a workflow.
    This is returned by the workflow endpoint when at least one parameter
    in the workflow has been intervalized.

    Interval Combinations can be single intervalized parameters or cartesian prodcuts of
    two intervalized parameters.

    Attributes
    ----------
    interval_id: IntervalId | None
        forign key reference to the interval id
        this combination is associated with
        It will have the form ROW# or ROW#XROW# depending on
        if it is a single interval or a product of two intervals
    interval_params: str | None
        The parameters participating in the interval.
    interval_string: str | None
        The string representation of the interval combination
        This will have the form "[Parameter Name]: [Parameter Value] [Parameter Unit]"
        for each parameter in the interval combination
    """

    interval_id: IntervalId | None = Field(default=None, alias="interval")
    interval_params: str | None = Field(default=None, alias="intervalParams")
    interval_string: str | None = Field(default=None, alias="intervalString")


class ParameterSetpoint(BaseAlbertModel):
    """A Pydantic class representing the setpoint or intervals of a parameter to use.
    For a single value, provide the value and unit. For multiple values, provide intervals.
    a parameter or parameter_id must be provided.

    Attributes
    ----------
    parameter : Parameter
        The parameter to set the setpoint on. Provide either a parameter or a parameter_id.
    parameter_id : ParameterId
        The id of the parameter. Provide either a parameter or a parameter_id.
    value : str | EntityLink
        The value of the setpoint. If the parameter is a InventoryItem, provide the EntityLink of the InventoryItem.
    unit : Unit
        The unit of the setpoint.
    intervals : list[Interval]
        The intervals of the setpoint. Either ether intervals or value + unit
    category : ParameterCategory
        The category of the parameter. Special for InventoryItem (then use name to specify "Equipment", "Consumeable", etc), normal for all others
    short_name : str
        The short / display name of the parameter. Required if value is a dictionary.
    row_id : RowId
        The id of the parameter with respect to the interval row id.
    """

    parameter: Parameter | None = Field(exclude=True, default=None)
    value: str | EntityLink | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    parameter_id: ParameterId | None = Field(alias="id", default=None)
    intervals: list[Interval] | None = Field(default=None, alias="Intervals")
    category: ParameterCategory | None = Field(default=None)
    short_name: str | None = Field(default=None, alias="shortName")
    name: str | None = Field(default=None, exclude=True)
    row_id: RowId | None = Field(default=None, alias="rowId")

    def model_post_init(self, __context) -> None:
        """
        Note:   We use post init here rather than doing the assignment
                in the validator because `name` is a pydantic field
                and setting it will trigger the model validation again
                causing an infinite recursion error
        """
        if self.parameter is not None and not self.name:
            self.name = self.parameter.name

    @model_validator(mode="after")
    def check_parameter_setpoint_validity(self):
        if self.parameter:
            if self.parameter_id is not None and self.parameter_id != self.parameter.id:
                raise ValueError("Provided parameter_id does not match the parameter's id.")
            if self.parameter_id is None:
                self.parameter_id = self.parameter.id
        elif self.parameter is None and self.parameter_id is None:
            raise ValueError("Either parameter or parameter_id must be provided.")
        if self.value is not None and self.intervals is not None:
            raise ValueError("Cannot provide both value and intervals.")
        if isinstance(self.value, dict) and self.short_name is None:
            raise ValueError("Please provide a short_name.")
        if isinstance(self.value, dict) and self.category is None:
            # Help the user out by setting the category to special if it's not set
            self.category = ParameterCategory.SPECIAL
        return self


class ParameterGroupSetpoints(BaseAlbertModel):
    """A class that represents the setpoints on a parameter group.


    Attributes
    ----------
    parameter_group : ParameterGroup
        The parameter group to set the setpoints on. Provide either a parameter_group or a paramerter_group_id
    parameter_group_id : ParameterGroupId
        The id of the parameter group.  Provide either a parameter_group or a paramerter_group_id
    parameter_group_name : str
        The name of the parameter group. This is a read-only field.
    parameter_setpoints : list[ParameterSetpoint]
        The setpoints to apply to the parameter group.
    """

    parameter_group: ParameterGroup | None = Field(exclude=True, default=None)
    parameter_group_id: ParameterGroupId | None = Field(alias="id", default=None)
    parameter_group_name: str | None = Field(alias="name", default=None, frozen=True, exclude=True)
    parameter_setpoints: list[ParameterSetpoint] = Field(default_factory=list, alias="Parameters")

    @model_validator(mode="after")
    def validate_pg_setpoint(self):
        if self.parameter_group is not None:
            if self.parameter_group_id is not None:
                if self.parameter_group.id != self.parameter_group_id:
                    raise ValueError(
                        "Provided parameter_group_id does not match the parameter_group's id."
                    )
            else:
                self.parameter_group_id = self.parameter_group.id
        return self


class Workflow(BaseResource):
    """A Pydantic Class representing a workflow in Albert.

    Workflows are combinations of Data Templates and Parameter groups and their associated setpoints.

    Attributes
    ----------
    name : str
        The name of the workflow.
    parameter_group_setpoints : list[ParameterGroupSetpoints]
        The setpoints to apply to the parameter groups in the workflow.
    id : str | None
        The AlbertID of the workflow. This is set when a workflow is retrived from the platform.
    """

    name: str
    parameter_group_setpoints: list[ParameterGroupSetpoints] = Field(alias="ParameterGroups")
    interval_combinations: list[IntervalCombination] | None = Field(
        default=None, alias="IntervalCombinations"
    )
    id: str | None = Field(
        alias="albertId",
        default=None,
        validation_alias=AliasChoices("albertId", "existingAlbertId"),
        exclude=True,
    )

    # post init fields
    _interval_parameters: list[IntervalParameter] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context) -> None:
        self._populate_interval_parameters()

    def _populate_interval_parameters(self):
        for parameter_group_setpoint in self.parameter_group_setpoints:
            for parameter_setpoint in parameter_group_setpoint.parameter_setpoints:
                if parameter_setpoint.intervals is not None:
                    for interval in parameter_setpoint.intervals:
                        self._interval_parameters.append(
                            IntervalParameter(
                                interval_param_name=parameter_setpoint.name,
                                interval_id=interval.row_id,
                                interval_value=interval.value,
                                interval_unit=None
                                if interval.unit is None
                                else interval.unit.name,
                            )
                        )
        return self

    def get_interval_id(self, parameter_values: dict[str, any]) -> str:
        """Get the interval ID for a set of parameter values.

        This method matches parameter values to intervals defined in the workflow and constructs
        a composite interval ID. For multiple parameters, the interval IDs are joined with 'X'.

        Parameters
        ----------
        parameter_values : dict[str, any]
            Dictionary mapping parameter names to their values. Values can be numbers or strings
            that match the interval values defined in the workflow.

        Returns
        -------
        str
            The composite interval ID string. For a single parameter this is just the interval ID.
            For multiple parameters, interval IDs are joined with 'X' (e.g. "ROW1XROW2").

        Raises
        ------
        ValueError
            If any parameter value does not match a defined interval in the workflow.

        Examples
        --------
        >>> workflow = Workflow(...)
        >>> # Single parameter
        >>> workflow.get_interval_id({"Temperature": 25})
        'ROW1'
        >>> # Multiple parameters
        >>> workflow.get_interval_id({"Temperature": 25, "Time": 60})
        'ROW1XROW2'
        >>> # Non-matching value raises error
        >>> workflow.get_interval_id({"Temperature": 999})
        AlbertException: No matching interval found for parameter 'Temperature' with value '999'
        """
        interval_id = ""
        for param_name, param_value in parameter_values.items():
            matching_interval = None
            for workflow_interval in self._interval_parameters:
                if workflow_interval.interval_param_name.lower() == param_name.lower() and (
                    param_value == workflow_interval.interval_value
                    or str(param_value) == workflow_interval.interval_value
                ):
                    matching_interval = workflow_interval
                    break

            if matching_interval is None:
                raise AlbertException(
                    f"No matching interval found for parameter '{param_name}' with value '{param_value}'"
                )

            interval_id += (
                f"X{matching_interval.interval_id}"
                if interval_id != ""
                else matching_interval.interval_id
            )

        return interval_id
