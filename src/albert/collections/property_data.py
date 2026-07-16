from collections.abc import Iterator
from contextlib import suppress

import pandas as pd
from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import (
    BlockId,
    DataColumnId,
    DataTemplateId,
    IntervalId,
    InventoryId,
    LotId,
    SearchInventoryId,
    SearchProjectId,
    TaskId,
    UserId,
)
from albert.core.shared.models.patch import PatchOperation
from albert.core.utils import ensure_list
from albert.exceptions import NotFoundError
from albert.resources.property_data import (
    BulkPropertyData,
    CheckPropertyData,
    CurvePropertyValue,
    DataEntity,
    ImagePropertyValue,
    InventoryDataColumn,
    InventoryPropertyData,
    InventoryPropertyDataCreate,
    PropertyDataPatchDatum,
    PropertyDataSearchItem,
    ReturnScope,
    TaskPropertyCreate,
    TaskPropertyData,
)
from albert.utils import property_data as property_data_utils


class PropertyDataCollection(BaseCollection):
    """Manage Property Data in the Albert platform.

    Property Data is the actual measured result values in Albert. It lives in two
    places, and this collection covers both:

    - **On a Task**: the results captured when a Property Task is executed,
      organized per Block, interval combination, and trial. Task methods here are
      named ``*_task_*`` / ``*_interval_*`` / ``*_trial_*``.
    - **On an Inventory Item**: properties attached directly to a material.
      Inventory methods here are named ``*_on_inventory``. Task-measured results
      roll up to the associated inventory item's properties.

    **Intervals and trials.** Within a Block, results are addressed by:

    - *Interval*: one specific combination of parameter setpoints (e.g. "measured
      at 25°C"). It is identified by an interval ID of the form ``ROW1`` (one
      intervalized parameter) or ``ROW1XROW2`` (two). Build this ID from parameter
      values with [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id], or
      list the intervals present on a task with [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data]. When a
      block has no intervalized parameters, use the literal ``"default"``.
    - *Trial*: one replicate measurement of a given interval, identified by an
      integer trial number.

    The void/unvoid methods mirror this hierarchy: void an entire task block, a
    single interval, or a single trial. Voided data is retained but excluded from
    results; unvoiding restores it.

    **Writing results.** Use [`add_properties_to_task`][albert.collections.property_data.PropertyDataCollection.add_properties_to_task] for brand-new values,
    [`update_or_create_task_properties`][albert.collections.property_data.PropertyDataCollection.update_or_create_task_properties] to upsert, and
    [`bulk_load_task_properties`][albert.collections.property_data.PropertyDataCollection.bulk_load_task_properties] to load a whole table at once. When adding
    trials, supply a trial number only for an existing trial; omit it to create a
    new trial, and create new trials one call at a time (loop for many).

    This collection is accessed as ``client.property_data``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        # Read every recorded result on a property task
        for block in client.property_data.get_all_task_properties(
            task_id="TASFOR1", with_data_only=True
        ):
            print(block.block_id, block.data)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for property data requests.

    Methods
    -------
    get_properties_on_inventory(inventory_id) -> InventoryPropertyData
        Get all properties attached to an inventory item.
    add_properties_to_inventory(inventory_id, properties) -> list[InventoryPropertyDataCreate]
        Add properties directly to an inventory item.
    update_property_on_inventory(inventory_id, property_data) -> InventoryPropertyData
        Update a property on an inventory item.
    get_task_block_properties(inventory_id, task_id, block_id, lot_id=None) -> TaskPropertyData
        Get the results in one task block for one inventory item.
    get_all_task_properties(task_id, with_data_only=False) -> list[TaskPropertyData]
        Get results across all block/inventory combinations of a task.
    check_for_task_data(task_id) -> list[CheckPropertyData]
        Report which block/interval combinations of a task have data.
    check_block_interval_for_data(block_id, task_id, interval_id) -> CheckPropertyData
        Report whether one block interval has data.
    add_properties_to_task(...) -> list[TaskPropertyData]
        Add new result values to a task block.
    update_property_on_task(task_id, patch_payload, ...) -> list[TaskPropertyData]
        Patch existing result values on a task.
    update_or_create_task_properties(...) -> list[TaskPropertyData]
        Upsert result values on a task block.
    bulk_load_task_properties(...) -> list[TaskPropertyData]
        Overwrite a task block's results from tabular data.
    bulk_delete_task_data(...) -> None
        Delete a task block's results.
    void_task_data(...) / unvoid_task_data(...) -> None
        Void/unvoid all results in a task block.
    void_interval_data(...) / unvoid_interval_data(...) -> None
        Void/unvoid the results of one interval combination.
    void_trial_data(...) / unvoid_trial_data(...) -> None
        Void/unvoid the results of one trial.
    search(...) -> Iterator[PropertyDataSearchItem]
        Search recorded property data across the platform.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a PropertyDataCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{PropertyDataCollection._api_version}/propertydata"

    @validate_call
    def get_properties_on_inventory(self, *, inventory_id: InventoryId) -> InventoryPropertyData:
        """Get all properties attached to an inventory item.

        This includes both task-measured results that have rolled up to the item
        and properties added directly to it. For results in the context of a
        specific task, use [`get_task_block_properties`][albert.collections.property_data.PropertyDataCollection.get_task_block_properties] instead.

        !!! example
            ```python
            props = client.property_data.get_properties_on_inventory(
                inventory_id="INVA1"
            )
            len(props.custom_property_data)
            # 3
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The inventory item to retrieve properties for (format ``INV...``).

        Returns
        -------
        InventoryPropertyData
            The item's properties, split into task-derived and directly-added data.
        """
        params = {"entity": "inventory", "id": [inventory_id]}
        response = self.session.get(url=self.base_path, params=params)
        response_json = response.json()
        return InventoryPropertyData(**response_json[0])

    @validate_call
    def add_properties_to_inventory(
        self, *, inventory_id: InventoryId, properties: list[InventoryDataColumn]
    ) -> list[InventoryPropertyDataCreate]:
        """Add properties directly to an inventory item.

        Use this for properties known independently of a task (e.g. a
        supplier-stated value). Each property targets a data column and carries a
        value. Properties are added one at a time and collected into the result.

        !!! example
            ```python
            from albert.resources.property_data import InventoryDataColumn
            props = client.property_data.add_properties_to_inventory(
                inventory_id="INVA1",
                properties=[InventoryDataColumn(data_column_id="DAC1", value="1.2")],
            )
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The inventory item to add properties to (format ``INV...``).
        properties : list[InventoryDataColumn]
            The properties to add. Each pairs a data column with a value.

        Returns
        -------
        list[InventoryPropertyDataCreate]
            The registered properties.
        """
        returned = []
        for p in properties:
            # Can only add one at a time.
            create_object = InventoryPropertyDataCreate(
                inventory_id=inventory_id, data_columns=[p]
            )
            response = self.session.post(
                self.base_path,
                json=create_object.model_dump(exclude_none=True, by_alias=True, mode="json"),
            )
            response_json = response.json()
            logger.info(response_json.get("message", None))
            returned.append(InventoryPropertyDataCreate(**response_json))
        return returned

    @validate_call
    def update_property_on_inventory(
        self, *, inventory_id: InventoryId, property_data: InventoryDataColumn
    ) -> InventoryPropertyData:
        """Update a property on an inventory item.

        Matches the existing property by its data column and updates its value. If
        the item has no value yet for that data column, the value is added.

        !!! example
            ```python
            from albert.resources.property_data import InventoryDataColumn
            updated = client.property_data.update_property_on_inventory(
                inventory_id="INVA1",
                property_data=InventoryDataColumn(data_column_id="DAC1", value="1.3"),
            )
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The inventory item to update (format ``INV...``).
        property_data : InventoryDataColumn
            The data column and new value to set.

        Returns
        -------
        InventoryPropertyData
            The item's properties after the update.
        """
        existing_properties = self.get_properties_on_inventory(inventory_id=inventory_id)
        existing_value = None
        for p in existing_properties.custom_property_data:
            if p.data_column.data_column_id == property_data.data_column_id:
                existing_value = (
                    p.data_column.property_data.value
                    if p.data_column.property_data.value is not None
                    else p.data_column.property_data.string_value
                    if p.data_column.property_data.string_value is not None
                    else str(p.data_column.property_data.numeric_value)
                    if p.data_column.property_data.numeric_value is not None
                    else None
                )
                existing_id = p.data_column.property_data.id
                break
        if existing_value is not None:
            payload = [
                PropertyDataPatchDatum(
                    operation=PatchOperation.UPDATE,
                    id=existing_id,
                    attribute="value",
                    new_value=property_data.value,
                    old_value=existing_value,
                )
            ]
        else:
            payload = [
                PropertyDataPatchDatum(
                    operation=PatchOperation.ADD,
                    id=existing_id,
                    attribute="value",
                    new_value=property_data.value,
                )
            ]

        self.session.patch(
            url=f"{self.base_path}/{inventory_id}",
            json=[x.model_dump(exclude_none=True, by_alias=True, mode="json") for x in payload],
        )
        return self.get_properties_on_inventory(inventory_id=inventory_id)

    @validate_call
    def get_task_block_properties(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        lot_id: LotId | None = None,
    ) -> TaskPropertyData:
        """Get the recorded results in one task block for one inventory item.

        This is the focused read for a single block/inventory (and optionally lot)
        combination. To sweep every combination on a task at once, use
        [`get_all_task_properties`][albert.collections.property_data.PropertyDataCollection.get_all_task_properties].

        !!! example
            ```python
            data = client.property_data.get_task_block_properties(
                inventory_id="INVA1", task_id="TASFOR1", block_id="BLK1"
            )
            data.block_id
            # 'BLK1'
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The inventory item whose results to read (format ``INV...``).
        task_id : TaskId
            The Property Task the block belongs to (format ``TAS...``).
        block_id : BlockId
            The block to read (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None (all lots).

        Returns
        -------
        TaskPropertyData
            The results in the block for the given inventory item, organized by
            interval and trial.
        """
        params = {
            "entity": "task",
            "blockId": block_id,
            "id": task_id,
            "inventoryId": inventory_id,
            "lotId": lot_id,
        }
        params = {k: v for k, v in params.items() if v is not None}

        response = self.session.get(url=self.base_path, params=params)
        response_json = response.json()
        return TaskPropertyData(**response_json[0])

    @validate_call
    def check_for_task_data(self, *, task_id: TaskId) -> list[CheckPropertyData]:
        """Report which block/interval combinations of a task have data.

        Returns one entry per block/interval/inventory combination on the task,
        each flagging whether data exists (``data_exists``) and carrying the
        ``interval_id`` you can pass to the void/unvoid or read methods. This is
        the easiest way to discover the interval IDs present on a task.

        !!! example
            ```python
            statuses = client.property_data.check_for_task_data(task_id="TASFOR1")
            [(s.block_id, s.interval_id, s.data_exists) for s in statuses]
            # [('BLK1', 'ROW1', True), ('BLK1', 'ROW2', False)]
            ```

        Parameters
        ----------
        task_id : TaskId
            The task to inspect (format ``TAS...``).

        Returns
        -------
        list[CheckPropertyData]
            The data status of each block/interval/inventory combination.
        """
        task_info = property_data_utils.get_task_from_id(session=self.session, id=task_id)

        params = {
            "entity": "block",
            "action": "checkdata",
            "parentId": task_id,
            "id": [x.id for x in task_info.blocks],
        }

        response = self.session.get(url=self.base_path, params=params)
        return [CheckPropertyData(**x) for x in response.json()]

    @validate_call
    def check_block_interval_for_data(
        self, *, block_id: BlockId, task_id: TaskId, interval_id: IntervalId
    ) -> CheckPropertyData:
        """Report whether one specific block interval has data.

        A single-interval version of [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data].

        !!! example
            ```python
            status = client.property_data.check_block_interval_for_data(
                block_id="BLK1", task_id="TASFOR1", interval_id="ROW1"
            )
            status.data_exists
            # True
            ```

        Parameters
        ----------
        block_id : BlockId
            The block to check (format ``BLK...``).
        task_id : TaskId
            The task the block belongs to (format ``TAS...``).
        interval_id : IntervalId
            The interval combination to check (e.g. ``"ROW1"``, ``"ROW1XROW2"``,
            or ``"default"``). See [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data] to list interval IDs.

        Returns
        -------
        CheckPropertyData
            The data status of the given block interval.
        """
        params = {
            "entity": "block",
            "action": "checkdata",
            "id": block_id,
            "parentId": task_id,
            "intervalId": interval_id,
        }

        response = self.session.get(url=self.base_path, params=params)
        return CheckPropertyData(response.json())

    @validate_call
    def get_all_task_properties(
        self, *, task_id: TaskId, with_data_only: bool = False
    ) -> list[TaskPropertyData]:
        """Get recorded results across all block/inventory combinations of a task.

        Sweeps every block/inventory/lot combination on the task and returns its
        results. For a single known combination, [`get_task_block_properties`][albert.collections.property_data.PropertyDataCollection.get_task_block_properties]
        is more direct.

        !!! example
            ```python
            blocks = client.property_data.get_all_task_properties(
                task_id="TASFOR1", with_data_only=True
            )
            [b.block_id for b in blocks]
            # ['BLK1', 'BLK2']
            ```

        Parameters
        ----------
        task_id : TaskId
            The task to retrieve results for (format ``TAS...``).
        with_data_only : bool, optional
            When True, skip combinations that have no recorded data. Defaults to
            False (every combination is returned).

        Returns
        -------
        list[TaskPropertyData]
            Results for each block/inventory/lot combination on the task.
        """
        all_info = []
        task_data_info = self.check_for_task_data(task_id=task_id)
        for combo_info in task_data_info:
            if with_data_only and not combo_info.data_exists:
                continue
            all_info.append(
                self.get_task_block_properties(
                    inventory_id=combo_info.inventory_id,
                    task_id=task_id,
                    block_id=combo_info.block_id,
                    lot_id=combo_info.lot_id,
                )
            )
        return all_info

    @validate_call
    def update_property_on_task(
        self,
        *,
        task_id: TaskId,
        patch_payload: list[PropertyDataPatchDatum],
        inventory_id: InventoryId | None = None,
        block_id: BlockId | None = None,
        lot_id: LotId | None = None,
        return_scope: ReturnScope = "task",
    ) -> list[TaskPropertyData]:
        """Patch existing result values on a task.

        This is the low-level update path: it applies a list of explicit patch
        operations to values that already exist. For most cases prefer
        [`update_or_create_task_properties`][albert.collections.property_data.PropertyDataCollection.update_or_create_task_properties] (upsert) or
        [`add_properties_to_task`][albert.collections.property_data.PropertyDataCollection.add_properties_to_task] (new values), which build the patches for
        you.

        !!! example
            ```python
            from albert.resources.property_data import PropertyDataPatchDatum
            from albert.core.shared.models.patch import PatchOperation
            patch = PropertyDataPatchDatum(
                operation=PatchOperation.UPDATE,
                id="PTD1",
                attribute="value",
                new_value="1.5",
                old_value="1.2",
            )
            client.property_data.update_property_on_task(
                task_id="TASFOR1", patch_payload=[patch]
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task to update (format ``TAS...``).
        patch_payload : list[PropertyDataPatchDatum]
            The patch operations to apply. Image and curve values cannot be updated
            here; use [`update_or_create_task_properties`][albert.collections.property_data.PropertyDataCollection.update_or_create_task_properties] for those.
        inventory_id : InventoryId | None, optional
            Required when return_scope="block".
        block_id : BlockId | None, optional
            Required when return_scope="block".
        lot_id : LotId | None, optional
            Optional context for combo fetches.
        return_scope : Literal["task", "block", "none"], optional
            Controls the response. "task" (default) returns all task properties,
            "block" returns only the affected block/inventory/lot combination, and "none" skips fetching data.

        Returns
        -------
        list[TaskPropertyData]
            The task's properties after the update, scoped per ``return_scope``.
        """
        if len(patch_payload) > 0:
            resolved_payload = property_data_utils.resolve_patch_payload(
                session=self.session,
                task_id=task_id,
                patch_payload=patch_payload,
            )
            self.session.patch(
                url=f"{self.base_path}/{task_id}",
                json=resolved_payload,
            )
        return property_data_utils.resolve_return_scope(
            task_id=task_id,
            return_scope=return_scope,
            inventory_id=inventory_id,
            block_id=block_id,
            lot_id=lot_id,
            prefetched_block=None,
            get_all_task_properties=self.get_all_task_properties,
            get_task_block_properties=self.get_task_block_properties,
        )

    @validate_call
    def void_task_data(
        self,
        *,
        task_id: TaskId,
        inventory_id: InventoryId,
        block_id: BlockId,
        lot_id: LotId | None = None,
    ) -> None:
        """Void all recorded results in a task block for one inventory item.

        Voided data is retained but excluded from results; restore it with
        [`unvoid_task_data`][albert.collections.property_data.PropertyDataCollection.unvoid_task_data]. To void a narrower scope, use
        [`void_interval_data`][albert.collections.property_data.PropertyDataCollection.void_interval_data] or [`void_trial_data`][albert.collections.property_data.PropertyDataCollection.void_trial_data].

        !!! example
            ```python
            client.property_data.void_task_data(
                task_id="TASFOR1", inventory_id="INVA1", block_id="BLK1"
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        inventory_id : InventoryId
            The inventory item whose results to void (format ``INV...``).
        block_id : BlockId
            The block to void (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.

        Returns
        -------
        None
        """
        payload = {
            "operation": "void",
            "by": "task",
            "id": task_id,
            "inventoryId": inventory_id,
            "blockId": block_id,
            "lotId": lot_id,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        self.session.patch(
            url=f"{self.base_path}/{task_id}",
            json=payload,
        )

    @validate_call
    def unvoid_task_data(
        self,
        *,
        task_id: TaskId,
        inventory_id: InventoryId,
        block_id: BlockId,
        lot_id: LotId | None = None,
    ) -> None:
        """Restore previously voided results in a task block for one inventory item.

        The inverse of [`void_task_data`][albert.collections.property_data.PropertyDataCollection.void_task_data].

        !!! example
            ```python
            client.property_data.unvoid_task_data(
                task_id="TASFOR1", inventory_id="INVA1", block_id="BLK1"
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        inventory_id : InventoryId
            The inventory item whose results to restore (format ``INV...``).
        block_id : BlockId
            The block to unvoid (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.

        Returns
        -------
        None
        """
        payload = {
            "operation": "unvoid",
            "by": "task",
            "id": task_id,
            "inventoryId": inventory_id,
            "blockId": block_id,
            "lotId": lot_id,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        self.session.patch(
            url=f"{self.base_path}/{task_id}",
            json=payload,
        )

    @validate_call
    def void_interval_data(
        self,
        *,
        task_id: TaskId,
        interval_id: str,
        inventory_id: InventoryId,
        block_id: BlockId,
        lot_id: LotId | None = None,
        data_template_id: DataTemplateId | None = None,
    ) -> None:
        """Void the results of one interval combination in a task block.

        Voided data is retained but excluded from results; restore it with
        [`unvoid_interval_data`][albert.collections.property_data.PropertyDataCollection.unvoid_interval_data].

        !!! example
            ```python
            client.property_data.void_interval_data(
                task_id="TASFOR1",
                interval_id="ROW1",
                inventory_id="INVA1",
                block_id="BLK1",
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        interval_id : str
            The interval combination to void (e.g. ``"ROW1"``, ``"ROW1XROW2"``).
            List a task's interval IDs with [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data], or build
            one with [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id].
        inventory_id : InventoryId
            The inventory item whose results to void (format ``INV...``).
        block_id : BlockId
            The block to void within (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.
        data_template_id : DataTemplateId, optional
            Limit voiding to a specific data template. Defaults to None (all).

        Returns
        -------
        None
        """
        payload = {
            "operation": "void",
            "by": "intervalCombination",
            "id": interval_id,
            "parentId": task_id,
            "inventoryId": inventory_id,
            "blockId": block_id,
            "lotId": lot_id,
            "dataTemplateId": data_template_id,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        self.session.patch(
            url=f"{self.base_path}/{task_id}",
            json=payload,
        )

    @validate_call
    def unvoid_interval_data(
        self,
        *,
        task_id: TaskId,
        interval_id: str,
        inventory_id: InventoryId,
        block_id: BlockId,
        lot_id: LotId | None = None,
        data_template_id: DataTemplateId | None = None,
    ) -> None:
        """Restore previously voided results of one interval combination.

        The inverse of [`void_interval_data`][albert.collections.property_data.PropertyDataCollection.void_interval_data].

        !!! example
            ```python
            client.property_data.unvoid_interval_data(
                task_id="TASFOR1",
                interval_id="ROW1",
                inventory_id="INVA1",
                block_id="BLK1",
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        interval_id : str
            The interval combination to restore (e.g. ``"ROW1"``, ``"ROW1XROW2"``).
            List a task's interval IDs with [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data].
        inventory_id : InventoryId
            The inventory item whose results to restore (format ``INV...``).
        block_id : BlockId
            The block to restore within (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.
        data_template_id : DataTemplateId, optional
            Limit unvoiding to a specific data template. Defaults to None (all).

        Returns
        -------
        None
        """
        payload = {
            "operation": "unvoid",
            "by": "intervalCombination",
            "id": interval_id,
            "parentId": task_id,
            "inventoryId": inventory_id,
            "blockId": block_id,
            "lotId": lot_id,
            "dataTemplateId": data_template_id,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        self.session.patch(
            url=f"{self.base_path}/{task_id}",
            json=payload,
        )

    @validate_call
    def void_trial_data(
        self,
        *,
        task_id: TaskId,
        interval_id: str,
        trial_number: int,
        inventory_id: InventoryId,
        block_id: BlockId,
        lot_id: LotId | None = None,
    ) -> None:
        """Void one trial (replicate) within an interval combination.

        The narrowest void scope: a single replicate measurement. Restore it with
        [`unvoid_trial_data`][albert.collections.property_data.PropertyDataCollection.unvoid_trial_data].

        !!! example
            ```python
            client.property_data.void_trial_data(
                task_id="TASFOR1",
                interval_id="ROW1",
                trial_number=2,
                inventory_id="INVA1",
                block_id="BLK1",
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        interval_id : str
            The interval combination the trial belongs to (e.g. ``"ROW1"``).
            List a task's interval IDs with [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data].
        trial_number : int
            The 1-based trial (replicate) number to void.
        inventory_id : InventoryId
            The inventory item whose result to void (format ``INV...``).
        block_id : BlockId
            The block to void within (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.

        Returns
        -------
        None
        """
        payload = [
            {
                "operation": "void",
                "by": "trial",
                "trial": trial_number,
                "id": interval_id,
                "inventoryId": inventory_id,
                "blockId": block_id,
                "lotId": lot_id,
            }
        ]
        payload = [{k: v for k, v in item.items() if v is not None} for item in payload]
        self.session.patch(
            url=f"{self.base_path}/{task_id}",
            json=payload,
        )

    @validate_call
    def unvoid_trial_data(
        self,
        *,
        task_id: TaskId,
        interval_id: str,
        trial_number: int,
        inventory_id: InventoryId,
        block_id: BlockId,
        lot_id: LotId | None = None,
    ) -> None:
        """Restore one previously voided trial (replicate).

        The inverse of [`void_trial_data`][albert.collections.property_data.PropertyDataCollection.void_trial_data].

        !!! example
            ```python
            client.property_data.unvoid_trial_data(
                task_id="TASFOR1",
                interval_id="ROW1",
                trial_number=2,
                inventory_id="INVA1",
                block_id="BLK1",
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        interval_id : str
            The interval combination the trial belongs to (e.g. ``"ROW1"``).
            List a task's interval IDs with [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data].
        trial_number : int
            The 1-based trial (replicate) number to restore.
        inventory_id : InventoryId
            The inventory item whose result to restore (format ``INV...``).
        block_id : BlockId
            The block to restore within (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.

        Returns
        -------
        None
        """
        payload = [
            {
                "operation": "unvoid",
                "by": "trial",
                "trial": trial_number,
                "id": interval_id,
                "inventoryId": inventory_id,
                "blockId": block_id,
                "lotId": lot_id,
            }
        ]
        payload = [{k: v for k, v in item.items() if v is not None} for item in payload]
        self.session.patch(
            url=f"{self.base_path}/{task_id}",
            json=payload,
        )

    @validate_call
    def add_properties_to_task(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        lot_id: LotId | None = None,
        properties: list[TaskPropertyCreate],
        return_scope: ReturnScope = "task",
    ) -> list[TaskPropertyData]:
        """Add new result values to a task block.

        This path is for **new** values only; to update existing values or upsert,
        use [`update_or_create_task_properties`][albert.collections.property_data.PropertyDataCollection.update_or_create_task_properties], and to overwrite a whole
        table use [`bulk_load_task_properties`][albert.collections.property_data.PropertyDataCollection.bulk_load_task_properties]. Each value targets a data
        column and an interval combination (build the interval ID with
        [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id]).

        !!! example
            ```python
            from albert.resources.property_data import TaskPropertyCreate, TaskDataColumn
            # Derive the required data column / template from the existing block
            block = client.property_data.get_task_block_properties(
                inventory_id="INVA1", task_id="TASFOR1", block_id="BLK1"
            )
            column = block.data[0].trials[0].data_columns[0]
            new_value = TaskPropertyCreate(
                interval_combination="default",
                data_column=TaskDataColumn(
                    data_column_id=column.id, column_sequence=column.sequence
                ),
                value="33.3",
                data_template=block.data_template,
            )
            client.property_data.add_properties_to_task(
                inventory_id="INVA1",
                task_id="TASFOR1",
                block_id="BLK1",
                properties=[new_value],
            )
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The inventory item the results are for (format ``INV...``).
        task_id : TaskId
            The task to add results to (format ``TAS...``).
        block_id : BlockId
            The block to add results to (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.
        properties : list[TaskPropertyCreate]
            The result values to add.
        return_scope : Literal["task", "block", "none"], optional
            Controls the response. "task" (default) returns all task properties,
            "block" returns only the affected block/inventory/lot combination, and "none" skips fetching data.

        Returns
        -------
        list[TaskPropertyData]
            The task's results after the add, scoped per ``return_scope``.

        Notes
        -----
        To add to an existing trial, set ``trial_number`` on the
        ``TaskPropertyCreate``; leave it unset to create a new trial. Create new
        trials one call at a time (loop for many) to avoid unexpected behavior.
        """
        params = {
            "blockId": block_id,
            "inventoryId": inventory_id,
            "lotId": lot_id,
            "autoCalculate": "true",
            "history": "true",
        }
        params = {k: v for k, v in params.items() if v is not None}
        payload = (
            property_data_utils.resolve_task_property_payload(
                session=self.session,
                task_id=task_id,
                block_id=block_id,
                properties=properties,
            )
            if any(
                isinstance(prop.value, ImagePropertyValue | CurvePropertyValue)
                for prop in properties
            )
            else [x.model_dump(exclude_none=True, by_alias=True, mode="json") for x in properties]
        )
        response = self.session.post(
            url=f"{self.base_path}/{task_id}",
            json=payload,
            params=params,
        )
        registered_properties = [
            TaskPropertyCreate(**x) for x in response.json() if "DataTemplate" in x
        ]
        existing_data_rows = self.get_task_block_properties(
            inventory_id=inventory_id, task_id=task_id, block_id=block_id, lot_id=lot_id
        )
        patches = property_data_utils.form_calculated_task_property_patches(
            existing_data_rows=existing_data_rows,
            properties=registered_properties,
        )
        if len(patches) > 0:
            return self.update_property_on_task(
                task_id=task_id,
                patch_payload=patches,
                return_scope=return_scope,
                inventory_id=inventory_id,
                block_id=block_id,
                lot_id=lot_id,
            )

        return property_data_utils.resolve_return_scope(
            task_id=task_id,
            return_scope=return_scope,
            inventory_id=inventory_id,
            block_id=block_id,
            lot_id=lot_id,
            prefetched_block=existing_data_rows,
            get_all_task_properties=self.get_all_task_properties,
            get_task_block_properties=self.get_task_block_properties,
        )

    @validate_call
    def update_or_create_task_properties(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        lot_id: LotId | None = None,
        properties: list[TaskPropertyCreate],
        return_scope: ReturnScope = "task",
    ) -> list[TaskPropertyData]:
        """Upsert result values on a task block.

        Updates values that already exist and adds those that do not, in a single
        call. This is the recommended general-purpose write method; use
        [`add_properties_to_task`][albert.collections.property_data.PropertyDataCollection.add_properties_to_task] when you know all values are new, or
        [`bulk_load_task_properties`][albert.collections.property_data.PropertyDataCollection.bulk_load_task_properties] to overwrite an entire table. Handles
        image and curve values, which [`update_property_on_task`][albert.collections.property_data.PropertyDataCollection.update_property_on_task] cannot.

        !!! example
            ```python
            from albert.resources.property_data import TaskPropertyCreate, TaskDataColumn
            block = client.property_data.get_task_block_properties(
                inventory_id="INVA1", task_id="TASFOR1", block_id="BLK1"
            )
            column = block.data[0].trials[0].data_columns[0]
            value = TaskPropertyCreate(
                interval_combination="default",
                data_column=TaskDataColumn(
                    data_column_id=column.id, column_sequence=column.sequence
                ),
                value="42",
                trial_number=1,
                data_template=block.data_template,
            )
            client.property_data.update_or_create_task_properties(
                inventory_id="INVA1",
                task_id="TASFOR1",
                block_id="BLK1",
                properties=[value],
            )
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The inventory item the results are for (format ``INV...``).
        task_id : TaskId
            The task to write to (format ``TAS...``).
        block_id : BlockId
            The block to write to (format ``BLK...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.
        properties : list[TaskPropertyCreate]
            The result values to update or create.
        return_scope : Literal["task", "block", "none"], optional
            Controls the response. "task" (default) returns all task properties,
            "block" returns only the affected block/inventory/lot combination, and "none" skips fetching data.

        Returns
        -------
        list[TaskPropertyData]
            The task's results after the upsert, scoped per ``return_scope``.

        Notes
        -----
        To target an existing trial, set ``trial_number`` on the
        ``TaskPropertyCreate``; leave it unset to create a new trial. Create new
        trials one call at a time (loop for many) to avoid unexpected behavior.
        """

        existing_data_rows = self.get_task_block_properties(
            inventory_id=inventory_id, task_id=task_id, block_id=block_id, lot_id=lot_id
        )
        update_patches, new_values = property_data_utils.form_existing_row_value_patches(
            session=self.session,
            task_id=task_id,
            block_id=block_id,
            existing_data_rows=existing_data_rows,
            properties=properties,
        )

        calculated_patches = property_data_utils.form_calculated_task_property_patches(
            existing_data_rows=existing_data_rows,
            properties=properties,
        )
        all_patches = update_patches + calculated_patches
        if len(new_values) > 0:
            if len(all_patches) > 0:
                self.update_property_on_task(
                    task_id=task_id,
                    patch_payload=all_patches,
                    return_scope="none",
                    inventory_id=inventory_id,
                    block_id=block_id,
                    lot_id=lot_id,
                )
            if any(
                isinstance(prop.value, ImagePropertyValue | CurvePropertyValue)
                for prop in new_values
            ):
                params = {
                    "blockId": block_id,
                    "inventoryId": inventory_id,
                }
                params = {k: v for k, v in params.items() if v is not None}
                payload = property_data_utils.resolve_task_property_payload(
                    session=self.session,
                    task_id=task_id,
                    block_id=block_id,
                    properties=new_values,
                )
                response = self.session.post(
                    url=f"{self.base_path}/{task_id}",
                    json=payload,
                    params=params,
                )
                registered_properties = [
                    TaskPropertyCreate(**x) for x in response.json() if "DataTemplate" in x
                ]
                existing_data_rows = self.get_task_block_properties(
                    inventory_id=inventory_id,
                    task_id=task_id,
                    block_id=block_id,
                    lot_id=lot_id,
                )
                patches = property_data_utils.form_calculated_task_property_patches(
                    existing_data_rows=existing_data_rows,
                    properties=registered_properties,
                )
                if len(patches) > 0:
                    return self.update_property_on_task(
                        task_id=task_id,
                        patch_payload=patches,
                        return_scope=return_scope,
                        inventory_id=inventory_id,
                        block_id=block_id,
                        lot_id=lot_id,
                    )
                return property_data_utils.resolve_return_scope(
                    task_id=task_id,
                    return_scope=return_scope,
                    inventory_id=inventory_id,
                    block_id=block_id,
                    lot_id=lot_id,
                    prefetched_block=existing_data_rows,
                    get_all_task_properties=self.get_all_task_properties,
                    get_task_block_properties=self.get_task_block_properties,
                )
            return self.add_properties_to_task(
                inventory_id=inventory_id,
                task_id=task_id,
                block_id=block_id,
                lot_id=lot_id,
                properties=new_values,
                return_scope=return_scope,
            )
        else:
            return self.update_property_on_task(
                task_id=task_id,
                patch_payload=all_patches,
                return_scope=return_scope,
                inventory_id=inventory_id,
                block_id=block_id,
                lot_id=lot_id,
            )

    def bulk_load_task_properties(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        property_data: BulkPropertyData,
        interval="default",
        lot_id: LotId = None,
        return_scope: ReturnScope = "task",
    ) -> list[TaskPropertyData]:
        """Overwrite a task block's results from tabular data.

        The fastest way to load a full table of results for one interval. Build the
        ``BulkPropertyData`` from a DataFrame with ``BulkPropertyData.from_dataframe``.

        .. warning::
            This overwrites any existing results for the targeted interval. Column
            names in the data must exactly match the data column names
            (case-sensitive).

        !!! example
            ```python
            from albert.resources.property_data import BulkPropertyData
            data = BulkPropertyData.from_dataframe(df=my_dataframe)
            results = client.property_data.bulk_load_task_properties(
                block_id="BLK1",
                inventory_id="INVA1",
                property_data=data,
                task_id="TASFOR291760",
            )
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory.
        task_id : TaskId
            The ID of the task.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId, optional
            The ID of the lot, by default None.
        interval : str, optional
            The interval combination to load into (e.g. ``"ROW1"``). Defaults to
            ``"default"``. Build it with
            [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id].
        property_data : BulkPropertyData
            Column-wise data holding all rows for a single interval. Create it with
            ``BulkPropertyData.from_dataframe``.
        return_scope : Literal["task", "block", "none"], optional
            Controls the response. "task" (default) returns all task properties,
            "block" returns only the affected block/inventory/lot combination, and "none" skips fetching data.

        Returns
        -------
        list[TaskPropertyData]
            The task's results after the load, scoped per ``return_scope``.
        """
        property_df = pd.DataFrame(
            {x.data_column_name: x.data_series for x in property_data.columns}
        )

        task_prop_data = self.get_task_block_properties(
            inventory_id=inventory_id, task_id=task_id, block_id=block_id, lot_id=lot_id
        )
        column_map = property_data_utils._get_column_map(
            dataframe=property_df,
            property_data=task_prop_data,
        )
        all_task_prop_create = property_data_utils._df_to_task_prop_create_list(
            dataframe=property_df,
            column_map=column_map,
            data_template_id=task_prop_data.data_template.id,
            interval=interval,
        )
        with suppress(NotFoundError):
            # This is expected if the task is new and has no data yet.
            self.bulk_delete_task_data(
                task_id=task_id,
                block_id=block_id,
                inventory_id=inventory_id,
                lot_id=lot_id,
                interval_id=interval,
            )
        return self.add_properties_to_task(
            inventory_id=inventory_id,
            task_id=task_id,
            block_id=block_id,
            lot_id=lot_id,
            properties=all_task_prop_create,
            return_scope=return_scope,
        )

    @validate_call
    def bulk_delete_task_data(
        self,
        *,
        task_id: TaskId,
        block_id: BlockId,
        inventory_id: InventoryId,
        lot_id: LotId | None = None,
        interval_id=None,
    ) -> None:
        """Delete a task block's results.

        Permanently removes results for the block/inventory combination (optionally
        narrowed to one interval). To hide data reversibly instead of deleting it,
        use the void methods ([`void_task_data`][albert.collections.property_data.PropertyDataCollection.void_task_data], [`void_interval_data`][albert.collections.property_data.PropertyDataCollection.void_interval_data]).

        !!! example
            ```python
            client.property_data.bulk_delete_task_data(
                task_id="TASFOR1", block_id="BLK1", inventory_id="INVA1"
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task to delete results from (format ``TAS...``).
        block_id : BlockId
            The block to delete results from (format ``BLK...``).
        inventory_id : InventoryId
            The inventory item whose results to delete (format ``INV...``).
        lot_id : LotId, optional
            A specific lot of the inventory item. Defaults to None.
        interval_id : IntervalId, optional
            Limit deletion to one interval combination (e.g. ``"ROW1"``). Defaults
            to None (all intervals in the block).

        Returns
        -------
        None
        """
        params = {
            "inventoryId": inventory_id,
            "blockId": block_id,
            "lotId": lot_id,
            "intervalRow": interval_id if interval_id != "default" else None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        self.session.delete(f"{self.base_path}/{task_id}", params=params)

    @validate_call
    def search(
        self,
        *,
        result: str | None = None,
        text: str | None = None,
        # Sorting/pagination
        order: OrderBy | None = None,
        sort_by: str | None = None,
        # Core platform identifiers
        inventory_ids: list[SearchInventoryId] | SearchInventoryId | None = None,
        project_ids: list[SearchProjectId] | SearchProjectId | None = None,
        lot_ids: list[LotId] | LotId | None = None,
        data_template_ids: DataTemplateId | list[DataTemplateId] | None = None,
        data_column_ids: DataColumnId | list[DataColumnId] | None = None,
        # Data structure filters
        category: list[DataEntity] | DataEntity | None = None,
        data_templates: list[str] | str | None = None,
        data_columns: list[str] | str | None = None,
        # Data content filters
        parameters: list[str] | str | None = None,
        parameter_group: list[str] | str | None = None,
        unit: list[str] | str | None = None,
        # User filters
        created_by: list[UserId] | UserId | None = None,
        task_created_by: list[UserId] | UserId | None = None,
        # Response customization
        return_fields: list[str] | str | None = None,
        return_facets: list[str] | str | None = None,
        # Pagination
        max_items: int | None = None,
    ) -> Iterator[PropertyDataSearchItem]:
        """Search recorded property data across the platform.

        Searches measured results platform-wide (not scoped to a single task) and
        returns lightweight search items. The ``result`` parameter accepts a
        compact result-query syntax for filtering by measured value under a
        condition. Results are returned as a lazily paginated iterator.

        !!! example
            ```python
            hits = client.property_data.search(
                data_columns="Viscosity", max_items=25
            )
            for item in hits:
                print(item)
            ```

        Parameters
        ----------
        result : str, optional
            Result-value query, e.g. ``"viscosity(<200)@temperature(25)"`` to find
            data where viscosity is under 200 measured at temperature 25.
        text : str, optional
            Free text search across all fields.
        order : OrderBy, optional
            Sort order (ascending/descending).
        sort_by : str, optional
            Field to sort results by.
        inventory_ids : SearchInventoryId or list[SearchInventoryId], optional
            Filter by inventory IDs.
        project_ids : SearchProjectId or list[SearchProjectId], optional
            Filter by project IDs.
        lot_ids : LotId or list[LotId], optional
            Filter by lot IDs.
        data_template_ids : DataTemplateId or list[DataTemplateId], optional
            Filter by data template IDs.
        data_column_ids : DataColumnId or list[DataColumnId], optional
            Filter by data column IDs.
        category : DataEntity or list[DataEntity], optional
            Filter by data entity categories.
        data_templates : str or list[str], optional
            Filter by data template names.
        data_columns : str or list[str], optional
            Filter by data column names.
        parameters : str or list[str], optional
            Filter by parameter names.
        parameter_group : str or list[str], optional
            Filter by parameter group names.
        unit : str or list[str], optional
            Filter by unit names.
        created_by : UserId or list[UserId], optional
            Filter by user IDs who created the data.
        task_created_by : UserId or list[UserId], optional
            Filter by user IDs who created the task.
        return_fields : str or list[str], optional
            Specific fields to return.
        return_facets : str or list[str], optional
            Specific facets to return.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[PropertyDataSearchItem]
            A lazily paginated iterator of matching property data search items.
        """

        def deserialize(items: list[dict]) -> list[PropertyDataSearchItem]:
            return [PropertyDataSearchItem.model_validate(x) for x in items]

        category_values = ensure_list(category)

        params = {
            "result": result,
            "text": text,
            "order": order,
            "sortBy": sort_by,
            "inventoryIds": ensure_list(inventory_ids),
            "projectIds": ensure_list(project_ids),
            "lotIds": ensure_list(lot_ids),
            "dataTemplateId": ensure_list(data_template_ids),
            "dataColumnId": ensure_list(data_column_ids),
            "category": category_values if category_values else None,
            "dataTemplates": ensure_list(data_templates),
            "dataColumns": ensure_list(data_columns),
            "parameters": ensure_list(parameters),
            "parameterGroup": ensure_list(parameter_group),
            "unit": ensure_list(unit),
            "createdBy": ensure_list(created_by),
            "taskCreatedBy": ensure_list(task_created_by),
            "returnFields": ensure_list(return_fields),
            "returnFacets": ensure_list(return_facets),
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=deserialize,
        )
