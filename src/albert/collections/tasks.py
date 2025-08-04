from __future__ import annotations

from collections.abc import Iterator

from pydantic import validate_call
from requests.exceptions import RetryError

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import (
    BlockId,
    DataTemplateId,
    TaskId,
    WorkflowId,
)
from albert.core.shared.models.base import EntityLink, EntityLinkWithName
from albert.core.shared.models.patch import PatchOperation
from albert.exceptions import AlbertHTTPError
from albert.resources.tasks import (
    BaseTask,
    BatchTask,
    GeneralTask,
    HistoryEntity,
    PropertyTask,
    TaskAdapter,
    TaskCategory,
    TaskHistory,
    TaskPatchPayload,
    TaskSearchItem,
)


class TaskCollection(BaseCollection):
    """TaskCollection is a collection class for managing Task entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {
        "metadata",
        "name",
        "priority",
        "state",
        "tags",
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

    def create(self, *, task: PropertyTask | GeneralTask | BatchTask) -> BaseTask:
        """Create a new task. Tasks can be of different types, such as PropertyTask, and are created using the provided task object.

        Parameters
        ----------
        task : PropertyTask | GeneralTask | BatchTask
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

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
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
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        max_items: int | None = None,
        offset: int = 0,
    ) -> Iterator[TaskSearchItem]:
        """
        Search for Task matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str, optional
            Text search across multiple task fields.
        tags : list[str], optional
            Filter by tags associated with tasks.
        task_id : list[str], optional
            Specific task IDs to search for.
        linked_task : list[str], optional
            Task IDs linked to the ones being searched.
        category : TaskCategory, optional
            Task category filter (e.g., Experiment, Analysis).
        albert_id : list[str], optional
            Albert-specific task identifiers.
        data_template : list[str], optional
            Data template IDs associated with tasks.
        assigned_to : list[str], optional
            User IDs assigned to the tasks.
        location : list[str], optional
            Locations where tasks are carried out.
        priority : list[str], optional
            Priority levels for filtering tasks.
        status : list[str], optional
            Task status values (e.g., Open, Done).
        parameter_group : list[str], optional
            Parameter Group IDs associated with tasks.
        created_by : list[str], optional
            User IDs who created the tasks.
        project_id : str, optional
            ID of the parent project for filtering tasks.
        order_by : OrderBy, optional
            The order in which to return results (asc or desc), default DESCENDING.
        sort_by : str, optional
            Attribute to sort tasks by (e.g., createdAt, name).
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            Number of results to skip for pagination, default 0.

        Returns
        -------
        Iterator[TaskSearchItem]
            An iterator of matching, lightweight TaskSearchItem entities.
        """
        params = {
            "offset": offset,
            "order": order_by.value,
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
            params=params,
            max_items=max_items,
            deserialize=lambda items: [
                TaskSearchItem(**item)._bind_collection(self) for item in items
            ],
        )

    def get_all(
        self,
        *,
        text: str | None = None,
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
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        max_items: int | None = None,
        offset: int = 0,
    ) -> Iterator[BaseTask]:
        """
        Retrieve fully hydrated Task entities with optional filters.

        This method returns complete entity data using `get_by_id`.
        Use :meth:`search` for faster retrieval when you only need lightweight, partial (unhydrated) entities.

        Parameters
        ----------
        text : str, optional
            Text search across multiple task fields.
        tags : list[str], optional
            Filter by tags associated with tasks.
        task_id : list[str], optional
            Specific task IDs to search for.
        linked_task : list[str], optional
            Task IDs linked to the ones being searched.
        category : TaskCategory, optional
            Task category filter (e.g., Experiment, Analysis).
        albert_id : list[str], optional
            Albert-specific task identifiers.
        data_template : list[str], optional
            Data template IDs associated with tasks.
        assigned_to : list[str], optional
            User IDs assigned to the tasks.
        location : list[str], optional
            Locations where tasks are carried out.
        priority : list[str], optional
            Priority levels for filtering tasks.
        status : list[str], optional
            Task status values (e.g., Open, Done).
        parameter_group : list[str], optional
            Parameter Group IDs associated with tasks.
        created_by : list[str], optional
            User IDs who created the tasks.
        project_id : str, optional
            ID of the parent project for filtering tasks.
        order_by : OrderBy, optional
            The order in which to return results (asc or desc), default DESCENDING.
        sort_by : str, optional
            Attribute to sort tasks by (e.g., createdAt, name).
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            Number of results to skip for pagination, default 0.

        Yields
        ------
        Iterator[BaseTask]
            A stream of fully hydrated Task entities (PropertyTask, BatchTask, or GeneralTask).
        """
        for task in self.search(
            text=text,
            tags=tags,
            task_id=task_id,
            linked_task=linked_task,
            category=category,
            albert_id=albert_id,
            data_template=data_template,
            assigned_to=assigned_to,
            location=location,
            priority=priority,
            status=status,
            parameter_group=parameter_group,
            created_by=created_by,
            project_id=project_id,
            order_by=order_by,
            sort_by=sort_by,
            max_items=max_items,
            offset=offset,
        ):
            task_id = getattr(task, "id", None)
            if not task_id:
                continue

            try:
                yield self.get_by_id(id=task_id)
            except (AlbertHTTPError, RetryError) as e:
                logger.warning(f"Error fetching task '{task_id}': {e}")

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

    def _generate_task_patch_payload(
        self,
        *,
        existing: BaseTask,
        updated: BaseTask,
    ) -> TaskPatchPayload:
        """Generate patch payload and capture metadata list updates."""

        base_payload = super()._generate_patch_payload(
            existing=existing,
            updated=updated,
            generate_metadata_diff=True,
        )
        return TaskPatchPayload(data=base_payload.data, id=existing.id)

    def _generate_adv_patch_payload(
        self, *, updated: BaseTask, existing: BaseTask
    ) -> TaskPatchPayload:
        """Generate a patch payload for updating a task.

         Parameters
         ----------
         existing : BaseTask
             The existing Task object.
         updated : BaseTask
             The updated Task object.

         Returns
         -------
        TaskPatchPayload
             The patch payload for updating the task
        """
        _updatable_attributes_special = {
            "inventory_information",
            "assigned_to",
        }
        if updated.assigned_to is not None:
            updated.assigned_to = EntityLinkWithName(
                id=updated.assigned_to.id, name=updated.assigned_to.name
            )
        base_payload = self._generate_task_patch_payload(
            existing=existing,
            updated=updated,
        )

        for attribute in _updatable_attributes_special:
            old_value = getattr(existing, attribute)
            new_value = getattr(updated, attribute)

            if attribute == "assigned_to":
                if new_value == old_value or (
                    new_value and old_value and new_value.id == old_value.id
                ):
                    continue
                if old_value is None:
                    base_payload.data.append(
                        {
                            "operation": PatchOperation.ADD,
                            "attribute": "AssignedTo",
                            "newValue": new_value,
                        }
                    )
                    continue

                if new_value is None:
                    base_payload.data.append(
                        {
                            "operation": PatchOperation.DELETE,
                            "attribute": "AssignedTo",
                            "oldValue": old_value,
                        }
                    )
                    continue
                base_payload.data.append(
                    {
                        "operation": PatchOperation.UPDATE,
                        "attribute": "AssignedTo",
                        "oldValue": EntityLink(
                            id=old_value.id
                        ),  # can't include name with the old value or you get an error
                        "newValue": new_value,
                    }
                )

            if attribute == "inventory_information":
                existing_unique = {f"{x.inventory_id}#{x.lot_id}": x for x in old_value}
                updated_unique = {f"{x.inventory_id}#{x.lot_id}": x for x in new_value}

                # Find items to remove (in existing but not in updated)
                inv_to_remove = [
                    item.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for key, item in existing_unique.items()
                    if key not in updated_unique
                ]

                # Find items to add (in updated but not in existing)
                inv_to_add = [
                    item.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for key, item in updated_unique.items()
                    if key not in existing_unique
                ]

                if inv_to_remove:
                    base_payload.data.append(
                        {
                            "operation": PatchOperation.DELETE,
                            "attribute": "inventory",
                            "oldValue": inv_to_remove,
                        }
                    )

                if inv_to_add:
                    base_payload.data.append(
                        {
                            "operation": PatchOperation.ADD,
                            "attribute": "inventory",
                            "newValue": inv_to_add,
                        }
                    )

        return base_payload

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
        patch_payload = self._generate_adv_patch_payload(updated=task, existing=existing)

        if len(patch_payload.data) == 0:
            logger.info(f"Task {task.id} is already up to date")
            return task
        path = f"{self.base_path}/{task.id}"

        for datum in patch_payload.data:
            patch_payload = TaskPatchPayload(data=[datum], id=task.id)
            self.session.patch(
                url=path,
                json=[patch_payload.model_dump(mode="json", by_alias=True, exclude_none=True)],
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
