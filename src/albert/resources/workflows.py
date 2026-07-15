from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import AliasChoices, Field, PrivateAttr, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DataTemplateId,
    IntervalId,
    ParameterGroupId,
    ParameterId,
    RowId,
)
from albert.core.shared.models.base import BaseResource, EntityLink
from albert.core.shared.types import SerializeAsEntityLink
from albert.exceptions import AlbertException
from albert.resources.parameter_groups import ParameterGroup
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.units import Unit


class IntervalParameter(BaseAlbertModel):
    """A single intervalized parameter value flattened out of a workflow's interval data.

    This is not a platform entity. It is an internal helper that
    :class:`Workflow` builds (one per interval value of each intervalized parameter)
    so that :meth:`Workflow.get_interval_id` can look up the row ID that matches a
    given parameter name and value. You do not normally construct this yourself.

    Attributes
    ----------
    interval_param_name : str | None
        The name of the intervalized parameter (e.g. ``"Temperature"``).
    interval_id : IntervalId | None
        The row ID of this single interval value (e.g. ``"ROW1"``). These are the
        building blocks that :meth:`Workflow.get_interval_id` joins with ``X`` to
        form a composite interval ID.
    interval_value : str | None
        The value of this interval, as a string (e.g. ``"25"``).
    interval_unit : str | None
        The unit name for this interval value, if any (e.g. ``"C"``).

    See Also
    --------
    Workflow.get_interval_id : Uses these to resolve a composite interval ID.
    Interval : The source model each of these is derived from.
    """

    interval_param_name: str | None = Field(default=None)
    interval_id: IntervalId | None = Field(default=None)
    interval_value: str | None = Field(default=None)
    interval_unit: str | None = Field(default=None)


class Interval(BaseAlbertModel):
    """One value that an intervalized parameter is varied across.

    When a parameter is "intervalized" (tested at several values rather than a single
    setpoint), each of those values is represented by an :class:`Interval`. A list of
    them is placed on the parameter's :class:`ParameterSetpoint` via its ``intervals``
    field. The workflow then carries the resulting :class:`IntervalCombination` entries,
    one per interval (or per cartesian product of two intervalized parameters).

    Attributes
    ----------
    value : str
        The value of this interval. For Special parameters (Equipment, Consumables,
        Templates) this is the entity ID (e.g. ``"INVC191778"``). For Normal parameters
        this is a plain scalar string (e.g. ``"23"``). Required.
    name : str | None
        The display name of the interval value. Populated for Special parameters (e.g.
        ``"Pipette 0.01 -0.1 ml (10 - 100 μl)"``). ``None`` for Normal parameters.
    unit : Unit | None
        The unit of ``value``, where applicable. If given, the unit must have an ``id``.

    See Also
    --------
    ParameterSetpoint : Holds a list of intervals when a parameter is intervalized.
    Workflow.get_interval_id : Resolves interval values to a composite interval ID.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.workflows import Interval

        # A Normal parameter varied across two temperatures.
        low = Interval(value="25", unit={"id": "UNI1"})
        high = Interval(value="60", unit={"id": "UNI1"})
        ```
    """

    value: str | None = Field(default=None)
    name: str | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    row_id: RowId | None = Field(default=None, alias="rowId", exclude=True)

    @model_validator(mode="after")
    def validate_interval(self) -> Interval:
        if not self.value:
            raise ValueError("Interval: 'value' is required.")
        if self.unit and not getattr(self.unit, "id", None):
            raise ValueError("Interval: 'Unit.id' is required.")
        return self


class IntervalDetail(BaseAlbertModel):
    """A single parameter's contribution to an interval combination.

    This appears inside :class:`IntervalCombination` (as its ``interval_details``) to
    break a combination down into the individual parameters that make it up. It is
    read from the workflow endpoint; you do not construct it directly.

    Attributes
    ----------
    name : str
        The parameter name (e.g. ``"Equipment"``).
    value : str
        The display value for this interval (e.g. ``"C191778 || Pipette 0.01 -0.1 ml"``).

    See Also
    --------
    IntervalCombination : The combination this detail belongs to.
    """

    name: str
    value: str


