from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.parameter_groups import ParameterGroupCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import WorkflowId
from albert.resources.parameter_groups import DataType, ParameterValue
from albert.resources.workflows import ParameterSetpoint, Workflow


class WorkflowCollection(BaseCollection):
    """Manage Workflows in the Albert platform.

    A Workflow is a specific set of **parameter setpoints**, the conditions a
    test is run under. It pulls together the parameters that appear on a Data
    Template (for a measurement) together with all the parameters from one or more
    Parameter Groups, and fixes each to a value (a *setpoint*), plus a unit where
    applicable.

    A Workflow does **not** include the *results / data columns* of a Data
    Template: it describes conditions (parameters) only, never measured results.
    The results live on the Data Template and, once measured, in Property Data. A
    Workflow is also not itself a task: it becomes actionable when paired with a
    Data Template inside a *Block* on a Property or Batch Task (see
    :meth:`~albert.collections.tasks.TaskCollection.add_block`).

    **Uniqueness.** A Workflow is uniquely identified by its full setpoint
    configuration: the value (and unit) of every parameter setpoint, the order of
    the parameters within each Data Template / Parameter Group, and the order of
    the Data Templates / Parameter Groups within the workflow. Because of this,
    workflows are *found-or-created* rather than blindly created: to obtain a
    workflow ID, build the Workflow object you want and let :meth:`create` return
    the existing match or make a new one.

    **Intervals.** When one or two parameters are "intervalized" (varied across
    several values), the workflow acts as a *parent* that carries the resulting
    *interval combinations*. Each combination has an interval ID of the form
    ``ROW1`` (one intervalized parameter) or ``ROW1XROW2`` (the product of two).
    That interval ID is how you target a specific condition when reading or writing
    Property Data. Use
    :meth:`~albert.resources.workflows.Workflow.get_interval_id` to build the
    correct interval ID from parameter values.

    This collection is accessed as ``client.workflows``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for workflow requests.

    Methods
    -------
    create(workflows) -> list[Workflow]
        Find-or-create workflows, deduplicating by parameter setpoints.
    get_by_id(id) -> Workflow
        Retrieve a single workflow, including its full setpoints.
    get_by_ids(ids) -> list[Workflow]
        Retrieve multiple workflows by ID in batches.
    get_all(max_items=None) -> Iterator[Workflow]
        Iterate over all workflows (rarely needed in production).

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        wf = client.workflows.get_by_id(id="WFL1")
        # Build the interval ID for a specific condition, then use it with
        # client.property_data to read/write that interval's results.
        interval_id = wf.get_interval_id({"Temperature": 25})
        interval_id
        # 'ROW1'
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a WorkflowCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{WorkflowCollection._api_version}/workflows"

    def create(self, *, workflows: list[Workflow]) -> list[Workflow]:
        """Find or create workflows.

        This is the intended way to obtain a workflow ID: build the Workflow object
        you want and let this method return the existing match or create a new one.
        Workflows are deduplicated by their full setpoint configuration: the value
        and unit of every setpoint, the order of parameters within each Data
        Template / Parameter Group, and the order of those groups within the
        workflow. Any parameter group supplied by ID only is expanded to its full
        parameters before matching.

        Parameters
        ----------
        workflows : list[Workflow]
            The workflows to find or create. Each is built from parameter group
            setpoints (see :class:`~albert.resources.workflows.Workflow`).

        Returns
        -------
        list[Workflow]
            The created or matched workflows, in the same order as the input.

        Notes
        -----
        Returned workflows carry an empty ``parameter_group_setpoints`` list
        whether they were newly created or matched. Call :meth:`get_by_id` to
        fetch the full setpoints.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.workflows import (
                Workflow,
                ParameterGroupSetpoints,
                ParameterSetpoint,
            )
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
        if isinstance(workflows, Workflow):
            # in case the user forgets this should be a list
            workflows = [workflows]

        # Hydrate any parameter groups provided only by ID with their parameters
        for wf in workflows:
            self._hydrate_parameter_groups(workflow=wf)

        response = self.session.post(
            url=f"{self.base_path}/bulk",
            json=[
                x.model_dump(
                    mode="json",
                    by_alias=True,
                    exclude_none=True,
                    exclude={"created", "updated"},
                )
                for x in workflows
            ],
        )
        results = []
        for x in response.json():
            if "existingAlbertId" in x and "name" not in x:
                results.append(self.get_by_id(id=x["existingAlbertId"]))
            else:
                results.append(Workflow(**x))
        return results

    def _hydrate_parameter_groups(self, *, workflow: Workflow) -> None:
        """Ensure parameter setpoints are fully populated for each parameter group with an id.

        When setpoints are user-supplied, missing sequence values are back-filled to prevent
        mismatches when a parameter appears multiple times within the same group.
        """
        dt_collection = DataTemplateCollection(session=self.session)
        pg_collection = ParameterGroupCollection(session=self.session)
        for pg_setpoint in workflow.parameter_group_setpoints:
            pg_id = pg_setpoint.id
            if pg_id is None:
                continue

            if pg_id.upper().startswith("DAT"):
                group = dt_collection.get_by_id(id=pg_id)
                pg_setpoint.parameter_group_name = group.name
                params = group.parameter_values or []
            else:
                group = pg_collection.get_by_id(id=pg_id)
                pg_setpoint.parameter_group_name = group.name
                params = group.parameters or []

            if pg_setpoint.parameter_setpoints:
                # User supplied explicit setpoints, only fill in missing sequences.
                sequence_by_param_id = {pv.id: pv.sequence for pv in params if pv.id}
                for sp in pg_setpoint.parameter_setpoints:
                    if sp.sequence is None and sp.parameter_id in sequence_by_param_id:
                        sp.sequence = sequence_by_param_id[sp.parameter_id]
            else:
                pg_setpoint.parameter_setpoints = [
                    self._parameter_value_to_setpoint(pv) for pv in params
                ]

    @staticmethod
    def _parameter_value_to_setpoint(parameter_value: ParameterValue) -> ParameterSetpoint:
        """Convert a ParameterValue to a ParameterSetpoint."""

        value = parameter_value.value
        if (
            parameter_value.validation
            and len(parameter_value.validation) > 0
            and parameter_value.validation[0].datatype == DataType.ENUM
            and parameter_value.validation[0].value
        ):
            enum_options = parameter_value.validation[0].value
            match = next(
                (
                    option
                    for option in enum_options
                    if option.id == parameter_value.value or option.text == parameter_value.value
                ),
                None,
            )
            if match is not None:
                value = {"id": match.id, "value": match.text}

        return ParameterSetpoint(
            parameter_id=parameter_value.id,
            category=parameter_value.category,
            short_name=parameter_value.short_name,
            value=value,
            unit=parameter_value.unit,
            sequence=parameter_value.sequence,
        )

    @validate_call
    def get_by_id(self, *, id: WorkflowId) -> Workflow:
        """Retrieve a single workflow by its ID, including its full setpoints.

        Unlike the workflows returned by :meth:`create`, this includes the fully
        populated ``parameter_group_setpoints`` and any interval combinations.

        Parameters
        ----------
        id : WorkflowId
            The workflow ID (format ``WFL...``).

        Returns
        -------
        Workflow
            The fully populated workflow.

        Examples
        --------
        !!! example
            ```python
            wf = client.workflows.get_by_id(id="WFL1")
            wf.name
            # 'Cure at 25C'
            ```
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Workflow(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[WorkflowId]) -> list[Workflow]:
        """Retrieve multiple workflows by their IDs.

        Requests are automatically split into batches, so long ID lists are
        supported. Each returned workflow includes its full setpoints.

        Parameters
        ----------
        ids : list[WorkflowId]
            The workflow IDs to retrieve (format ``WFL...``).

        Returns
        -------
        list[Workflow]
            The matching workflows.

        Examples
        --------
        !!! example
            ```python
            workflows = client.workflows.get_by_ids(ids=["WFL1", "WFL2"])
            [w.name for w in workflows]
            # ['Cure at 25C', 'Cure at 40C']
            ```
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            Workflow(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def get_all(
        self,
        max_items: int | None = None,
    ) -> Iterator[Workflow]:
        """Iterate over all workflows.

        Workflows are usually retrieved by ID (via :meth:`get_by_id`) or created
        as part of building a task, so a full listing is rarely needed in
        production. Results are returned as a lazily paginated iterator.

        Parameters
        ----------
        max_items : int, optional
            Maximum number of workflows to return in total. If None, iterates over
            all workflows.

        Yields
        ------
        Workflow
            Each workflow, fully populated.

        Examples
        --------
        !!! example
            ```python
            for wf in client.workflows.get_all(max_items=10):
                print(wf.id, wf.name)
            ```
        """

        def deserialize(items: list[dict]) -> list[Workflow]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params={},
            session=self.session,
            deserialize=deserialize,
            max_items=max_items,
        )
