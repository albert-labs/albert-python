from pydantic import Field, model_validator

from albert.resources.base import BaseAlbertModel, BaseResource
from albert.resources.parameter_groups import ParameterGroup
from albert.resources.parameters import Parameter
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.units import Unit
from albert.utils.exceptions import AlbertException


class Interval(BaseAlbertModel):
    """A Pydantic class representing an interval.

    Attrubutes
    ----------
    value : str
        The value of the interval setpoint.
    unit : Unit
        The unit of the related value.

    """

    value: str = Field(default=None)
    unit: SerializeAsEntityLink[Unit] = Field(default=None, alias="Unit")


class ParameterSetpoint(BaseAlbertModel):
    """A Pydantic class representing the setpoint or intervals of a parameter to use.
    For a single value, provide the value and unit. For multiple values, provide intervals.
    a parameter or parameter_id must be provided.

    Attributes
    ----------
    parameter : Parameter
        The parameter to set the setpoint on. Provide either a parameter or a parameter_id.
    parameter_id : str
        The id of the parameter. Provide either a parameter or a parameter_id.
    value : str | dict[str, str]
        The value of the setpoint. If the parameter is a InventoryItem, provide a dictionary of values.
    unit : Unit
        The unit of the setpoint.
    intervals : list[Interval]
        The intervals of the setpoint. Either ether intervals or value + unit

    """

    parameter: Parameter = Field(exclude=True, default=None)
    value: str | dict[str, str] = Field(default=None)
    unit: SerializeAsEntityLink[Unit] = Field(default=None, alias="Unit")
    parameter_id: str = Field(alias="id", default=None)
    intervals: list[Interval] = Field(default=None, alias="Intervals")

    @model_validator(mode="after")
    def check_parameter_setpoint_validity(self):
        if self.parameter:
            if self.parameter_id is not None and self.parameter_id != self.parameter.id:
                raise AlbertException("Provided parameter_id does not match the parameter's id.")
            if self.parameter_id is None:
                self.parameter_id = self.parameter.id
        elif self.parameter is None and self.parameter_id is None:
            raise AlbertException("Either parameter or parameter_id must be provided.")
        if self.value is not None and self.intervals is not None:
            raise AlbertException("Cannot provide both value and intervals.")
        return self


class ParameterGroupSetpoints(BaseAlbertModel):
    """A class that represents the setpoints on a parameter group.


    Attributes
    ----------
    parameter_group : ParameterGroup
        The parameter group to set the setpoints on. Provide either a parameter_group or a paramerter_group_id
    parameter_group_id : str
        The id of the parameter group.  Provide either a parameter_group or a paramerter_group_id
    parameter_group_name : str
        The name of the parameter group. This is a read-only field.
    parameter_setpoints : list[ParameterSetpoint]
        The setpoints to apply to the parameter group.
    """

    parameter_group: ParameterGroup = Field(exclude=True, default=None)
    parameter_group_id: str = Field(alias="id", default=None)
    parameter_group_name: str = Field(alias="name", default=None, frozen=True, exclude=True)
    parameter_setpoints: list[ParameterSetpoint] = Field(alias="Parameters")

    @model_validator(mode="after")
    def validate_pg_setpoint(self):
        if self.parameter_group is not None:
            if self.parameter_group_id is not None:
                if self.parameter_group.id != self.parameter_group_id:
                    raise AlbertException(
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
    id: str | None = Field(alias="albertId", default=None)