class IntervalCombination(BaseAlbertModel):
    """One realized condition (interval combination) carried by a workflow.

    Returned by the workflow endpoint when at least one parameter in the workflow has
    been intervalized. A combination is either a single intervalized parameter (interval
    ID ``ROW#``) or the cartesian product of two intervalized parameters (interval ID
    ``ROW#XROW#``). Its ``interval_id`` is what you pass to the property_data endpoints
    to read or write results for that specific condition.

    Attributes
    ----------
    interval_id : IntervalId | None
        The interval ID this combination is associated with. It has the form ``ROW#``
        for a single interval or ``ROW#XROW#`` for a product of two intervals. This is
        the same value :meth:`Workflow.get_interval_id` returns.
    interval_params : str | None
        The parameters participating in the interval.
    interval_string : str | None
        A human-readable representation of the combination, of the form
        ``"[Parameter Name]: [Parameter Value] [Parameter Unit]"`` for each parameter.
    interval_details : list[IntervalDetail] | None
        Per-parameter breakdown of the combination. Each entry has ``name``
        (parameter name) and ``value`` (display string, e.g. ``"C191778 || Pipette ..."``).

    See Also
    --------
    Workflow : Carries a list of these on its ``interval_combinations`` field.
    Workflow.get_interval_id : Builds the ``interval_id`` from parameter values.
    IntervalDetail : The per-parameter breakdown held in ``interval_details``.
    """

    interval_id: IntervalId | None = Field(default=None, alias="interval")
    interval_params: str | None = Field(default=None, alias="intervalParams")
    interval_string: str | None = Field(default=None, alias="intervalString")
    interval_details: list[IntervalDetail] | None = Field(default=None, alias="intervalDetails")


class ParameterSetpoint(BaseAlbertModel):
    """The fixed value (or set of interval values) for one parameter within a workflow.

    A setpoint pins a single parameter to a condition. Provide either a single ``value``
    (plus ``unit`` where applicable) for a fixed setpoint, or a list of ``intervals`` to
    intervalize the parameter across several values. You must identify the parameter by
    passing either a full ``parameter`` object or its ``parameter_id``. Setpoints are
    grouped under a :class:`ParameterGroupSetpoints`, which is in turn placed on a
    :class:`Workflow`.

    Normal parameters take exactly one of ``value`` or ``intervals``. Special parameters
    (Equipment, Consumables, Templates) take an entity ID as their value.

    Attributes
    ----------
    parameter : Parameter | None
        The parameter to set. Provide either ``parameter`` or ``parameter_id``. If both
        are given they must refer to the same parameter.
    parameter_id : ParameterId | None
        The ID of the parameter (e.g. ``"PRM1"``). Provide either ``parameter`` or
        ``parameter_id``.
    value : str | dict | EntityLink | None
        The value of the setpoint. For a Special parameter (an inventory item), provide
        the item's :class:`~albert.core.shared.models.base.EntityLink` (or a mapping with
        an ``id``). Mutually exclusive with ``intervals`` for Normal parameters.
    unit : Unit | None
        The unit of ``value``, where applicable.
    intervals : list[Interval] | None
        The interval values when the parameter is intervalized. Provide either
        ``intervals`` or ``value`` (plus ``unit``), not both.
    category : ParameterCategory | None
        The category of the parameter: ``SPECIAL`` for an inventory item (Equipment,
        Consumable, Template), ``NORMAL`` for everything else.
    short_name : str | None
        The short / display name of the parameter. Required if ``value`` is a mapping.
    name : str | None
        The parameter name. Auto-filled from ``parameter`` when one is provided.
    row_id : RowId | None
        Read-only. The row ID of this parameter with respect to its interval row.
    sequence : str | None
        Ordering key; needed because a Parameter Group can be repeated within a
        workflow. Not required when writing (PUT).

    See Also
    --------
    ParameterGroupSetpoints : Groups setpoints under one parameter group.
    Interval : The interval values supplied to ``intervals``.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.workflows import ParameterSetpoint, Interval

        # A single fixed setpoint identified by parameter ID.
        temp = ParameterSetpoint(parameter_id="PRM1", value="25", short_name="Temp")

        # The same parameter intervalized across two values.
        temp_varied = ParameterSetpoint(
            parameter_id="PRM1",
            short_name="Temp",
            intervals=[
                Interval(value="25", unit={"id": "UNI1"}),
                Interval(value="60", unit={"id": "UNI1"}),
            ],
        )
        ```
    """

    parameter: Parameter | None = Field(exclude=True, default=None)
    value: str | dict[str, Any] | EntityLink | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    parameter_id: ParameterId | None = Field(alias="id", default=None)
    intervals: list[Interval] | None = Field(default=None, alias="Intervals")
    category: ParameterCategory | None = Field(default=None)
    short_name: str | None = Field(default=None, alias="shortName")
    name: str | None = Field(default=None, exclude=True)
    row_id: RowId | None = Field(default=None, alias="rowId", frozen=True, exclude=True)
    sequence: str | None = Field(default=None, alias="prgPrmRowId")

    @model_validator(mode="after")
    def validate_shape(self) -> ParameterSetpoint:
        def has_id(obj: Any) -> bool:
            if isinstance(obj, Mapping):
                return bool(obj.get("id"))
            return getattr(obj, "id", None) not in (None, "")

        if self.parameter:
            if self.parameter_id is not None and self.parameter_id != self.parameter.id:
                raise ValueError("Provided parameter_id does not match the parameter's id.")

            # Note: We use  __setattr__ here rather than doing the assignment
            # because `name` and `parameter_id` are pydantic field
            # and setting it will trigger the model validation again
            # causing an infinite recursion error

            object.__setattr__(self, "parameter_id", self.parameter.id)
            if not self.name:
                object.__setattr__(self, "name", self.parameter.name)

        if self.parameter_id is None:
            raise ValueError("Either parameter or parameter_id must be provided.")

        pid = self.parameter_id

        # Special Parameters
        if self.category == ParameterCategory.SPECIAL:
            if self.intervals is not None:
                # Intervalized special parameters (Equipment, Consumables, Templates) are valid;
                # each interval value is a plain entity ID string.
                return self
            if self.value is None:
                return self  # presence-only allowed
            if not has_id(self.value):
                raise ValueError(
                    f"Parameter {pid}: Special parameters require an object value with an 'id'."
                )
            return self

        # Normal Parameters
        # Exactly one of value / intervals
        if self.value is not None and self.intervals is not None:
            raise ValueError(f"Parameter {pid}: provide exactly one of 'value' or 'Intervals'.")

        # If value is mapping-shaped for Normal, it must include id (e.g., enum {id,...})
        if isinstance(self.value, Mapping) and not has_id(self.value):
            raise ValueError(f"Parameter {pid}: object-shaped 'value' must include an 'id'.")

        return self


