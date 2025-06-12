from __future__ import annotations

from collections.abc import Iterator

from pydantic import validate_call
from requests.exceptions import RetryError

from albert.collections.base import BaseCollection, OrderBy
from albert.exceptions import AlbertHTTPError
from albert.resources.identifiers import (
    BlockId,
    DataTemplateId,
    TaskId,
    WorkflowId,
)
from albert.resources.tasks import (
    BaseTask,
    HistoryEntity,
    PropertyTask,
    TaskAdapter,
    TaskCategory,
    TaskHistory,
    TaskPatchPayload,
)
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode
from albert.utils.patch_types import PatchDatum, PatchOperation, PatchPayload


class TaskCollection(BaseCollection):
    """TaskCollection is a collection class for managing Task entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {
        "metadata",
        "name",
        "priority",
        "state",
        "tags",
        "assigned_to",
        "due_date",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize the TaskCollection.

        Parameters
        ----------
        session : AlbertSession
            The Albert Session information
        """
        super().__init__(session=session)
        self.base_path = f"/api/{TaskCollection._api_version}/tasks"

    def create(self, *, task: BaseTask) -> BaseTask:
        """Create a new task. Tasks can be of different types, such as PropertyTask, and are created using the provided task object.

        Parameters
        ----------
        task : BaseTask
            The task object to create.

        Returns
        -------
        BaseTask
            The registered task object.
        """
        payload = [task.model_dump(mode="json", by_alias=True, exclude_none=True)]
        url = f"{self.base_path}/multi?category={task.category.value}"
        if task.parent_id is not None:
            url = f"{url}&parentId={task.parent_id}"
        response = self.session.post(url=url, json=payload)
        task_data = response.json()[0]
        return TaskAdapter.validate_python(task_data)

    @validate_call
    def add_block(
        self, *, task_id: TaskId, data_template_id: DataTemplateId, workflow_id: WorkflowId
    ) -> None:
        """Add a block to a Property task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task to add the block to.
        data_template_id : DataTemplateId
            The ID of the data template to use for the block.
        workflow_id : WorkflowId
            The ID of the workflow to assign to the block.

        Returns
        -------
        None
            This method does not return any value.

        """
        url = f"{self.base_path}/{task_id}"
        payload = [
            {
                "id": task_id,
                "data": [
                    {
                        "operation": "add",
                        "attribute": "Block",
                        "newValue": [{"datId": data_template_id, "Workflow": {"id": workflow_id}}],
                    }
                ],
            }
        ]
        self.session.patch(url=url, json=payload)
        return None

    @validate_call
    def update_block_workflow(
        self, *, task_id: TaskId, block_id: BlockId, workflow_id: WorkflowId
    ) -> None:
        """
        Update the workflow of a specific block within a task.

        This method updates the workflow of a specified block within a task.
        Parameters
        ----------
        task_id : str
            The ID of the task.
        block_id : str
            The ID of the block within the task.
        workflow_id : str
            The ID of the new workflow to be assigned to the block.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        - The method asserts that the retrieved task is an instance of `PropertyTask`.
        - If the block's current workflow matches the new workflow ID, no update is performed.
        - The method handles the case where the block has a default workflow named "No Parameter Group".
        """
        url = f"{self.base_path}/{task_id}"
        task = self.get_by_id(id=task_id)
        if not isinstance(task, PropertyTask):
            logger.error(f"Task {task_id} is not an instance of PropertyTask")
            raise TypeError(f"Task {task_id} is not an instance of PropertyTask")
        for b in task.blocks:
            if b.id != block_id:
                continue
            for w in b.workflow:
                if w.name == "No Parameter Group" and len(b.workflow) > 1:
                    # hardcoded default workflow
                    continue
                existing_workflow_id = w.id
        if existing_workflow_id == workflow_id:
            logger.info(f"Block {block_id} already has workflow {workflow_id}")
            return None
        patch = [
            {
                "data": [
                    {
                        "operation": "update",
                        "attribute": "workflow",
                        "oldValue": existing_workflow_id,
                        "newValue": workflow_id,
                        "blockId": block_id,
                    }
                ],
                "id": task_id,
            }
        ]
        self.session.patch(url=url, json=patch)
        return None

    @validate_call
    def remove_block(self, *, task_id: TaskId, block_id: BlockId) -> None:
        """Remove a block from a Property task.

        Parameters
        ----------
        task_id : str
            ID of the Task to remove the block from (e.g., TASFOR1234)
        block_id : str
            ID of the Block to remove (e.g., BLK1)

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{task_id}"
        payload = [
            {
                "id": task_id,
                "data": [
                    {
                        "operation": "delete",
                        "attribute": "Block",
                        "oldValue": [block_id],
                    }
                ],
            }
        ]
        self.session.patch(url=url, json=payload)
        return None

    @validate_call
    def delete(self, *, id: TaskId) -> None:
        """Delete a task.

        Parameters
        ----------
        id : TaskId
            The ID of the task to delete.
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def get_by_id(self, *, id: TaskId) -> BaseTask:
        """Retrieve a task by its ID.

        Parameters
        ----------
        id : TaskId
            The ID of the task to retrieve.

        Returns
        -------
        BaseTask
            The task object with the provided ID.
        """
        url = f"{self.base_path}/multi/{id}"
        response = self.session.get(url)
        return TaskAdapter.validate_python(response.json())

    def list(
        self,
        *,
        order: OrderBy = OrderBy.DESCENDING,
        text: str | None = None,
        sort_by: str | None = None,
        tags: list[str] | None = None,
        task_id: list[str] | None = None,
        linked_task: list[str] | None = None,
        category: TaskCategory | None = None,
        albert_id: list[str] | None = None,
        data_template: list[str] | None = None,
        assigned_to: list[str] | None = None,
        location: list[str] | None = None,
        priority: list[str] | None = None,
        status: list[str] | None = None,
        parameter_group: list[str] | None = None,
        created_by: list[str] | None = None,
        project_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Iterator[BaseTask]:
        """Search for tasks matching the given criteria.

        Parameters
        ----------
        order : OrderBy, optional
            The order in which to return results, by default OrderBy.DESCENDING
        text : str | None, optional
            The text to search for, by default None
        sort_by : str | None, optional
            The attribute to sort by, by default None
        tags : list[str] | None, optional
            The tags to search for, by default None
        task_id : list[str] | None, optional
            The related task IDs to search for, by default None
        linked_task : list[str] | None, optional
            The Linked Task IDs to search for, by default None
        category : TaskCategory | None, optional
            The category of the task to search for, by default None
        albert_id : list[str] | None, optional
            The Albert IDs to search for, by default None
        data_template : list[str] | None, optional
            The data template IDs to search for, by default None
        assigned_to : list[str] | None, optional
            The User IDs to search for, by default None
        location : list[str] | None, optional
            The Locations names to search for, by default None
        priority : list[str] | None, optional
            The Priority levels to search for, by default None
        status : list[str] | None, optional
            The Task Statuses to search for, by default None
        parameter_group : list[str] | None, optional
            The related Parameter Group IDs to search for, by default None
        created_by : list[str] | None, optional
            The User IDs of the task creators to search for, by default None
        project_id : str | None, optional
            The Project ID to search for, by default None

        Yields
        ------
        Iterator[BaseTask]
            An iterator of matching Task objects.
        """

        def deserialize(items: list[dict]) -> Iterator[BaseTask]:
            for item in items:
                id = item["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except (
                    AlbertHTTPError,
                    RetryError,
                ) as e:  # some legacy poorly formed Tasks raise 500s. The allowance on Retry error to also ignore these.
                    logger.warning(f"Error fetching task '{id}': {e}")

        params = {
            "limit": limit,
            "offset": offset,
            "order": OrderBy(order).value if order else None,
            "text": text,
            "sortBy": sort_by,
            "tags": tags,
            "taskId": task_id,
            "linkedTask": linked_task,
            "category": category,
            "albertId": albert_id,
            "dataTemplate": data_template,
            "assignedTo": assigned_to,
            "location": location,
            "priority": priority,
            "status": status,
            "parameterGroup": parameter_group,
            "createdBy": created_by,
            "projectId": project_id,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            deserialize=deserialize,
            params=params,
        )

    def _is_metadata_item_list(
        self,
        *,
        existing_object: BaseTask,
        updated_object: BaseTask,
        metadata_field: str,
    ) -> bool:
        """Return True if the metadata field is list-typed on either object."""

        if not metadata_field.startswith("Metadata."):
            return False

        metadata_field = metadata_field.split(".")[1]

        if existing_object.metadata is None:
            existing_object.metadata = {}
        if updated_object.metadata is None:
            updated_object.metadata = {}

        existing = existing_object.metadata.get(metadata_field, None)
        updated = updated_object.metadata.get(metadata_field, None)

        return isinstance(existing, list) or isinstance(updated, list)

    def _generate_patch_payload(
        self,
        *,
        existing: BaseTask,
        updated: BaseTask,
    ) -> tuple[PatchPayload, dict[str, list[str]]]:
        """Generate patch payload and capture metadata list updates."""

        base_payload = super()._generate_patch_payload(
            existing=existing,
            updated=updated,
        )

        new_data: list[PatchDatum] = []
        list_metadata_updates: dict[str, list[str]] = {}

        for datum in base_payload.data:
            if self._is_metadata_item_list(
                existing_object=existing,
                updated_object=updated,
                metadata_field=datum.attribute,
            ):
                key = datum.attribute.split(".", 1)[1]
                updated_list = updated.metadata.get(key) or []
                list_values: list[str] = [
                    item.id if hasattr(item, "id") else item for item in updated_list
                ]

                list_metadata_updates[datum.attribute] = list_values
                continue

            new_data.append(
                PatchDatum(
                    operation=datum.operation,
                    attribute=datum.attribute,
                    new_value=datum.new_value,
                    old_value=datum.old_value,
                )
            )

        return TaskPatchPayload(data=new_data, id=existing.id), list_metadata_updates

    def _generate_adv_patch_payload(
        self, *, updated: BaseTask, existing: BaseTask
    ) -> tuple[dict, dict[str, list[str]]]:
        """Generate a patch payload for updating a task.

        Parameters
        ----------
        existing : BaseTask
            The existing Task object.
        updated : BaseTask
            The updated Task object.

        Returns
        -------
        tuple[dict, dict[str, list[str]]]
            The patch payload for updating the task and metadata list updates.
        """
        _updatable_attributes_special = {"inventory_information"}
        base_payload, list_metadata_updates = self._generate_patch_payload(
            existing=existing,
            updated=updated,
        )
        patch_payload = base_payload.model_dump(mode="json", by_alias=True)

        for attribute in _updatable_attributes_special:
            old_value = getattr(existing, attribute)
            new_value = getattr(updated, attribute)
            if attribute == "inventory_information":
                existing_unique = [f"{x.inventory_id}#{x.lot_id}" for x in old_value]
                updated_unique = [f"{x.inventory_id}#{x.lot_id}" for x in new_value]
                inv_to_remove = []
                for i, inv in enumerate(existing_unique):
                    if inv not in updated_unique:
                        inv_to_remove.append(
                            old_value[i].model_dump(mode="json", by_alias=True, exclude_none=True)
                        )
                if len(inv_to_remove) > 0:
                    patch_payload["data"].append(
                        {
                            "operation": PatchOperation.DELETE,
                            "attribute": "inventory",
                            "oldValue": inv_to_remove,
                        }
                    )
                inv_to_add = []
                for i, inv in enumerate(updated_unique):
                    if inv not in existing_unique:
                        inv_to_add.append(
                            new_value[i].model_dump(mode="json", by_alias=True, exclude_none=True)
                        )
                if len(inv_to_add) > 0:
                    patch_payload["data"].append(
                        {
                            "operation": PatchOperation.ADD,
                            "attribute": "inventory",
                            "newValue": inv_to_add,
                        }
                    )

        return patch_payload, list_metadata_updates

    def update(self, *, task: BaseTask) -> BaseTask:
        """Update a task.

        Parameters
        ----------
        task : BaseTask
            The updated Task object.

        Returns
        -------
        BaseTask
            The updated Task object as it exists in the Albert platform.
        """
        existing = self.get_by_id(id=task.id)
        patch_payload, list_metadata_updates = self._generate_adv_patch_payload(
            updated=task, existing=existing
        )
        patch_operations = patch_payload.get("data", [])

        if len(patch_operations) == 0 and len(list_metadata_updates) == 0:
            logger.info(f"Task {task.id} is already up to date")
            return task
        path = f"{self.base_path}/{task.id}"

        for datum in patch_operations:
            patch_payload = TaskPatchPayload(data=[datum], id=task.id)
            self.session.patch(
                url=path,
                json=[patch_payload.model_dump(mode="json", by_alias=True, exclude_none=True)],
            )

        # For metadata list field updates, we clear, then update
        # since duplicate attribute values are not allowed in single patch request.
        for attribute, values in list_metadata_updates.items():
            entity_links = existing.metadata.get(attribute.split(".")[1])
            old_values = [item.id if hasattr(item, "id") else item for item in entity_links]
            clear_datum = PatchDatum(
                operation=PatchOperation.DELETE, attribute=attribute, oldValue=old_values
            )
            clear_payload = TaskPatchPayload(data=[clear_datum], id=task.id)
            self.session.patch(
                url=path,
                json=[clear_payload.model_dump(mode="json", by_alias=True, exclude_none=True)],
            )
            if values:
                update_datum = PatchDatum(
                    operation=PatchOperation.UPDATE,
                    attribute=attribute,
                    newValue=values,
                    oldValue=[],
                )

                update_payload = TaskPatchPayload(data=[update_datum], id=task.id)
                self.session.patch(
                    url=path,
                    json=[
                        update_payload.model_dump(mode="json", by_alias=True, exclude_none=False)
                    ],
                )
        return self.get_by_id(id=task.id)

    def get_history(
        self,
        *,
        id: TaskId,
        order: OrderBy = OrderBy.DESCENDING,
        limit: int = 1000,
        entity: HistoryEntity | None = None,
        blockId: str | None = None,
        startKey: str | None = None,
    ) -> TaskHistory:
        params = {
            "limit": limit,
            "orderBy": OrderBy(order).value if order else None,
            "entity": entity,
            "blockId": blockId,
            "startKey": startKey,
        }
        url = f"{self.base_path}/{id}/history"
        response = self.session.get(url, params=params)
        return TaskHistory(**response.json())
