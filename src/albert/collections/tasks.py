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
from albert.core.utils import ensure_list
from albert.exceptions import AlbertHTTPError
from albert.resources.attachments import AttachmentCategory
from albert.resources.data_templates import ImportMode
from albert.resources.tasks import (
    BaseTask,
    BatchTask,
    CsvTableInput,
    CsvTableResponseItem,
    GeneralTask,
    HistoryEntity,
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
    """Manage Tasks in the Albert platform.

    A Task is a unit of lab work. There are three kinds, and choosing the right
    one matters:

    - **PropertyTask**: test and document the properties of products/formulas or
      raw materials. This is the task type that captures measured Property Data.
      A PropertyTask holds one or more *Blocks*, each pairing a Data Template
      (the results to capture) with a Workflow (the conditions to run under).
    - **BatchTask**: manufacture a batch within Albert after creating a new
      formulation.
    - **GeneralTask**: anything else happening in the lab that is not a batch or
      property task (e.g. equipment calibration). Has no blocks.

    Typical PropertyTask flow: create the task, attach a Block with
    [`add_block`][albert.collections.tasks.TaskCollection.add_block] (a Data Template + a Workflow), then record results through
    the Property Data collection
    ([`PropertyDataCollection`][albert.collections.property_data.PropertyDataCollection]). Measured
    results roll up to the associated inventory item's properties.

    This collection is accessed as ``client.tasks``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for task requests.

    Methods
    -------
    create(task) -> BaseTask
        Create a PropertyTask, BatchTask, or GeneralTask.
    get_by_id(id) -> BaseTask
        Get a single fully populated task by its ID.
    search(...) -> Iterator[TaskSearchItem]
        Fast, lightweight search returning partial tasks.
    get_all(...) -> Iterator[BaseTask]
        Same filters as search, but returns fully populated tasks.
    update(task) -> BaseTask
        Update an existing task.
    delete(id) -> None
        Delete a task by its ID.
    add_block(task_id, data_template_id, workflow_id) -> None
        Add a Block (Data Template + Workflow) to a Property or Batch task.
    remove_block(task_id, block_id) -> None
        Remove a Block from a Property or Batch task.
    update_block_workflow(task_id, block_id, workflow_id) -> None
        Swap the Workflow assigned to a Block.
    import_results(...) -> BaseTask
        Import measured results into a Property task from a file or attachment.
    get_history(id, ...) -> TaskHistory
        Get a task's audit history.

    Examples
    --------
    ```python
    from albert import Albert
    from albert.resources.tasks import PropertyTask
    client = Albert()
    task = client.tasks.create(
        task=PropertyTask(name="Viscosity screen", parent_id="PRO1")
    )
    client.tasks.add_block(
        task_id=task.id, data_template_id="DAT1", workflow_id="WFL1"
    )
    ```
    """

    _api_version = "v3"
    _updatable_attributes = {
        "metadata",
        "name",
        "priority",
        "state",
        "due_date",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize a TaskCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{TaskCollection._api_version}/tasks"

    def create(self, *, task: PropertyTask | GeneralTask | BatchTask) -> BaseTask:
        """Create a new task.

        Pass the concrete task type you want to create. Its ``category`` is set
        automatically by the type, so the platform routes it correctly:

        - [`PropertyTask`][albert.resources.tasks.PropertyTask]: test/document properties.
        - [`BatchTask`][albert.resources.tasks.BatchTask]: manufacture a batch.
        - [`GeneralTask`][albert.resources.tasks.GeneralTask]: any other lab work.

        For a PropertyTask, set ``parent_id`` to the parent Project ID. Blocks are
        added separately with [`add_block`][albert.collections.tasks.TaskCollection.add_block] after creation.

        Parameters
        ----------
        task : PropertyTask or GeneralTask or BatchTask
            The task to create. ``name`` is required.

        Returns
        -------
        BaseTask
            The created task (a ``PropertyTask``, ``BatchTask``, or ``GeneralTask``),
            populated with its assigned Task ID.

        Examples
        --------
        ```python
        from albert.resources.tasks import GeneralTask
        task = client.tasks.create(task=GeneralTask(name="Calibrate balance"))
        task.id
        # 'TASGEN1'
        ```
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
        """Add a Block to a Property or Batch task.

        A Block pairs a Data Template (the results/data columns to capture) with a
        Workflow (the parameter conditions to run under). A task can hold multiple
        blocks, e.g. one per test. Once a block exists, results are written against
        it through the Property Data collection.

        Parameters
        ----------
        task_id : TaskId
            The task to add the block to (format ``TAS...``).
        data_template_id : DataTemplateId
            The Data Template supplying the block's results/data columns
            (format ``DAT...``).
        workflow_id : WorkflowId
            The Workflow supplying the block's parameter conditions
            (format ``WFL...``).

        Returns
        -------
        None

        See Also
        --------
        remove_block : Remove a block from a task.
        update_block_workflow : Change the workflow on an existing block.

        Examples
        --------
        ```python
        client.tasks.add_block(
            task_id="TASFOR1", data_template_id="DAT1", workflow_id="WFL1"
        )
        ```
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
        """Swap the Workflow assigned to a Block within a task.

        Use this to change the conditions a block runs under without removing and
        re-adding the block. The task must be a Property or Batch task.

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        block_id : BlockId
            The block to update (format ``BLK...``).
        workflow_id : WorkflowId
            The new Workflow to assign to the block (format ``WFL...``).

        Returns
        -------
        None

        Raises
        ------
        TypeError
            If the task is not a PropertyTask or BatchTask.

        Notes
        -----
        If the block already uses ``workflow_id``, no change is made. A block's
        default placeholder workflow ("No Parameter Group") is skipped when it is
        not the block's only workflow.

        Examples
        --------
        ```python
        client.tasks.update_block_workflow(
            task_id="TASFOR1", block_id="BLK1", workflow_id="WFL2"
        )
        ```
        """
        url = f"{self.base_path}/{task_id}"
        task = self.get_by_id(id=task_id)
        if not isinstance(task, PropertyTask | BatchTask):
            logger.error(f"Task {task_id} is not a PropertyTask or BatchTask")
            raise TypeError(f"Task {task_id} is not a PropertyTask or BatchTask")
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
        """Remove a Block from a Property or Batch task.

        Removing a block also removes the results captured against it. To keep the
        block but change its conditions, use [`update_block_workflow`][albert.collections.tasks.TaskCollection.update_block_workflow] instead.

        Parameters
        ----------
        task_id : TaskId
            The task to remove the block from (e.g. ``"TASFOR1234"``).
        block_id : BlockId
            The block to remove (e.g. ``"BLK1"``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.tasks.remove_block(task_id="TASFOR1234", block_id="BLK1")
        ```
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
            Interval combination to write to, as an interval ID (``"ROW1"`` for a
            single intervalized parameter, ``"ROW1XROW2"`` for two). Defaults to
            ``"default"`` when the block has no intervalized parameters. Build the
            ID from parameter values with
            [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id].
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
        ```python
        from albert.resources.data_templates import ImportMode
        task = client.tasks.import_results(
            task_id="TAS123",
            inventory_id="INVA123",
            data_template_id="DAT123",
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
        """Delete a task by its ID.

        Deleting a task also removes any results recorded against its blocks.

        Parameters
        ----------
        id : TaskId
            The task to delete (format ``TAS...``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.tasks.delete(id="TASFOR1")
        ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def get_by_id(self, *, id: TaskId) -> BaseTask:
        """Get a single, fully populated task by its ID.

        The returned object is the concrete type matching the task's category:
        ``PropertyTask``, ``BatchTask``, or ``GeneralTask``. For a PropertyTask
        this includes its blocks.

        Parameters
        ----------
        id : TaskId
            The task to retrieve (format ``TAS...``).

        Returns
        -------
        BaseTask
            The fully populated task.

        Examples
        --------
        ```python
        task = client.tasks.get_by_id(id="TASFOR1")
        task.name
        # 'Viscosity screen'
        ```
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
        """Search for tasks matching the given filters.

        Returns lightweight, partially populated results and is the fastest way to
        look tasks up. When you need complete tasks (e.g. a PropertyTask's blocks),
        use [`get_all`][albert.collections.tasks.TaskCollection.get_all] with the same filters, or pass the resulting IDs to
        [`get_by_id`][albert.collections.tasks.TaskCollection.get_by_id]. Results are returned as a lazily paginated iterator.

        Parameters
        ----------
        text : str, optional
            Text search across multiple task fields.
        tags : list[str], optional
            Filter by tags associated with tasks.
        task_id : list[str], optional
            Filter by task IDs (e.g., ``["TAS123", "TAS456"]``).
        linked_task : list[str], optional
            Task IDs linked to the ones being searched.
        category : TaskCategory, optional
            Filter by task category: ``Property``, ``Batch``, or ``General``.
        albert_id : list[str], optional
            Filter by Albert IDs of entities linked to the tasks (e.g. inventory
            IDs like ``["INVA46", "INVA50"]``).
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
            Maximum number of tasks to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[TaskSearchItem]
            A lazily paginated iterator of partially populated search results.

        Examples
        --------
        ```python
        from albert.resources.tasks import TaskCategory
        hits = client.tasks.search(
            category=TaskCategory.PROPERTY, status=["Open"], max_items=20
        )
        for t in hits:
            print(t.id, t.name)
        ```
        """
        if project_id is not None:
            project_id = remove_id_prefix(project_id, "ProjectId")

        params = {
            "offset": offset,
            "order": order_by,
            "text": text,
            "sortBy": sort_by,
            "tags": tags,
            "taskId": task_id,
            "linkedTask": linked_task,
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

        category_values = ensure_list(category)
        params["category"] = category_values if category_values else None

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
        """Get fully populated tasks matching the given filters.

        Accepts the same filters as [`search`][albert.collections.tasks.TaskCollection.search] but returns complete task
        entities (``PropertyTask``, ``BatchTask``, or ``GeneralTask``) rather than
        lightweight search results. This is slower because it fetches full detail
        for every match, so prefer [`search`][albert.collections.tasks.TaskCollection.search] when you only need names, IDs, or
        status. Results are returned as a lazily paginated iterator.

        Parameters
        ----------
        text : str, optional
            Text search across multiple task fields.
        tags : list[str], optional
            Filter by tags associated with tasks.
        task_id : list[str], optional
            Filter by task IDs (e.g. ``["TAS123", "TAS456"]``).
        linked_task : list[str], optional
            Task IDs linked to the ones being searched.
        category : TaskCategory, optional
            Filter by task category: ``Property``, ``Batch``, or ``General``.
        albert_id : list[str], optional
            Filter by Albert IDs of entities linked to the tasks (e.g. inventory
            IDs like ``["INVA46", "INVA50"]``).
        data_template : list[str], optional
            Data template names associated with tasks.
        assigned_to : list[str], optional
            User names assigned to the tasks.
        location : list[str], optional
            Locations where tasks are carried out.
        priority : list[str], optional
            Priority levels for filtering tasks.
        status : list[str], optional
            Task status values (e.g. ``"Open"``, ``"Done"``).
        parameter_group : list[str], optional
            Parameter Group names associated with tasks.
        created_by : list[str], optional
            User names who created the tasks.
        project_id : ProjectId, optional
            ID of the parent project for filtering tasks.
        order_by : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        sort_by : str, optional
            Attribute to sort tasks by (e.g. ``createdAt``, ``name``).
        max_items : int, optional
            Maximum number of tasks to return in total. If None, iterates over all
            matches.

        Yields
        ------
        BaseTask
            Each fully populated task (``PropertyTask``, ``BatchTask``, or
            ``GeneralTask``).

        Examples
        --------
        ```python
        from albert.resources.tasks import TaskCategory
        for task in client.tasks.get_all(
            category=TaskCategory.PROPERTY, max_items=50
        ):
            print(task.id, task.name)
        ```
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
        """Update an existing task.

        Fetch the task (e.g. with [`get_by_id`][albert.collections.tasks.TaskCollection.get_by_id]), modify the updatable fields,
        then pass it here. Only the fields listed in Notes are applied. To change a
        task's blocks, use [`add_block`][albert.collections.tasks.TaskCollection.add_block], [`remove_block`][albert.collections.tasks.TaskCollection.remove_block], or
        [`update_block_workflow`][albert.collections.tasks.TaskCollection.update_block_workflow] instead.

        Parameters
        ----------
        task : BaseTask
            The task to update. Must have a valid ``id``.

        Returns
        -------
        BaseTask
            The updated task.

        Notes
        -----
        The following fields can be updated: ``due_date``, ``metadata``, ``name``,
        ``priority``, ``project``, ``state``.

        Examples
        --------
        ```python
        from albert.resources.tasks import TaskPriority
        task = client.tasks.get_by_id(id="TASFOR1")
        task.priority = TaskPriority.HIGH
        updated = client.tasks.update(task=task)
        ```
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

    @validate_call
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
        """Get the audit history for a task.

        Returns the chronological record of changes made to the task (and,
        optionally, a specific block).

        Parameters
        ----------
        id : TaskId
            The task to inspect (format ``TAS...``).
        order : OrderBy, optional
            Sort direction for history entries. Default ``OrderBy.DESCENDING``.
        limit : int, optional
            Maximum number of history entries to return.
        entity : HistoryEntity, optional
            Restrict history to a specific entity scope (e.g. ``workflow``).
        blockId : str, optional
            Restrict history to a specific block.
        startKey : str, optional
            Pagination key used to continue a previous history query.

        Returns
        -------
        TaskHistory
            The task's history entries plus pagination metadata.

        Examples
        --------
        ```python
        history = client.tasks.get_history(id="TASFOR1")
        len(history.items)
        # 12
        ```
        """
        params = {
            "limit": limit,
            "orderBy": order,
            "entity": entity,
            "blockId": blockId,
            "startKey": startKey,
        }
        url = f"{self.base_path}/{id}/history"
        response = self.session.get(url, params=params)
        return TaskHistory(**response.json())