class ParameterGroupSetpoints(BaseAlbertModel):
    """All parameter setpoints belonging to one Data Template or Parameter Group.

    A workflow is organized by group: each :class:`ParameterGroupSetpoints` names one
    Data Template or Parameter Group (by ``id`` or by a full ``parameter_group`` object)
    and carries the :class:`ParameterSetpoint` list for the parameters in it. A
    :class:`Workflow` holds one of these per group. Both the order of setpoints within a
    group and the order of groups within the workflow are part of what makes a workflow
    unique, so preserve the order you intend.

    Attributes
    ----------
    parameter_group : ParameterGroup | None
        The parameter group to set setpoints on. Provide either ``parameter_group`` or
        ``id``. If both are given they must refer to the same group.
    id : ParameterGroupId | DataTemplateId | None
        The ID of the parameter group (``PRG...``) or Data Template (``DAT...``). Provide
        either ``id`` or ``parameter_group``. Auto-filled from ``parameter_group`` when
        one is provided.
    parameter_group_name : str
        Read-only display name of the group (defaults to ``"Pre-linked Parameters"``).
    parameter_setpoints : list[ParameterSetpoint]
        The setpoints to apply to this group's parameters.
    row_id : RowId | None
        Read-only. The group's interval row ID.
    sequence : int | None
        Ordering key; needed because a Parameter Group can be repeated within a
        workflow. Not required when writing (PUT).

    See Also
    --------
    Workflow : Holds one of these per Data Template / Parameter Group.
    ParameterSetpoint : A single parameter's setpoint within this group.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.workflows import (
            ParameterGroupSetpoints,
            ParameterSetpoint,
        )

        group = ParameterGroupSetpoints(
            id="PRG1",
            parameter_setpoints=[
                ParameterSetpoint(parameter_id="PRM1", value="25", short_name="Temp"),
            ],
        )
        ```
    """

    parameter_group: ParameterGroup | None = Field(exclude=True, default=None)
    id: ParameterGroupId | DataTemplateId | None = Field(default=None, alias="id")
    parameter_group_name: str = Field(default="Pre-linked Parameters", alias="name", exclude=True)
    parameter_setpoints: list[ParameterSetpoint] = Field(default_factory=list, alias="Parameters")

    # READ ONLY
    row_id: RowId | None = Field(default=None, alias="rowId", frozen=True, exclude=True)
    sequence: int | None = Field(default=None, alias="prgSequence", frozen=True, exclude=True)

    @model_validator(mode="after")
    def validate_identifiers(self):
        if self.parameter_group is not None and getattr(self.parameter_group, "id", None) is None:
            raise ValueError("Provided parameter_group must include a non-null `id` attribute.")

        if (
            self.parameter_group is not None
            and self.id is not None
            and self.id != self.parameter_group.id
        ):
            raise ValueError(f"id mismatch: expected {self.parameter_group.id!r}, got {self.id!r}")

        if self.parameter_group is not None and self.id is None:
            object.__setattr__(self, "id", self.parameter_group.id)

        return self


