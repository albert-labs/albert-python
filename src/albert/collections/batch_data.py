from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import TaskId
from albert.resources.batch_data import BatchData, BatchDataType, BatchValuePatchPayload


class BatchDataCollection(BaseCollection):
    """Manage Batch Data for Batch Tasks in the Albert platform.

    Batch Data is the tabular record behind a Batch Task
    (:class:`~albert.resources.tasks.BatchTask`): the grid that captures how a
    physical batch of a formulation was actually made. It is organized as:

    - **Rows** (:class:`~albert.resources.batch_data.BatchDataRow`): the
      formulation components (ingredients) that go into the batch, along with
      nested child rows for sub-formulas.
    - **Product columns** (:class:`~albert.resources.batch_data.BatchDataColumn`):
      the batch/product being manufactured, carrying batch totals, reference
      totals, and any lot breakdowns.
    - **Values** (:class:`~albert.resources.batch_data.BatchDataValue`): the
      amount recorded for a given row within a given column.

    Batch Data is keyed by the Task ID of its Batch Task (format ``TAS...``); it
    is not a standalone catalog entity, so there is no free-text search. Retrieve
    it with :meth:`get_by_id` using the owning Task ID, initialize it for a task
    with :meth:`create_batch_data`, and record which lots were consumed with
    :meth:`update_used_batch_amounts`.

    This collection is accessed as ``client.batch_data``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for batch data requests.

    Methods
    -------
    create_batch_data(task_id) -> BatchData
        Initialize the batch data entry for a batch task.
    get_by_id(id, type=..., limit=..., start_key=..., order_by=...) -> BatchData
        Retrieve the batch data for a batch task by its Task ID.
    update_used_batch_amounts(task_id, patches) -> None
        Record which lots were used for the batch's recorded amounts.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert

        client = Albert()
        batch_data = client.batch_data.get_by_id(id="TAS123")
        for row in batch_data.rows or []:
            print(row.name)
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a BatchDataCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{BatchDataCollection._api_version}/batchdata"

    @validate_call
    def create_batch_data(self, *, task_id: TaskId):
        """Initialize the batch data entry for a batch task.

        Sets up the empty batch data grid for the given Batch Task so that
        amounts and lots can subsequently be recorded. Retrieve the populated
        grid afterwards with :meth:`get_by_id`.

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the batch task to create batch data for
            (format ``TAS...``).

        Returns
        -------
        BatchData
            The created batch data entry.

        Examples
        --------
        !!! example
            ```python
            from albert import Albert

            client = Albert()
            batch_data = client.batch_data.create_batch_data(task_id="TAS123")
            ```
        """
        url = f"{self.base_path}"
        response = self.session.post(url, json={"parentId": task_id})
        return BatchData(**response.json())

    @validate_call
    def get_by_id(
        self,
        *,
        id: TaskId,
        type: BatchDataType = BatchDataType.TASK_ID,
        limit: int = 100,
        start_key: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> BatchData:
        """Retrieve the batch data for a batch task by its Task ID.

        Returns the batch data grid (rows, product columns, and recorded values)
        for the owning Batch Task (:class:`~albert.resources.tasks.BatchTask`).

        Parameters
        ----------
        id : TaskId
            The identifier to look up, of the kind given by ``type``. By default
            this is the Task ID of the batch task (format ``TAS...``).
        type : BatchDataType, optional
            The kind of identifier passed as ``id``. Defaults to
            :attr:`~albert.resources.batch_data.BatchDataType.TASK_ID`.
        limit : int, optional
            Maximum number of row entries to return per response. Defaults to 100.
        start_key : str, optional
            Pagination cursor identifying the first entry to evaluate; pass the
            ``last_key`` from a previous response to continue where it left off.
        order_by : OrderBy, optional
            Direction in which results are sorted. Defaults to
            :attr:`~albert.core.shared.enums.OrderBy.DESCENDING`.

        Returns
        -------
        BatchData
            The batch data for the task.

        Examples
        --------
        !!! example
            ```python
            from albert import Albert

            client = Albert()
            batch_data = client.batch_data.get_by_id(id="TAS123")
            batch_data.size
            # 12
            ```
        """
        params = {
            "id": id,
            "limit": limit,
            "type": type,
            "startKey": start_key,
            "orderBy": order_by,
        }
        response = self.session.get(self.base_path, params=params)
        return BatchData(**response.json())

    @validate_call
    def update_used_batch_amounts(
        self, *, task_id: TaskId, patches: list[BatchValuePatchPayload]
    ) -> None:
        """Record which lots were used for a batch task's recorded amounts.

        Applies patch entries that set the lot consumed for individual cells of
        the batch data grid, identified by their row (and optional column). Each
        patch targets a value via a
        :class:`~albert.resources.batch_data.BatchValueId` and describes the
        change with one or more
        :class:`~albert.resources.batch_data.BatchValuePatchDatum` entries.

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        patches : list[BatchValuePatchPayload]
            Patch entries describing which batch values to update and the lot to
            assign to each.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import (
                BatchValueId,
                BatchValuePatchDatum,
                BatchValuePatchPayload,
            )

            client = Albert()
            patch = BatchValuePatchPayload(
                id=BatchValueId(row_id="ROW1", col_id="COL1"),
                data=[
                    BatchValuePatchDatum(
                        operation="update",
                        new_value="LOT123",
                        old_value="LOT100",
                    )
                ],
            )
            client.batch_data.update_used_batch_amounts(task_id="TAS123", patches=[patch])
            ```
        """
        url = f"{self.base_path}/{task_id}/values"
        self.session.patch(
            url,
            json=[
                patch.model_dump(exclude_none=True, by_alias=True, mode="json")
                for patch in patches
            ],
        )
