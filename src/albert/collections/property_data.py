from collections.abc import Iterator
from contextlib import suppress
from enum import Enum

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
    """PropertyDataCollection is a collection class for managing Property Data entities in the Albert platform."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CompanyCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{PropertyDataCollection._api_version}/propertydata"

    @validate_call
    def get_properties_on_inventory(self, *, inventory_id: InventoryId) -> InventoryPropertyData:
        """Returns all the properties of an inventory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory item to retrieve properties for.

        Returns
        -------
        InventoryPropertyData
            The properties of the inventory item.
        """
        params = {"entity": "inventory", "id": [inventory_id]}
        response = self.session.get(url=self.base_path, params=params)
        response_json = response.json()
        return InventoryPropertyData(**response_json[0])

    @validate_call
    def add_properties_to_inventory(
        self, *, inventory_id: InventoryId, properties: list[InventoryDataColumn]
    ) -> list[InventoryPropertyDataCreate]:
        """Add new properties to an inventory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory item to add properties to.
        properties : list[InventoryDataColumn]
            The properties to add.

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

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory item to update the property on.
        property_data : InventoryDataColumn
            The updated property data.

        Returns
        -------
        InventoryPropertyData
            The updated property data as returned by the server.
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
        """Returns all the properties within a Property Task block for a specific inventory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory.
        task_id : TaskId
            The Property task ID.
        block_id : BlockId
            The Block ID of the block to retrieve properties for.
        lot_id : LotId | None, optional
            The specific Lot of the inventory Item to retrieve lots for, by default None

        Returns
        -------
        TaskPropertyData
            The properties of the inventory item within the block.
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
        """Checks if a task has data.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task to check for data.

        Returns
        -------
        list[CheckPropertyData]
            A list of CheckPropertyData entities representing the data status of each block + inventory item of the task.
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
        """Check if a specific block interval has data.

        Parameters
        ----------
        block_id : BlockId
            The ID of the block.
        task_id : TaskId
            The ID of the task.
        interval_id : IntervalId
            The ID of the interval.

        Returns
        -------
        CheckPropertyData
            CheckPropertyData representing the data status of each block + inventory item of the task.
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
        """Collect task property data for block/inventory combinations in a task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task to retrieve properties for.
        with_data_only : bool, optional
            When True, only return combinations actually having task data (``dataExist`` flag is true). Defaults to False.

        Returns
        -------
        list[TaskPropertyData]
            Task property data for each block/inventory/lot combination. When
            ``with_data_only`` is True, combinations without recorded data are omitted.
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
        """Updates a specific property on a task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        patch_payload : list[PropertyDataPatchDatum]
            The specific patch to make to update the property. ImagePropertyValue and
            CurvePropertyValue updates require update_or_create_task_properties.
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
            A list of TaskPropertyData entities representing the properties within the task.
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
        """Void all property data for a task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        inventory_id : InventoryId
            The ID of the inventory item.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId | None, optional
            The ID of the lot, by default None.

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
        """Unvoid all property data for a task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        inventory_id : InventoryId
            The ID of the inventory item.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId | None, optional
            The ID of the lot, by default None.

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
        """Void all property data for a specific interval combination.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        interval_id : str
            The interval combination identifier (``CheckPropertyData.interval_id``).
            Use ``check_for_task_data`` to list interval combinations for a task.
        inventory_id : InventoryId
            The ID of the inventory item.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId | None, optional
            The ID of the lot, by default None.
        data_template_id : DataTemplateId | None, optional
            When provided, limits the voiding to a specific data template.

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
        """Unvoid all property data for a specific interval combination.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        interval_id : str
            The interval combination identifier (``CheckPropertyData.interval_id``).
            Use ``check_for_task_data`` to list interval combinations for a task.
        inventory_id : InventoryId
            The ID of the inventory item.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId | None, optional
            The ID of the lot, by default None.
        data_template_id : DataTemplateId | None, optional
            When provided, limits the unvoiding to a specific data template.

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
        """Void property data for a specific trial in an interval combination.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        interval_id : str
            The interval combination identifier (``CheckPropertyData.interval_id``).
            Use ``check_for_task_data`` to list interval combinations for a task.
        trial_number : int
            The trial number to void.
        inventory_id : InventoryId
            The ID of the inventory item.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId | None, optional
            The ID of the lot, by default None.

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
        """Unvoid property data for a specific trial in an interval combination.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        interval_id : str
            The interval combination identifier (``CheckPropertyData.interval_id``).
            Use ``check_for_task_data`` to list interval combinations for a task.
        trial_number : int
            The trial number to unvoid.
        inventory_id : InventoryId
            The ID of the inventory item.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId | None, optional
            The ID of the lot, by default None.

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
        """
        Add new task properties for a given task.

        This method only works for new values. If a trial number is provided in the TaskPropertyCreate,
        it must relate to an existing trial. New trials must be added with no trial number provided.
        Do not try to create multiple new trials in one call as this will lead to unexpected behavior.
        Build out new trials in a loop if many new trials are needed.

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
        properties : list[TaskPropertyCreate]
            A list of TaskPropertyCreate entities representing the properties to add.
        return_scope : Literal["task", "block", "none"], optional
            Controls the response. "task" (default) returns all task properties,
            "block" returns only the affected block/inventory/lot combination, and "none" skips fetching data.

        Returns
        -------
        list[TaskPropertyData]
            The newly created task properties.
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
        """
        Update or create task properties for a given task.

        If a trial number is provided in the TaskPropertyCreate, it must relate to an existing trial.
        New trials must be added with no trial number provided. Do not try to create multiple new trials
        in one call as this will lead to unexpected behavior. Build out new trials in a loop if many new
        trials are needed.

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
        properties : list[TaskPropertyCreate]
            A list of TaskPropertyCreate entities representing the properties to update or create.
        return_scope : Literal["task", "block", "none"], optional
            Controls the response. "task" (default) returns all task properties,
            "block" returns only the affected block/inventory/lot combination, and "none" skips fetching data.

        Returns
        -------
        list[TaskPropertyData]
            The updated or newly created task properties.

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
        """
        Bulk load task properties for a given task. WARNING: This will overwrite any existing properties!
        BulkPropertyData column names must exactly match the names of the data columns (Case Sensitive).

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
            The interval to use for the properties, by default "default". Can be obtained using Workflow.get_interval_id().
        property_data : BulkPropertyData
            A list of columnwise data containing all your rows of data for a single interval. Can be created using BulkPropertyData.from_dataframe().
        return_scope : Literal["task", "block", "none"], optional
            Controls the response. "task" (default) returns all task properties,
            "block" returns only the affected block/inventory/lot combination, and "none" skips fetching data.

        Returns
        -------
        list[TaskPropertyData]
            The updated or newly created task properties.

        Example
        -------

        ```python
        from albert.resources.property_data import BulkPropertyData

        data = BulkPropertyData.from_dataframe(df=my_dataframe)
        res = client.property_data.bulk_load_task_properties(
            block_id="BLK1",
            inventory_id="INVEXP102748-042",
            property_data=data,
            task_id="TASFOR291760",
        )

        [TaskPropertyData(id="TASFOR291760", ...)]
        ```
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
        """
        Bulk delete task data for a given task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        block_id : BlockId
            The ID of the block.
        inventory_id : InventoryId
            The ID of the inventory.
        lot_id : LotId, optional
            The ID of the lot, by default None.
        interval_id : IntervalId, optional
            The ID of the interval, by default None. If provided, will delete data for this specific interval.

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
        """
        Search for property data with various filtering options.

        Parameters
        ----------
        result : str, optional
            Query using syntax, e.g. result=viscosity(<200)@temperature(25).
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
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[PropertyDataSearchItem]
            An iterator of search results matching the specified filters.
        """

        def deserialize(items: list[dict]) -> list[PropertyDataSearchItem]:
            return [PropertyDataSearchItem.model_validate(x) for x in items]

        category_values = ensure_list(category)

        params = {
            "result": result,
            "text": text,
            "order": order.value if order else None,
            "sortBy": sort_by,
            "inventoryIds": ensure_list(inventory_ids),
            "projectIds": ensure_list(project_ids),
            "lotIds": ensure_list(lot_ids),
            "dataTemplateId": ensure_list(data_template_ids),
            "dataColumnId": ensure_list(data_column_ids),
            "category": (
                [c.value if isinstance(c, Enum) else c for c in category_values]
                if category_values
                else None
            ),
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