class Workflow(BaseResource):
    """A specific set of parameter setpoints: the conditions a test runs under.

    A workflow (WFL) captures only the *conditions* of a test, not its results. It gathers
    the parameters that appear on a Data Template (for a measurement) together with all
    parameters from one or more Parameter Groups, each fixed to a value (a setpoint) and a
    unit where applicable. It does not include the Data Template's results / data columns.

    A workflow is uniquely identified by its full setpoint configuration: the value and
    unit of every setpoint, the order of parameters within each Data Template / Parameter
    Group, and the order of those groups within the workflow. For this reason workflows are
    *found-or-created* rather than blindly created: build the object you want and pass it to
    :meth:`~albert.collections.workflows.WorkflowCollection.create`, which returns the
    existing match or makes a new one. IDs look like ``WFL...``.

    When one or two parameters are intervalized, the workflow acts as a *parent* that carries
    the resulting :class:`IntervalCombination` entries. Each combination has an interval ID of
    the form ``ROW1`` (one intervalized parameter) or ``ROW1XROW2`` (product of two). Use
    :meth:`get_interval_id` to build the interval ID for a condition, then use it with the
    property_data endpoints to read or write that condition's results.

    Attributes
    ----------
    name : str
        The name of the workflow.
    parameter_group_setpoints : list[ParameterGroupSetpoints]
        The setpoints to apply, organized one entry per Data Template / Parameter Group.
        The order of these entries is part of the workflow's identity.
    interval_combinations : list[IntervalCombination] | None
        The realized conditions when parameters are intervalized. Populated by the platform;
        present when the workflow is retrieved, not something you set when building one.
    id : str | None
        The Albert ID of the workflow (``WFL...``). Set when a workflow is created or
        retrieved from the platform.
    block_mapping : str | None
        Read-only / informational. When a Workflow is returned in the context of a
        block, this is hydrated for convenience.

    See Also
    --------
    ParameterGroupSetpoints : One group's worth of setpoints within the workflow.
    IntervalCombination : A single realized condition carried by an intervalized workflow.
    albert.collections.workflows.WorkflowCollection.create : Find-or-create a workflow.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        from albert.resources.workflows import (
            Workflow,
            ParameterGroupSetpoints,
            ParameterSetpoint,
        )

        client = Albert()
        workflow = Workflow(
            name="Cure at 25C",
            parameter_group_setpoints=[
                ParameterGroupSetpoints(
                    id="PRG1",
                    parameter_setpoints=[
                        ParameterSetpoint(parameter_id="PRM1", value="25", short_name="Temp"),
                    ],
                )
            ],
        )
        created = client.workflows.create(workflows=[workflow])
        created[0].id
        # 'WFL1'
        ```
    """

    name: str
    # NOTE: create() (POST /workflows/bulk) does not return ParameterGroups in the response.
    parameter_group_setpoints: list[ParameterGroupSetpoints] = Field(
        alias="ParameterGroups", default_factory=list
    )
    interval_combinations: list[IntervalCombination] | None = Field(
        default=None, alias="IntervalCombinations"
    )
    id: str | None = Field(
        alias="albertId",
        default=None,
        validation_alias=AliasChoices("albertId", "existingAlbertId"),
        exclude=True,
    )
    block_mapping: str | None = Field(default=None, alias="blockMapping")

    # post init fields
    _interval_parameters: list[IntervalParameter] = PrivateAttr(default_factory=list)
    category: str | None = Field(default=None, alias="category", exclude=True, frozen=True)

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
                                interval_unit=interval.unit.name if interval.unit else None,
                            )
                        )
        return self

    def get_interval_id(self, parameter_values: dict[str, Any]) -> str:
        """Build the composite interval ID for a set of parameter values.

        Matches each given parameter name and value against the workflow's intervalized
        parameters and assembles the corresponding interval ID. This is the ID you pass to
        the property_data endpoints to read or write results for that specific condition.
        For a single intervalized parameter the result is one row ID (``ROW1``); for two,
        the row IDs are joined with ``X`` (``ROW1XROW2``). Matching on value is
        case-insensitive to type: ``25`` and ``"25"`` both match an interval value of
        ``"25"``.

        Parameters
        ----------
        parameter_values : dict[str, Any]
            Mapping of parameter names to their values. Values may be numbers or strings
            and must match interval values defined on the workflow.

        Returns
        -------
        str
            The composite interval ID. A single interval ID for one parameter, or several
            joined with ``X`` for multiple (e.g. ``"ROW1XROW2"``).

        Raises
        ------
        AlbertException
            If any parameter value does not match a defined interval in the workflow.

        See Also
        --------
        IntervalCombination : The conditions whose interval IDs this method reproduces.

        Examples
        --------
        !!! example
            ```python
            # Single intervalized parameter
            workflow.get_interval_id({"Temperature": 25})
            # 'ROW1'

            # Two intervalized parameters (cartesian product)
            workflow.get_interval_id({"Temperature": 25, "Time": 60})
            # 'ROW1XROW2'

            # A value that matches no interval raises AlbertException
            workflow.get_interval_id({"Temperature": 999})
            # AlbertException: No matching interval found for parameter 'Temperature' ...
            ```
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
