from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from pydantic import validate_call

if TYPE_CHECKING:
    import requests

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import InventoryId, LotId, TaskId
from albert.exceptions import AlbertPartialError
from albert.resources.batch_data import (
    BatchData,
    BatchDataDesignRow,
    BatchDataLotUsage,
    BatchDataProduct,
    BatchDataRowCreated,
    BatchDataType,
    BatchValuePatchPayload,
    RawCostEntry,
    ReactionBatchData,
    ReactionCompleteResult,
    ReactionValuePatchPayload,
)


class BatchDataCollection(BaseCollection):
    """Manage Batch Data for Batch Tasks in the Albert platform.

    Batch Data is the tabular record behind a Batch Task
    ([`BatchTask`][albert.resources.tasks.BatchTask]): the grid that captures how a
    physical batch of a formulation was actually made. It is organized as:

    - **Rows** ([`BatchDataRow`][albert.resources.batch_data.BatchDataRow]): the
      formulation components (ingredients) that go into the batch, along with
      nested child rows for sub-formulas.
    - **Product columns** ([`BatchDataColumn`][albert.resources.batch_data.BatchDataColumn]):
      the batch/product being manufactured, carrying batch totals, reference
      totals, and any lot breakdowns.
    - **Values** ([`BatchDataValue`][albert.resources.batch_data.BatchDataValue]): the
      amount recorded for a given row within a given column.

    Batch Data is keyed by the Task ID of its Batch Task (format ``TAS...``); it
    is not a standalone catalog entity, so there is no free-text search. Retrieve
    it with [`get_by_id`][albert.collections.batch_data.BatchDataCollection.get_by_id] using the owning Task ID, initialize it for a task
    with [`create_batch_data`][albert.collections.batch_data.BatchDataCollection.create_batch_data], and record which lots were consumed with
    [`update_used_batch_amounts`][albert.collections.batch_data.BatchDataCollection.update_used_batch_amounts].

    This collection is accessed as ``client.batch_data``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        batch_data = client.batch_data.get_by_id(id="TAS123")
        for row in batch_data.rows or []:
            print(row.name)
        ```

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
        Get the batch data for a batch task by its ID.
    get_lookup_column(id) -> BatchData
        Get the lookup column data for a batch task.
    get_by_lot_id(id, max_items=...) -> Iterator[BatchDataLotUsage]
        Get the batch tasks and products that reference a lot.
    get_reaction(task_id) -> ReactionBatchData
        Get the reaction grid of a reaction batch task. (🧪 Beta)
    update_used_batch_amounts(task_id, patches) -> None
        Record which lots were used for the batch's recorded amounts.
    update_batch_size(task_id, formula_id, new_value, old_value) -> None
        Update the batch size of a batch task and rescale its amounts.
    back_update_from_design(design_id, patches) -> None
        Back-update batch data from changed design values.
    update_raw_cost(entries) -> None
        Recalculate the raw material cost of formula lots.
    resync(design_id, formula_id, col_id, task_id=..., total_updated_at=...) -> None
        Sync batch data with the formulation design grid.
    resync_task(task_id, design_id=..., value_sync=...) -> None
        Sync the batch data of a single batch task with its design.
    replace_design_row(design_id, row_id, inventory_id) -> None
        Replace the inventory of a design row across all batch tasks.
    update_reaction(task_id, patches) -> None
        Record reagent lot picks and product actuals on a reaction batch task. (🧪 Beta)
    complete_reaction(task_id) -> ReactionCompleteResult
        Complete a reaction batch task and create the output lot. (🧪 Beta)
    update_column_sequence(task_id, source_id, reference_id) -> None
        Move a product column after another column.
    add_products(id, products) -> None
        Add product, lookup, or block columns to the batch data grid.
    delete_products(id, products) -> None
        Remove columns from the batch data grid.
    reset_products(id, products) -> None
        Reset product columns to reflect a total change.
    add_design_rows(id, rows) -> list[BatchDataRowCreated]
        Add design rows to the batch data grid.
    delete(id) -> None
        Delete the batch data of a batch task.
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
        grid afterwards with [`get_by_id`][albert.collections.batch_data.BatchDataCollection.get_by_id].

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            batch_data = client.batch_data.create_batch_data(task_id="TAS123")
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the batch task to create batch data for
            (format ``TAS...``).

        Returns
        -------
        BatchData
            The created batch data entry.
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
        """Get the batch data for a batch task by its ID.

        Returns the batch data grid (rows, product columns, and recorded values)
        for the owning Batch Task ([`BatchTask`][albert.resources.tasks.BatchTask]).

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            batch_data = client.batch_data.get_by_id(id="TAS123")
            batch_data.size
            # 12
            ```

        Parameters
        ----------
        id : TaskId
            The identifier to look up, of the kind given by ``type``. By default
            this is the Task ID of the batch task (format ``TAS...``).
        type : BatchDataType, optional
            The kind of identifier passed as ``id``. Defaults to
            [`TASK_ID`][albert.resources.batch_data.BatchDataType.TASK_ID].
        limit : int, optional
            Maximum number of product columns to return per response (pagination
            is over columns, not rows). Defaults to 100.
        start_key : str, optional
            Pagination cursor identifying the first column to evaluate; pass the
            ``last_key`` from a previous response to continue where it left off.
        order_by : OrderBy, optional
            Direction in which results are sorted. Defaults to
            [`DESCENDING`][albert.core.shared.enums.OrderBy.DESCENDING].
            Currently has no effect on the returned grid.

        Returns
        -------
        BatchData
            The fully populated batch data.
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
        [`BatchValueId`][albert.resources.batch_data.BatchValueId] and describes the
        change with one or more
        [`BatchValuePatchDatum`][albert.resources.batch_data.BatchValuePatchDatum] entries.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import (
                BatchValueId,
                BatchValuePatchDatum,
                BatchValuePatchPayload,
            )

            client = Albert()

            # Step 1: add the lot's child row under the ingredient row. The lot
            # id goes on the datum's `lot_id`; `new_value` is the initial amount.
            add_lot = BatchValuePatchPayload(
                id=BatchValueId(row_id="ROW1", col_id="COL9999999"),
                data=[BatchValuePatchDatum(operation="add", lot_id="LOT123", new_value="0")],
            )
            client.batch_data.update_used_batch_amounts(task_id="TAS123", patches=[add_lot])

            # Step 2: re-read the grid, find the child row whose `id` is the lot,
            # and write the amount on it (parent rows reject value writes).
            grid = client.batch_data.get_by_id(id="TAS123")
            lot_row = next(
                child
                for row in grid.rows or []
                for child in row.child_rows or []
                if child.id == "LOT123"
            )
            write_amount = BatchValuePatchPayload(
                id=BatchValueId(row_id=lot_row.row_id, col_id="COL9999999"),
                data=[
                    BatchValuePatchDatum(
                        attribute="cell", operation="update", old_value="0", new_value="0.025"
                    )
                ],
            )
            client.batch_data.update_used_batch_amounts(task_id="TAS123", patches=[write_amount])
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        patches : list[BatchValuePatchPayload]
            Patch entries describing which batch values to update. To link a lot,
            set ``lot_id`` on the ``add`` datum, not on the payload.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{task_id}/values"
        self.session.patch(
            url,
            json=[
                patch.model_dump(exclude_none=True, by_alias=True, mode="json")
                for patch in patches
            ],
        )

    @staticmethod
    def _build_raw_cost_payload(entries: list[RawCostEntry]) -> list[dict[str, Any]]:
        """Assemble the raw cost body, nesting each entry's product and lot."""
        return [
            {
                "parentId": entry.task_id,
                **({"updatedAt": entry.updated_at} if entry.updated_at is not None else {}),
                "Product": {"id": entry.product_id, "lotId": entry.lot_id},
            }
            for entry in entries
        ]

    @staticmethod
    def _raise_on_partial_failure(response: requests.Response) -> None:
        """Raise AlbertPartialError when a partial success reports failed items."""
        if response.status_code != 206:
            return
        data = response.json()
        failed_items = data.get("FailedItems") if isinstance(data, dict) else data
        if failed_items:
            raise AlbertPartialError(
                f"Operation partially succeeded: {len(failed_items)} item(s) failed. "
                f"Failures: {failed_items}",
                failed_items=failed_items,
            )

    @validate_call
    def get_lookup_column(self, *, id: TaskId) -> BatchData:
        """Get the lookup column data for a batch task.

        Returns the batch data grid slice used by lookup columns, keyed by the
        owning Batch Task ([`BatchTask`][albert.resources.tasks.BatchTask]).

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            lookup = client.batch_data.get_lookup_column(id="TAS123")
            ```

        Parameters
        ----------
        id : TaskId
            The Task ID of the batch task (format ``TAS...``).

        Returns
        -------
        BatchData
            The lookup column batch data.
        """
        response = self.session.get(f"{self.base_path}/{id}/lookupColumn")
        return BatchData(**response.json())

    @validate_call
    def get_by_lot_id(
        self, *, id: LotId, max_items: int | None = None
    ) -> Iterator[BatchDataLotUsage]:
        """Get the batch tasks and products that reference a lot.

        Results are returned as a lazily paginated iterator of
        [`BatchDataLotUsage`][albert.resources.batch_data.BatchDataLotUsage] items.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            for usage in client.batch_data.get_by_lot_id(id="LOT123"):
                print(usage.task_id, usage.product.id)
            ```

        Parameters
        ----------
        id : LotId
            The Lot ID to look up (format ``LOT...``).
        max_items : int, optional
            Maximum number of usages to return in total. If None, returns all
            matching usages.

        Returns
        -------
        Iterator[BatchDataLotUsage]
            An iterator over the batch task and product pairs referencing the lot.
        """
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=f"{self.base_path}/lot/{id}",
            session=self.session,
            max_items=max_items,
            deserialize=lambda items: [BatchDataLotUsage(**item) for item in items],
        )

    @validate_call
    def update_batch_size(
        self,
        *,
        task_id: TaskId,
        formula_id: InventoryId,
        new_value: float,
        old_value: float,
    ) -> None:
        """Update the batch size of a batch task and rescale its amounts.

        Recalculates the reference amounts of the given formula's product column
        so they scale to the new batch size.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            client.batch_data.update_batch_size(
                task_id="TAS123", formula_id="INV456", new_value=100.0, old_value=50.0
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        formula_id : InventoryId
            The Inventory ID of the formula whose batch size changes
            (format ``INV...``).
        new_value : float
            The new batch size.
        old_value : float
            The previous batch size.

        Returns
        -------
        None
        """
        response = self.session.put(
            self.base_path,
            json={
                "parentId": task_id,
                "data": {"formulaId": formula_id, "oldValue": old_value, "newValue": new_value},
            },
        )
        self._raise_on_partial_failure(response)

    @validate_call
    def back_update_from_design(
        self, *, design_id: str, patches: list[BatchValuePatchPayload]
    ) -> None:
        """Back-update batch data from changed design values.

        Propagates value changes made in a formulation design grid to every batch
        task created from it. Each patch targets a design value via a
        [`BatchValueId`][albert.resources.batch_data.BatchValueId] carrying both
        ``row_id`` and ``col_id``, and describes the change with one or more
        [`BatchValuePatchDatum`][albert.resources.batch_data.BatchValuePatchDatum]
        entries. All patches must target the same design column.

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
                id=BatchValueId(row_id="ROW2", col_id="COL4"),
                data=[BatchValuePatchDatum(operation="update", old_value="1", new_value="2")],
            )
            client.batch_data.back_update_from_design(design_id="DES100", patches=[patch])
            ```

        Parameters
        ----------
        design_id : str
            The design ID of the formulation design whose values changed.
        patches : list[BatchValuePatchPayload]
            Patch entries describing the changed design values. Each ``id`` must
            set both ``row_id`` and ``col_id``.

        Returns
        -------
        None
        """
        response = self.session.put(
            self.base_path,
            json={
                "parentId": design_id,
                "data": [
                    patch.model_dump(exclude_none=True, by_alias=True, mode="json")
                    for patch in patches
                ],
            },
        )
        self._raise_on_partial_failure(response)

    @validate_call
    def update_raw_cost(self, *, entries: list[RawCostEntry]) -> None:
        """Recalculate the raw material cost of formula lots.

        For each [`RawCostEntry`][albert.resources.batch_data.RawCostEntry], the
        cost of the formula lot is recomputed from the amounts and costs of the
        ingredient lots consumed in the given batch task, divided by the batch
        size.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import RawCostEntry

            client = Albert()
            client.batch_data.update_raw_cost(
                entries=[RawCostEntry(task_id="TAS123", product_id="INV456", lot_id="LOT789")]
            )
            ```

        Parameters
        ----------
        entries : list[RawCostEntry]
            The formula lots to reprice, each with the batch task driving the
            recalculation.

        Returns
        -------
        None

        Raises
        ------
        AlbertPartialError
            If only some entries were repriced successfully.
        """
        response = self.session.patch(
            f"{self.base_path}/rawcost", json=self._build_raw_cost_payload(entries)
        )
        self._raise_on_partial_failure(response)

    @validate_call
    def resync(
        self,
        *,
        design_id: str,
        formula_id: InventoryId | list[InventoryId],
        col_id: str | list[str],
        task_id: TaskId | None = None,
        total_updated_at: str | None = None,
    ) -> None:
        """Sync batch data with the formulation design grid.

        Reconciles the batch data of every batch task created from the given
        design column(s) with the current design values, adding, updating, and
        removing rows and values as needed.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            client.batch_data.resync(design_id="DES100", formula_id="INV456", col_id="COL4")
            ```

        Parameters
        ----------
        design_id : str
            The design ID of the formulation design to sync from.
        formula_id : InventoryId | list[InventoryId]
            The Inventory ID(s) of the formula(s) to sync (format ``INV...``).
        col_id : str | list[str]
            The design column ID(s) to sync.
        task_id : TaskId, optional
            Restrict the sync to a single batch task (format ``TAS...``).
        total_updated_at : str, optional
            Optimistic concurrency timestamp (ISO 8601) for the design totals.

        Returns
        -------
        None

        Raises
        ------
        AlbertPartialError
            If only some tasks were synced successfully.
        """
        response = self.session.patch(
            f"{self.base_path}/resync",
            json={
                "Formula": {
                    "designId": design_id,
                    "taskId": task_id,
                    "formulaId": formula_id,
                    "colId": col_id,
                    "totalUpdatedAt": total_updated_at,
                }
            },
        )
        self._raise_on_partial_failure(response)

    @validate_call
    def resync_task(
        self, *, task_id: TaskId, design_id: str | None = None, value_sync: bool = False
    ) -> None:
        """Sync the batch data of a single batch task with its design.

        Reconciles the batch data grid of the given batch task with the current
        values of the formulation design it was created from. The design is
        inferred from the batch data when ``design_id`` is not given.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            client.batch_data.resync_task(task_id="TAS123", value_sync=True)
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the batch task to sync (format ``TAS...``).
        design_id : str, optional
            The design ID of the formulation design to sync from. Inferred from
            the batch data when omitted.
        value_sync : bool, optional
            Sync the formula values in addition to the grid structure. Defaults
            to False.

        Returns
        -------
        None
        """
        params = {
            "taskId": task_id,
            "designId": design_id,
            # The backend treats any present valueSync (even "false") as true.
            "valueSync": True if value_sync else None,
        }
        self.session.patch(f"{self.base_path}/task/resync", params=params)

    @validate_call
    def replace_design_row(
        self, *, design_id: str, row_id: str, inventory_id: InventoryId
    ) -> None:
        """Replace the inventory of a design row across all batch tasks.

        Rewrites the batch data rows (and their values) created from the given
        design row so they reference the replacement inventory item.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            client.batch_data.replace_design_row(
                design_id="DES100", row_id="ROW2", inventory_id="INV789"
            )
            ```

        Parameters
        ----------
        design_id : str
            The design ID of the formulation design containing the row.
        row_id : str
            The design row ID whose inventory is replaced.
        inventory_id : InventoryId
            The Inventory ID of the replacement item (format ``INV...``).

        Returns
        -------
        None
        """
        self.session.patch(
            f"{self.base_path}/replace/row",
            json={"designId": design_id, "rowId": row_id, "inventoryId": inventory_id},
        )

    @validate_call
    def get_reaction(self, *, task_id: TaskId) -> ReactionBatchData:
        """Get the reaction grid of a reaction batch task.

        (🧪 Beta) Requires the reaction batch task feature to be enabled for the
        tenant.

        Returns each reaction's reagents (with their picked lots) and products
        (with their actual amounts). An empty ``reactions`` list means the
        reaction snapshot has not been created for the task yet.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            grid = client.batch_data.get_reaction(task_id="TAS123")
            for reaction in grid.reactions:
                for reagent in reaction.reagents:
                    print(reagent.name, reagent.total_used)
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the reaction batch task (format ``TAS...``).

        Returns
        -------
        ReactionBatchData
            The fully populated reaction grid.
        """
        response = self.session.get(f"{self.base_path}/reaction", params={"taskId": task_id})
        return ReactionBatchData(**response.json())

    @validate_call
    def update_reaction(
        self, *, task_id: TaskId, patches: list[ReactionValuePatchPayload]
    ) -> None:
        """Record reagent lot picks and product actuals on a reaction batch task.

        (🧪 Beta) Requires the reaction batch task feature to be enabled for the
        tenant.

        Applies patch entries that pick lots for reagents and record amounts and
        sub IDs on the reaction grid. Picking a lot moves inventory immediately;
        each patch targets a reagent or product via a
        [`ReactionValueId`][albert.resources.batch_data.ReactionValueId] and
        describes the change with one or more
        [`ReactionValuePatchDatum`][albert.resources.batch_data.ReactionValuePatchDatum]
        entries. A task that is Completed or Closed rejects further changes.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import (
                ReactionLotPick,
                ReactionValueId,
                ReactionValuePatchDatum,
                ReactionValuePatchPayload,
            )

            client = Albert()
            patch = ReactionValuePatchPayload(
                id=ReactionValueId(reaction_id="RXN1826", stt_id="STT1f13"),
                data=[
                    ReactionValuePatchDatum(
                        operation="add",
                        attribute="lot",
                        new_value=ReactionLotPick(lot_id="LOT123", amt=2.5, unit="g"),
                    )
                ],
            )
            client.batch_data.update_reaction(task_id="TAS123", patches=[patch])
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the reaction batch task to update (format ``TAS...``).
        patches : list[ReactionValuePatchPayload]
            Patch entries describing the lot picks and amount updates.

        Returns
        -------
        None

        Raises
        ------
        AlbertPartialError
            If only some patches were applied successfully.
        """
        response = self.session.patch(
            f"{self.base_path}/reaction/{task_id}",
            json=[
                patch.model_dump(exclude_none=True, by_alias=True, mode="json")
                for patch in patches
            ],
        )
        self._raise_on_partial_failure(response)

    @validate_call
    def complete_reaction(self, *, task_id: TaskId) -> ReactionCompleteResult:
        """Complete a reaction batch task and create the output lot.

        (🧪 Beta) Requires the reaction batch task feature to be enabled for the
        tenant.

        Creates the output lot for the reaction product from the recorded actual
        amounts and stamps the task completion date. Completion is idempotent:
        completing an already-completed task returns the existing output lot
        with ``replay`` set to ``True``.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            result = client.batch_data.complete_reaction(task_id="TAS123")
            result.lot_id
            # 'LOT98231'
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the reaction batch task to complete (format ``TAS...``).

        Returns
        -------
        ReactionCompleteResult
            The outcome of the completion, including the output lot.
        """
        response = self.session.post(f"{self.base_path}/reaction/{task_id}/complete")
        return ReactionCompleteResult(**response.json())

    @validate_call
    def update_column_sequence(
        self, *, task_id: TaskId, source_id: str, reference_id: str
    ) -> None:
        """Move a product column after another column in the batch data grid.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            client.batch_data.update_column_sequence(
                task_id="TAS123", source_id="COL4", reference_id="COL3"
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        source_id : str
            The ID of the column to move (format ``COL...``).
        reference_id : str
            The ID of the column after which the source column is placed
            (format ``COL...``).

        Returns
        -------
        None
        """
        self.session.patch(
            f"{self.base_path}/{task_id}",
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "colsequence",
                        "sourceId": source_id,
                        "referenceId": reference_id,
                    }
                ]
            },
        )

    @validate_call
    def add_products(self, *, id: TaskId, products: list[BatchDataProduct]) -> None:
        """Add product, lookup, or block columns to the batch data grid.

        Each [`BatchDataProduct`][albert.resources.batch_data.BatchDataProduct]
        identifies a column by its kind: set ``id`` for an inventory product
        column, ``id`` and ``name`` for a lookup column, or ``name`` alone to
        enable a Batch Instructions block column. Columns of different kinds
        cannot be mixed in one call.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import BatchDataProduct

            client = Albert()
            client.batch_data.add_products(id="TAS123", products=[BatchDataProduct(id="INV456")])
            ```

        Parameters
        ----------
        id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        products : list[BatchDataProduct]
            The columns to add.

        Returns
        -------
        None
        """
        self.session.post(
            f"{self.base_path}/{id}/products",
            json=[
                product.model_dump(exclude_none=True, by_alias=True, mode="json")
                for product in products
            ],
        )

    @validate_call
    def delete_products(self, *, id: TaskId, products: list[BatchDataProduct]) -> None:
        """Remove columns from the batch data grid.

        Each [`BatchDataProduct`][albert.resources.batch_data.BatchDataProduct]
        identifies a column to remove: set ``id`` for an inventory product or
        lookup column, or ``col_id`` for a Batch Instructions block column.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import BatchDataProduct

            client = Albert()
            client.batch_data.delete_products(id="TAS123", products=[BatchDataProduct(id="INV456")])
            ```

        Parameters
        ----------
        id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        products : list[BatchDataProduct]
            The columns to remove.

        Returns
        -------
        None

        Raises
        ------
        AlbertPartialError
            If only some columns were removed successfully.
        """
        response = self.session.delete(
            f"{self.base_path}/{id}/products",
            json=[
                product.model_dump(exclude_none=True, by_alias=True, mode="json")
                for product in products
            ],
        )
        self._raise_on_partial_failure(response)

    @validate_call
    def reset_products(self, *, id: TaskId, products: list[BatchDataProduct]) -> None:
        """Reset product columns to reflect a total change.

        Recreates the given inventory product columns so their recorded amounts
        match the current design totals. Each
        [`BatchDataProduct`][albert.resources.batch_data.BatchDataProduct] must
        set ``id`` to the Inventory ID of the product (format ``INV...``).

        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import BatchDataProduct

            client = Albert()
            client.batch_data.reset_products(id="TAS123", products=[BatchDataProduct(id="INV456")])
            ```

        Parameters
        ----------
        id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        products : list[BatchDataProduct]
            The product columns to reset.

        Returns
        -------
        None
        """
        self.session.patch(
            f"{self.base_path}/{id}/products",
            json=[
                product.model_dump(exclude_none=True, by_alias=True, mode="json")
                for product in products
            ],
        )

    @validate_call
    def add_design_rows(
        self, *, id: TaskId, rows: list[BatchDataDesignRow]
    ) -> list[BatchDataRowCreated]:
        """Add design rows to the batch data grid.

        Adds one row per given design cell to the batch data of the owning batch
        task. The design cell must belong to the formulation design the task was
        created from, must hold a value, and must not already exist in the grid.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.batch_data import BatchDataDesign, BatchDataDesignRow

            client = Albert()
            created = client.batch_data.add_design_rows(
                id="TAS123",
                rows=[
                    BatchDataDesignRow(
                        design=BatchDataDesign(id="DES100", row_id="ROW2", col_id="COL4")
                    )
                ],
            )
            created[0].row_id
            # 'ROW101'
            ```

        Parameters
        ----------
        id : TaskId
            The Task ID of the batch task to update (format ``TAS...``).
        rows : list[BatchDataDesignRow]
            The design cells to add as rows.

        Returns
        -------
        list[BatchDataRowCreated]
            The added rows.
        """
        response = self.session.post(
            f"{self.base_path}/{id}/designs",
            json=[row.model_dump(exclude_none=True, by_alias=True, mode="json") for row in rows],
        )
        return [BatchDataRowCreated(**item) for item in response.json()]

    @validate_call
    def delete(self, *, id: TaskId) -> None:
        """Delete the batch data of a batch task.

        The batch data is soft-deleted: the grid is deactivated but remains
        recoverable. The owning Batch Task
        ([`BatchTask`][albert.resources.tasks.BatchTask]) itself is not deleted.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            client.batch_data.delete(id="TAS123")
            ```

        Parameters
        ----------
        id : TaskId
            The Task ID of the batch task whose batch data is deleted
            (format ``TAS...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")
