from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from pydantic import validate_call
from requests.exceptions import RetryError

from albert.collections.attachments import AttachmentCollection
from albert.collections.base import BaseCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.property_data import PropertyDataCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import (
    AttachmentId,
    BlockId,
    DataTemplateId,
    InventoryId,
    LotId,
    ProjectId,
    TaskId,
    WorkflowId,
    remove_id_prefix,
)
from albert.exceptions import AlbertHTTPError
from albert.resources.attachments import AttachmentCategory
from albert.resources.tasks import (
    BaseTask,
    BatchTask,
    CsvTableInput,
    CsvTableResponseItem,
    GeneralTask,
    HistoryEntity,
    ImportMode,
    PropertyTask,
    TaskAdapter,
    TaskCategory,
    TaskHistory,
    TaskPatchPayload,
    TaskSearchItem,
)
from albert.utils.tasks import (
    CSV_EXTENSIONS,
    build_property_payload,
    build_task_metadata,
    determine_extension,
    extract_extensions_from_attachment,
    fetch_csv_table_rows,
    generate_adv_patch_payload,
    map_csv_headers_to_columns,
    resolve_attachment,
)


class TaskCollection(BaseCollection):
    """TaskCollection is a collection class for managing Task entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {
        "metadata",
        "name",
        "priority",
        "state",
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
    def import_results(
        self,
        *,
        task_id: TaskId,
        inventory_id: InventoryId,
        data_template_id: DataTemplateId,
        block_id: BlockId | None = None,
        attachment_id: AttachmentId | None = None,
        file_path: str | Path | None = None,
        note_text: str | None = None,
        lot_id: LotId | None = None,
        interval: str = "default",
        field_mapping: dict[str, str] | None = None,
        mode: ImportMode = ImportMode.CSV,
    ) -> BaseTask:
        """
        Import results from an attachment into property data. Reuse an existing attachment or upload a
        new one, optionally provide header-to-column mappings, and target the desired block, lot,
        and interval. Returns the task after the import.

        Parameters
        ----------
        task_id : TaskId
            The property task receiving the results.
        block_id : BlockId | None
            Target block on the task where the data will be written. Optional, when a
            single block present on the task. If multiple blocks exist, this parameter must be provided.
        inventory_id : InventoryId
            Inventory item id.
        data_template_id : DataTemplateId
            Data template Id.
        attachment_id : AttachmentId | None, optional
            Existing attachment to use. Exactly one of ``attachment_id`` or
            ``file_path`` must be provided.
        file_path : str | Path | None, optional
            Local file to upload and attach to a new note on the task. Exactly one of
            ``attachment_id`` or ``file_path`` must be provided.
        note_text : str | None, optional
            Optional text for the note created when uploading a new file.
        lot_id : LotId | None, optional
            Lot context when deleting/writing property data.
        interval : str, optional
            Interval combination to target. Defaults to "default".
        field_mapping : dict[str, str] | None, optional
            Optional mapping from CSV header labels to data column names. Keys should match the
            header text from the CSV (case-insensitive comparison is applied), and values should
            match the corresponding data template column names. For example,
            ``{"APHA": "APHA Color", "Comm": "Comments"}``.
        mode : ImportMode, optional
            Import mode to use, by default ImportMode.CSV. Use ImportMode.SCRIPT to run a custom
            script to process the CSV before import. This requires a script attachment on the data template.

        Returns
        -------
        BaseTask
            The task with the newly imported results.

        Examples
        --------
        !!! example "Import results from a CSV file"
            ```python
            task = client.tasks.import_results(
                task_id="TAS123",
                inventory_id="MO123",
                data_template_id="DT123",
                file_path="path/to/results.csv",
                field_mapping={"comm": "Comments"},
                mode=ImportMode.CSV,
            )
            ```
        """
        logger.info("Importing results for task %s using %s mode", task_id, mode)

        if (attachment_id is None) == (file_path is None):
            raise ValueError("Provide exactly one of 'attachment_id' or 'file_path'.")

        attachment_collection = AttachmentCollection(session=self.session)
        data_template_collection = DataTemplateCollection(session=self.session)
        property_data_collection = PropertyDataCollection(session=self.session)
        data_template = data_template_collection.get_by_id(id=data_template_id)

        needs_task_details = block_id is None or mode is ImportMode.SCRIPT
        task_details = self.get_by_id(id=task_id) if needs_task_details else None

        if block_id is None:
            block_ids = [
                blk.id
                for blk in (task_details.blocks if task_details else [])
                if getattr(blk, "id", None)
            ]
            if not block_ids:
                raise ValueError("No blocks found on the task.")
            if len(block_ids) > 1:
                raise ValueError(
                    "Multiple blocks detected on the task; specify 'block_id' to import results."
                )
            block_id = block_ids[0]

        script_signed_url: str | None = None
        if mode is ImportMode.SCRIPT:
            script_attachments = attachment_collection.get_by_parent_ids(
                parent_ids=[data_template_id]
            )
            script_entries = (
                script_attachments.get(data_template_id, []) if script_attachments else []
            )
            script_attachment = next(
                (att for att in script_entries if att.category == AttachmentCategory.SCRIPT),
                None,
            )
            if script_attachment is None:
                raise ValueError("Script attachment was not found on the data template.")
            script_signed_url = script_attachment.signed_url
            script_extensions = extract_extensions_from_attachment(attachment=script_attachment)
            if not script_extensions:
                raise ValueError("Script attachment must define allowed extensions.")
            allowed_extensions = set(script_extensions)
        else:
            allowed_extensions = set(CSV_EXTENSIONS)

        attachment_id = AttachmentId(
            resolve_attachment(
                attachment_collection=attachment_collection,
                task_id=task_id,
                file_path=file_path,
                attachment_id=attachment_id if attachment_id else None,
                allowed_extensions=allowed_extensions,
                note_text=note_text,
            )
        )

        attachment_details = attachment_collection.get_by_id(id=attachment_id)
        attachment_extension = determine_extension(filename=attachment_details.name)
        if allowed_extensions and attachment_extension not in allowed_extensions:
            raise ValueError(
                f"Attachment '{attachment_details.name}' does not match required extensions {sorted(allowed_extensions)}."
            )

        if mode is ImportMode.SCRIPT:
            if not attachment_details.signed_url:
                raise ValueError(
                    "Attachment does not include a signed URL required for script execution."
                )
            metadata = build_task_metadata(
                task=task_details,
                block_id=block_id,
                filename=attachment_details.name,
            )
            csv_payload = CsvTableInput(
                script_s3_url=script_signed_url,
                data_s3_url=attachment_details.signed_url,
                task_metadata=metadata,
            )
            response = self.session.post(
                f"/api/{self._api_version}/proxy/csvtable",
                json=csv_payload.model_dump(by_alias=True, mode="json"),
            )
            response_body = response.json()
            table_results = [CsvTableResponseItem.model_validate(item) for item in response_body]
            table_rows = table_results[0].data if table_results else None
            if not isinstance(table_rows, list) or len(table_rows) < 2:
                raise ValueError(
                    "Script CSV preview must contain a header row followed by at least one data row."
                )
        else:
            table_rows = fetch_csv_table_rows(
                session=self.session,
                attachment_id=str(attachment_id),
            )

        header_row = table_rows[0]
        data_rows = [row for row in table_rows[1:] if isinstance(row, dict)]
        if not data_rows:
            raise ValueError("No data rows detected in CSV preview.")

        header_sequence: list[tuple[str, str]] = []
        if isinstance(header_row, dict):
            # API is expected to return lowercase `col#` keys (e.g. `col1`).
            for key, value in header_row.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                normalized_key = key.strip().lower()
                header_name = value
                if not header_name:
                    continue
                header_sequence.append((normalized_key, header_name))
        logger.debug("CSV header sequence: %s", header_sequence)
        data_columns = data_template.data_column_values or []
        column_to_csv_key = map_csv_headers_to_columns(
            header_sequence=header_sequence,
            data_columns=data_columns,
            field_mapping=field_mapping,
        )

        if not column_to_csv_key:
            raise ValueError(
                "Unable to map any data template columns to CSV fields. Ensure CSV headers match data template column names."
            )

        # Build task property payload
        properties_to_add = build_property_payload(
            data_rows=data_rows,
            column_to_csv_key=column_to_csv_key,
            data_columns=data_columns,
            interval=interval,
            data_template_id=data_template_id,
        )

        if not properties_to_add:
            raise ValueError("CSV data produced no values to import after filtering empty cells.")

        # Delete existing property data before writing new values
        logger.warning(
            "Existing property data for block %s, inventory %s, lot %s will be overwritten during CSV import.",
            block_id,
            inventory_id,
            lot_id or "None",
        )
        property_data_collection.bulk_delete_task_data(
            task_id=task_id,
            block_id=block_id,
            inventory_id=inventory_id,
            lot_id=lot_id,
            interval_id=interval,
        )

        property_data_collection.add_properties_to_task(
            inventory_id=inventory_id,
            task_id=task_id,
            block_id=block_id,
            lot_id=lot_id,
            properties=properties_to_add,
        )

        return self.get_by_id(id=task_id)

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
        task_id: list[TaskId] | None = None,
        linked_task: list[TaskId] | None = None,
        category: TaskCategory | str | list[str] | None = None,
        albert_id: list[str] | None = None,
        data_template: list[str] | None = None,
        assigned_to: list[str] | None = None,
        location: list[str] | None = None,
        priority: list[str] | None = None,
        status: list[str] | None = None,
        parameter_group: list[str] | None = None,
        created_by: list[str] | None = None,
        project_id: ProjectId | None = None,
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
            Data template names associated with tasks.
        assigned_to : list[str], optional
            User names assigned to the tasks.
        location : list[str], optional
            Locations where tasks are carried out.
        priority : list[str], optional
            Priority levels for filtering tasks.
        status : list[str], optional
            Task status values (e.g., Open, Done).
        parameter_group : list[str], optional
            Parameter Group names associated with tasks.
        created_by : list[str], optional
            User names who created the tasks.
        project_id : ProjectId, optional
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
        if project_id is not None:
            project_id = remove_id_prefix(project_id, "ProjectId")

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

    @validate_call
    def get_all(
        self,
        *,
        text: str | None = None,
        tags: list[str] | None = None,
        task_id: list[TaskId] | None = None,
        linked_task: list[TaskId] | None = None,
        category: TaskCategory | str | list[str] | None = None,
        albert_id: list[str] | None = None,
        data_template: list[str] | None = None,
        assigned_to: list[str] | None = None,
        location: list[str] | None = None,
        priority: list[str] | None = None,
        status: list[str] | None = None,
        parameter_group: list[str] | None = None,
        created_by: list[str] | None = None,
        project_id: ProjectId | None = None,
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
            Data template names associated with tasks.
        assigned_to : list[str], optional
            User names assigned to the tasks.
        location : list[str], optional
            Locations where tasks are carried out.
        priority : list[str], optional
            Priority levels for filtering tasks.
        status : list[str], optional
            Task status values (e.g., Open, Done).
        parameter_group : list[str], optional
            Parameter Group names associated with tasks.
        created_by : list[str], optional
            User names who created the tasks.
        project_id : ProjectId, optional
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
        patch_payload = generate_adv_patch_payload(
            collection=self,
            updated=task,
            existing=existing,
        )

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
        """Fetch the audit history for the specified task."""
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
