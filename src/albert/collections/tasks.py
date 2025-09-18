from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from pydantic import validate_call
from requests.exceptions import RetryError

from albert.collections.attachments import AttachmentCollection
from albert.collections.base import BaseCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.notes import NotesCollection
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
    ParameterGroupId,
    ProjectId,
    TaskId,
    WorkflowId,
)
from albert.core.shared.models.base import EntityLink, EntityLinkWithName
from albert.core.shared.models.patch import PatchOperation
from albert.exceptions import AlbertHTTPError
from albert.resources.attachments import AttachmentCategory
from albert.resources.property_data import TaskDataColumn, TaskPropertyCreate
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
    def import_results_from_csv(
        self,
        *,
        task_id: TaskId,
        block_id: BlockId,
        inventory_id: InventoryId,
        data_template_id: DataTemplateId,
        csv_attachment_id: AttachmentId | None = None,
        csv_file_path: str | Path | None = None,
        note_text: str | None = None,
        lot_id: LotId | None = None,
        interval: str = "default",
        csv_table_key: str | None = None,
        column_mapping: dict[str, str] | None = None,
        mode: Literal["SCRIPT", "CSV"] = "CSV",
    ) -> BaseTask:
        """
        Import result values from a CSV attachment into task property data.

        This orchestrates the multi-step workflow of discovering the script attachment on the
        data template, filtering eligible CSV files on the task, optionally uploading a new file,
        reading the CSV preview, mapping the data columns, deleting existing property data, and
        finally posting the new values. The updated task is returned for convenience.

        Parameters
        ----------
        task_id : TaskId
            The property task receiving the results.
        block_id : BlockId
            Target block on the task where the data will be written.
        inventory_id : InventoryId
            Inventory identifier paired with the block.
        data_template_id : DataTemplateId
            Data template guiding the column mapping.
        csv_attachment_id : AttachmentId | None, optional
            Existing CSV attachment to use. If omitted a new upload or the first matching
            attachment will be used.
        csv_file_path : str | Path | None, optional
            Local CSV to upload and attach to a new note on the task.
        note_text : str | None, optional
            Optional text for the note created when uploading a new CSV.
        lot_id : LotId | None, optional
            Lot context when deleting/writing property data.
        interval : str, optional
            Interval combination to target. Defaults to "default".
        csv_table_key : str | None, optional
            Specific table key to read from the csvtables preview. Defaults to the first table.
        column_mapping : dict[str, str] | None, optional
            Optional mapping hints. Keys or values containing a data column ID (e.g. ``DAC1037``)
            are associated with the provided CSV identifier (either a ``col#`` key or header
            label).
        mode : Literal["SCRIPT", "CSV"], optional
            Workflow mode. Currently informational; script metadata is always leveraged.

        Returns
        -------
        BaseTask
            Hydrated task after property data import completes.
        """

        logger.info("Importing results for task %s using %s mode", task_id, mode)

        if csv_attachment_id and csv_file_path:
            raise ValueError("Provide either 'csv_attachment_id' or 'csv_file_path', not both.")

        # --- Discover allowed extensions from the data template script attachment ---
        attachment_collection = AttachmentCollection(session=self.session)
        data_template_collection = DataTemplateCollection(session=self.session)
        property_data_collection = PropertyDataCollection(session=self.session)
        notes_collection = NotesCollection(session=self.session)

        data_template = data_template_collection.get_by_id(id=data_template_id)

        def _extract_extensions_from_attachment(attachment) -> set[str]:
            metadata = getattr(attachment, "metadata", None)
            raw_extensions = []
            if metadata is None:
                return set()
            if isinstance(metadata, dict):
                raw_extensions = metadata.get("extensions", [])
            else:
                raw_extensions = getattr(metadata, "extensions", []) or []
            extensions = set()
            for ext in raw_extensions:
                name = ext.get("name") if isinstance(ext, dict) else getattr(ext, "name", None)
                if name:
                    extensions.add(name.lower().lstrip("."))
            return extensions

        script_attachments = attachment_collection.get_by_parent_ids(parent_ids=[data_template_id])
        script_entries = script_attachments.get(data_template_id, []) if script_attachments else []
        allowed_extensions = set()
        for script_attachment in script_entries:
            if (
                script_attachment.category
                and script_attachment.category != AttachmentCategory.SCRIPT
            ):
                continue
            allowed_extensions.update(_extract_extensions_from_attachment(script_attachment))
        if not allowed_extensions:
            allowed_extensions = {"csv"}

        def _collect_task_attachments() -> tuple[dict[str, object], list[object]]:
            attachments_by_id: dict[str, object] = {}
            ordered: list[object] = []
            for note in notes_collection.get_by_parent_id(parent_id=task_id):
                if not note.attachments:
                    continue
                for att in note.attachments:
                    attachments_by_id[att.id] = att
                    ordered.append(att)
            return attachments_by_id, ordered

        _, ordered_attachments = _collect_task_attachments()

        def _determine_extension(filename: str | None) -> str | None:
            if not filename:
                return None
            return Path(filename).suffix.lower().lstrip(".")

        # --- Optional upload of a new CSV file ---
        if csv_file_path is not None:
            csv_path = Path(csv_file_path).expanduser()
            if not csv_path.exists() or not csv_path.is_file():
                raise FileNotFoundError(f"CSV file not found at '{csv_path}'.")
            ext = _determine_extension(csv_path.name)
            if allowed_extensions and (ext or "") not in allowed_extensions:
                raise ValueError(
                    f"File extension '{ext}' is not permitted. Allowed extensions: {sorted(allowed_extensions)}"
                )
            note_text_to_use = note_text or ""
            with csv_path.open("rb") as csv_handle:
                attachment_collection.upload_and_attach_file_as_note(
                    parent_id=task_id,
                    file_data=csv_handle,
                    note_text=note_text_to_use,
                    file_name=csv_path.name,
                )
            # Refresh attachment cache including the newly uploaded file
            _, ordered_attachments = _collect_task_attachments()
            csv_candidates = [
                att
                for att in ordered_attachments
                if att.name and att.name.lower() == csv_path.name.lower()
            ]
            if not csv_candidates:
                raise ValueError("Uploaded CSV attachment could not be located on the task note.")
            csv_attachment_id = csv_candidates[0].id

        # --- Resolve the CSV attachment to use ---
        if csv_attachment_id is None:
            eligible = [
                att
                for att in ordered_attachments
                if _determine_extension(att.name) in allowed_extensions
            ]
            if not eligible:
                raise ValueError(
                    "No CSV attachments on the task match the extensions specified by the data template script."
                )
            csv_attachment_id = eligible[0].id
        else:
            csv_attachment_id = AttachmentId(csv_attachment_id)

        attachment_details = attachment_collection.get_by_id(id=csv_attachment_id)
        attachment_extension = _determine_extension(attachment_details.name)
        if allowed_extensions and attachment_extension not in allowed_extensions:
            raise ValueError(
                f"Attachment '{attachment_details.name}' does not match required extensions {sorted(allowed_extensions)}."
            )

        # --- Fetch and parse CSV preview ---
        csv_tables_response = self.session.get(
            f"/api/{self._api_version}/csvtables/{csv_attachment_id}"
        )
        csv_tables_payload = csv_tables_response.json()
        if not csv_tables_payload:
            raise ValueError("CSV preview response was empty; unable to import results.")

        if csv_table_key:
            if csv_table_key not in csv_tables_payload:
                raise ValueError(f"CSV table key '{csv_table_key}' not found in preview response.")
            table_rows = csv_tables_payload[csv_table_key]
        else:
            first_key = next(iter(csv_tables_payload))
            table_rows = csv_tables_payload[first_key]

        if not isinstance(table_rows, list) or len(table_rows) < 2:
            raise ValueError(
                "CSV preview must contain a header row followed by at least one data row."
            )

        header_row = table_rows[0]
        data_rows = [row for row in table_rows[1:] if isinstance(row, dict)]
        if not data_rows:
            raise ValueError("No data rows detected in CSV preview.")

        header_lookup = {}
        row_key_lookup = {}
        if isinstance(header_row, dict):
            for key, value in header_row.items():
                row_key_lookup[key.lower()] = key
                if isinstance(value, str):
                    header_lookup[value.strip().lower()] = key

        user_mapping: dict[str, str] = {}
        if column_mapping:
            for key, value in column_mapping.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError("column_mapping keys and values must be strings.")
                key_upper = key.upper()
                value_upper = value.upper()
                if key_upper.startswith("DAC"):
                    user_mapping[key_upper] = value
                elif value_upper.startswith("DAC"):
                    user_mapping[value_upper] = key
                else:
                    raise ValueError(
                        "column_mapping must include a data column ID (e.g. 'DAC1037') in either the key or the value."
                    )

        def _resolve_csv_identifier(identifier: str) -> str | None:
            candidate = identifier.strip()
            candidate_lower = candidate.lower()
            if candidate_lower in row_key_lookup:
                return row_key_lookup[candidate_lower]
            if candidate_lower.startswith("col"):
                return row_key_lookup.get(candidate_lower)
            header_match = header_lookup.get(candidate_lower)
            if header_match:
                return header_match
            return None

        def _auto_map_sequence(sequence: str | None) -> str | None:
            if not sequence:
                return None
            digits = "".join(ch for ch in sequence if ch.isdigit())
            if not digits:
                return None
            return _resolve_csv_identifier(f"col{digits}")

        column_to_csv_key: dict[str, str] = {}
        data_columns = data_template.data_column_values or []
        for column in data_columns:
            if getattr(column, "hidden", False):
                continue
            csv_identifier = None
            if user_mapping:
                csv_identifier = user_mapping.get(column.data_column_id)
            if csv_identifier:
                resolved = _resolve_csv_identifier(csv_identifier)
            else:
                resolved = _auto_map_sequence(column.sequence)
                if resolved is None:
                    for label in filter(None, [column.name, column.original_name]):
                        resolved = _resolve_csv_identifier(label)
                        if resolved:
                            break
            if resolved:
                column_to_csv_key[column.data_column_id] = resolved

        if not column_to_csv_key:
            raise ValueError(
                "Unable to map any data template columns to CSV fields. Provide 'column_mapping' hints or verify the CSV header matches the template."
            )

        # --- Build task property payload ---
        properties_to_add: list[TaskPropertyCreate] = []
        for trial_index, row in enumerate(data_rows, start=1):
            for data_column_id, csv_key in column_to_csv_key.items():
                value = row.get(csv_key)
                if value is None or value == "":
                    continue
                value_str = str(value)
                column = next(
                    (c for c in data_columns if c.data_column_id == data_column_id), None
                )
                if column is None:
                    continue
                properties_to_add.append(
                    TaskPropertyCreate(
                        data_column=TaskDataColumn(
                            data_column_id=data_column_id,
                            column_sequence=column.sequence,
                        ),
                        value=value_str,
                        visible_trial_number=trial_index,
                        interval_combination=interval,
                        data_template=EntityLink(id=data_template_id),
                    )
                )

        if not properties_to_add:
            raise ValueError("CSV data produced no values to import after filtering empty cells.")

        # --- Delete existing property data if present ---
        existing_data_info = property_data_collection.check_for_task_data(task_id=task_id)
        target_combo = next(
            (
                combo
                for combo in existing_data_info
                if combo.block_id == block_id
                and combo.inventory_id == inventory_id
                and (lot_id is None or combo.lot_id == lot_id)
            ),
            None,
        )
        if target_combo and target_combo.data_exists:
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

        # Return the refreshed task representation
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
        category: TaskCategory | None = None,
        albert_id: list[str] | None = None,
        data_template: list[DataTemplateId] | None = None,
        assigned_to: list[str] | None = None,
        location: list[str] | None = None,
        priority: list[str] | None = None,
        status: list[str] | None = None,
        parameter_group: list[ParameterGroupId] | None = None,
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
            Data template IDs associated with tasks.
        assigned_to : list[str], optional
            User names assigned to the tasks.
        location : list[str], optional
            Locations where tasks are carried out.
        priority : list[str], optional
            Priority levels for filtering tasks.
        status : list[str], optional
            Task status values (e.g., Open, Done).
        parameter_group : list[str], optional
            Parameter Group IDs associated with tasks.
        created_by : list[str], optional
            User names who created the tasks.
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

    @validate_call
    def get_all(
        self,
        *,
        text: str | None = None,
        tags: list[str] | None = None,
        task_id: list[TaskId] | None = None,
        linked_task: list[TaskId] | None = None,
        category: TaskCategory | None = None,
        albert_id: list[str] | None = None,
        data_template: list[DataTemplateId] | None = None,
        assigned_to: list[str] | None = None,
        location: list[str] | None = None,
        priority: list[str] | None = None,
        status: list[str] | None = None,
        parameter_group: list[ParameterGroupId] | None = None,
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
            Data template IDs associated with tasks.
        assigned_to : list[str], optional
            User names assigned to the tasks.
        location : list[str], optional
            Locations where tasks are carried out.
        priority : list[str], optional
            Priority levels for filtering tasks.
        status : list[str], optional
            Task status values (e.g., Open, Done).
        parameter_group : list[str], optional
            Parameter Group IDs associated with tasks.
        created_by : list[str], optional
            User names who created the tasks.
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
