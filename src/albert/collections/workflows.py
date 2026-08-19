from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.parameter_groups import ParameterGroupCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode, Status
from albert.core.shared.identifiers import WorkflowId
from albert.core.utils import ensure_list
from albert.resources.parameter_groups import DataType, ParameterValue
from albert.resources.workflows import (
    ParameterSetpoint,
    Workflow,
    WorkflowParameterSet,
    WorkflowSearchItem,
)


class WorkflowCollection(BaseCollection):
    """Manage Workflows in the Albert platform.

    A Workflow is a grouping of **parameters and their setpoints**, the *independent
    variables* a test is run under. It is built from one or more groupings, where each
    grouping is either a Data Template with pre-linked parameters or a Parameter Group.
    A single Workflow can combine a Data Template's pre-linked parameters with one or
    more Parameter Groups, each contributing its own parameter setpoints (a value, plus
    a unit where applicable). Because a Data Template can carry pre-linked parameters, it
    is used here exactly like a Parameter Group: purely to describe parameters and their
    setpoints.

    A Workflow does **not** include a Data Template's **Data Columns** (also called
    *Results*). Those are the *dependent variables*, and they are recorded only in
    Property Data ([`PropertyDataCollection`][albert.collections.property_data.PropertyDataCollection]). In
    short, the Workflow holds the independent variables and Property Data holds the
    dependent ones. A Workflow is also not itself a task: it becomes actionable when
    paired with a Data Template inside a *Block* on a Property or Batch Task (see
    [`add_block`][albert.collections.tasks.TaskCollection.add_block]).

    **Uniqueness.** A Workflow is uniquely identified by its full setpoint
    configuration: the value (and unit) of every parameter setpoint, the order of
    the parameters within each Data Template / Parameter Group, and the order of
    the Data Templates / Parameter Groups within the workflow. Because of this,
    workflows are *found-or-created* rather than blindly created: to obtain a
    workflow ID, build the Workflow object you want and let [`create`][albert.collections.workflows.WorkflowCollection.create] return
    the existing match or make a new one.

    Every tenant also includes a built-in workflow ``WFL1`` ("No Parameter Group") with no
    parameter groups. Use it for tasks and blocks that do not involve parameter groups; it
    does not need to be created via
    [`create`][albert.collections.workflows.WorkflowCollection.create].

    **Intervals.** When one or two parameters are "intervalized" (varied across
    several values), the workflow acts as a *parent* that carries the resulting
    *interval combinations*. Each combination has an interval ID of the form
    ``ROW1`` (one intervalized parameter) or ``ROW1XROW2`` (the product of two).
    That interval ID is how you target a specific condition when reading or writing
    Property Data. Use
    [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id] to build the
    correct interval ID from parameter values.

    This collection is accessed as ``client.workflows``.

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
        Get a single workflow, including its full setpoints.
    get_by_ids(ids) -> list[Workflow]
        Get multiple workflows by their IDs in batches.
    get_all(max_items=None) -> Iterator[Workflow]
        Iterate over all workflows (rarely needed in production).
    search(...) -> Iterator[WorkflowSearchItem]
        Search for workflows matching the given filters.
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
        workflow. Any parameter group supplied by its ID only is expanded to its
        full parameters before matching.

        !!! example
            ```python
            from albert.resources.workflows import (
                Workflow,
                ParameterGroupSetpoints,
                ParameterSetpoint,
            )

            # A workflow combining a Data Template's pre-linked parameters (keyed by a
            # DAT... id, used just like a Parameter Group) with two Parameter Groups.
            workflow = Workflow(
                name="Tensile test at 23C, 50% RH",
                parameter_group_setpoints=[
                    ParameterGroupSetpoints(
                        id="DAT9999999",
                        parameter_setpoints=[
                            ParameterSetpoint(parameter_id="PRM9999999", value="23", short_name="Temperature"),
                            ParameterSetpoint(parameter_id="PRM2", value="50", short_name="Humidity"),
                        ],
                    ),
                    ParameterGroupSetpoints(
                        id="PRG9999999",
                        parameter_setpoints=[
                            ParameterSetpoint(parameter_id="PRM3", value="24", short_name="Cure Time"),
                        ],
                    ),
                    ParameterGroupSetpoints(
                        id="PRG2",
                        parameter_setpoints=[
                            ParameterSetpoint(parameter_id="PRM4", value="2000", short_name="Mix Speed"),
                        ],
                    ),
                ],
            )
            created = client.workflows.create(workflows=[workflow])
            created[0].id
            # 'WFL1'
            ```

        Parameters
        ----------
        workflows : list[Workflow]
            The workflows to find or create. Each is built from parameter group
            setpoints (see [`Workflow`][albert.resources.workflows.Workflow]).

        Returns
        -------
        list[Workflow]
            The created or matched workflows, in the same order as the input.

        Notes
        -----
        Returned workflows carry an empty ``parameter_group_setpoints`` list
        whether they were newly created or matched. Call [`get_by_id`][albert.collections.workflows.WorkflowCollection.get_by_id] to
        fetch the full setpoints.
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
        """Get a single workflow by its ID, including its full setpoints.

        Unlike the workflows returned by [`create`][albert.collections.workflows.WorkflowCollection.create], this includes the fully
        populated ``parameter_group_setpoints`` and any interval combinations.

        !!! example
            ```python
            wf = client.workflows.get_by_id(id="WFL1")
            wf.name
            # 'Cure at 25C'
            ```

        Parameters
        ----------
        id : WorkflowId
            The workflow ID (format ``WFL...``).

        Returns
        -------
        Workflow
            The fully populated workflow.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Workflow(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[WorkflowId]) -> list[Workflow]:
        """Get multiple workflows by their IDs.

        Requests are automatically split into batches, so long ID lists are
        supported. Each returned workflow includes its full setpoints.

        !!! example
            ```python
            workflows = client.workflows.get_by_ids(ids=["WFL1", "WFL2"])
            [w.name for w in workflows]
            # ['Cure at 25C', 'Cure at 40C']
            ```

        Parameters
        ----------
        ids : list[WorkflowId]
            The workflow IDs to retrieve (format ``WFL...``).

        Returns
        -------
        list[Workflow]
            The matching workflows.
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

        Workflows are usually retrieved by their IDs (via [`get_by_id`][albert.collections.workflows.WorkflowCollection.get_by_id]) or created
        as part of building a task, so a full listing is rarely needed in
        production. Results are returned as a lazily paginated iterator.

        !!! example
            ```python
            for wf in client.workflows.get_all(max_items=10):
                print(wf.id, wf.name)
            ```

        Parameters
        ----------
        max_items : int, optional
            Maximum number of workflows to return in total. If None, iterates over
            all workflows.

        Yields
        ------
        Workflow
            Each workflow, fully populated.
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

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        status: Status | list[Status] | None = None,
        created_by: str | list[str] | None = None,
        ids: WorkflowId | list[WorkflowId] | None = None,
        data_templates: str | list[str] | None = None,
        data_template_ids: str | list[str] | None = None,
        parameter_groups: str | list[str] | None = None,
        parameter_group_ids: str | list[str] | None = None,
        parameters: str | list[str] | None = None,
        unit: str | list[str] | None = None,
        parameter_set: list[WorkflowParameterSet] | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: str | list[str] | None = None,
        contains_text: str | list[str] | None = None,
        search_field: list[str] | None = None,
        source_field: list[str] | None = None,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        sort_by: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        max_items: int | None = None,
    ) -> Iterator[WorkflowSearchItem]:
        """Search for workflows matching the given filters.

        This is the fast path: it returns partial (unhydrated)
        [`WorkflowSearchItem`][albert.resources.workflows.WorkflowSearchItem] hits and is
        best for lookups, counts, and pulling IDs. To retrieve fully populated
        workflows, use [`get_by_id`][albert.collections.workflows.WorkflowCollection.get_by_id]
        or call `hydrate()` on a hit. Results are returned lazily as an iterator
        that pages through the API on demand.

        !!! example
            ```python
            for item in client.workflows.search(text="Tensile", max_items=10):
                print(item.id, item.name)
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query.
        status : Status or list[Status], optional
            Filter by workflow status.
        created_by : str or list[str], optional
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``).
        ids : WorkflowId or list[WorkflowId], optional
            Filter by workflow ID(s) (format ``WFL...``).
        data_templates : str or list[str], optional
            Filter by data template name(s).
        data_template_ids : str or list[str], optional
            Filter by data template ID(s) (format ``DAT...``).
        parameter_groups : str or list[str], optional
            Filter by parameter group name(s).
        parameter_group_ids : str or list[str], optional
            Filter by parameter group ID(s) (format ``PRG...``).
        parameters : str or list[str], optional
            Filter by parameter name(s). Supports inline range syntax such as
            ``name(value)``, ``name(>n)``, ``name(<n)``, or ``name(min-max)``.
        unit : str or list[str], optional
            Filter by unit name(s).
        parameter_set : list[WorkflowParameterSet], optional
            Filter by parameter constraints that bind a name, value range, and unit.
        facet_text : str, optional
            Text to match within a facet search.
        facet_field : str, optional
            Field to search within for facet filtering.
        contains_field : str or list[str], optional
            Field(s) to apply a "contains" search to.
        contains_text : str or list[str], optional
            Text value(s) for the "contains" search.
        search_field : list[str], optional
            Restrict which fields the text query searches.
        source_field : list[str], optional
            Restrict which fields are returned in search results.
        from_created_at : str, optional
            Only include workflows created on or after this date (ISO 8601).
        to_created_at : str, optional
            Only include workflows created on or before this date (ISO 8601).
        sort_by : str, optional
            Attribute to sort results by.
        order_by : OrderBy, optional
            The order in which to sort results. Default is ``DESCENDING``.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matching items.

        Returns
        -------
        Iterator[WorkflowSearchItem]
            A lazy iterator of matching partial workflows. Call
            `hydrate()` on an item to fetch its full
            [`Workflow`][albert.resources.workflows.Workflow].
        """
        payload: dict[str, Any] = {
            "limit": 100,
            "order": order_by,
            "text": text,
            "status": ensure_list(status),
            "createdBy": ensure_list(created_by),
            "albertId": ensure_list(ids),
            "dataTemplates": ensure_list(data_templates),
            "dataTemplateIds": ensure_list(data_template_ids),
            "parameterGroups": ensure_list(parameter_groups),
            "parameterGroupIds": ensure_list(parameter_group_ids),
            "parameters": ensure_list(parameters),
            "unit": ensure_list(unit),
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": ensure_list(contains_field),
            "containsText": ensure_list(contains_text),
            "searchField": ensure_list(search_field),
            "sourceField": ensure_list(source_field),
            "fromCreatedAt": from_created_at,
            "toCreatedAt": to_created_at,
            "sortBy": sort_by,
        }
        if parameter_set is not None:
            payload["parameterSet"] = [
                item.model_dump(by_alias=True, mode="json", exclude_none=True)
                for item in parameter_set
            ]

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            method="POST",
            json=payload,
            max_items=max_items,
            deserialize=lambda items: [
                WorkflowSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
        )
