from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path
from typing import Any

import requests
from pydantic import validate_call
from requests.exceptions import RetryError

from albert.collections.attachments import AttachmentCollection
from albert.collections.base import BaseCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.property_data import PropertyDataCollection
from albert.collections.workflows import WorkflowCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator, MappedPaginator
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
from albert.exceptions import (
    AlbertException,
    AlbertHTTPError,
    CombinationGenerationError,
    NotFoundError,
)
from albert.resources.attachments import AttachmentCategory
from albert.resources.data_templates import ImportMode
from albert.resources.interval_combinations import (
    BlockRules,
    CombinationOverride,
    ExclusionRule,
    IntervalCombinationItem,
)
from albert.resources.tasks import (
    BaseTask,
    BatchTask,
    Block,
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
from albert.resources.worker_jobs import (
    WorkerJob,
    WorkerJobCreateRequest,
    WorkerJobMetadata,
    WorkerJobState,
)
from albert.resources.workflows import Workflow
from albert.utils.interval_combinations import generate_interval_combinations
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
from albert.utils.worker_jobs import poll_worker_job

_BLOCK_COMBINATION_JOB_GAP_SECONDS: float = 10.0
"""Minimum interval in seconds between kicking off consecutive block combination worker jobs.

Submitting multiple block child-workflow generation jobs concurrently on a newly created task
can trigger backend database lock contention or worker queue race conditions on the parent task
record. Pacing consecutive job submissions by 10 seconds allows each job to initialize cleanly.
"""


class _BlockCombinationsPaginator(AlbertPaginator):
    """KEY-mode paginator for GET /tasks/{id}/blocks/{blockId}/combinations.

    The envelope lists items under ``combinations``, not ``Items``. ``lastKey`` is
    omitted when exhausted; a page may under-return because of DynamoDB's 1MB cap,
    so completion is inferred from ``lastKey``, not page size.
    """

    def _response_items(self, data: dict[str, Any]) -> list:
        return data.get("combinations") or []


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

    !!! example
        ```python
        from albert import Albert
        from albert.resources.tasks import PropertyTask
        client = Albert()
        task = client.tasks.create(
            task=PropertyTask(name="Viscosity screen", parent_id="PROA9999999")
        )
        client.tasks.add_block(
            task_id=task.id, data_template_id="DAT9999999", workflow_id="WFL1"
        )
        ```

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
    create_with_combinations(task, wait=True) -> PropertyTask (🧪 Beta)
        Create a Property task and orchestrate combination generation across all its blocks.
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
    get_block_combinations(task_id, block_id, max_items=None) -> Iterator[IntervalCombinationItem] (🧪 Beta)
        Get the child-workflow combinations of a block.
    get_block_rules(task_id, block_id) -> BlockRules (🧪 Beta)
        Get combination rules and overrides for a block.
    set_block_rules(task_id, block_id, rules=None, overrides=None, generate_combinations=True, wait=True) -> BlockRules (🧪 Beta)
        Set combination rules and overrides for a block, automatically regenerating combinations.
    generate_block_combinations(task_id, block_id, old_workflow_id=None, wait=True) -> WorkerJob (🧪 Beta)
        Generate child-workflow interval combinations for a task block.
    import_results(...) -> BaseTask
        Import measured results into a Property task from a file or attachment.
    get_history(id, ...) -> TaskHistory
        Get a task's audit history.
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

        !!! example
            ```python
            from albert.resources.tasks import GeneralTask
            task = client.tasks.create(task=GeneralTask(name="Calibrate balance"))
            task.id
            # 'TASGEN1'
            ```

        Parameters
        ----------
        task : PropertyTask or GeneralTask or BatchTask
            The task to create. ``name`` is required.

        Returns
        -------
        BaseTask
            The created task (a ``PropertyTask``, ``BatchTask``, or ``GeneralTask``),
            populated with its assigned Task ID.
        """
        payload = [task.model_dump(mode="json", by_alias=True, exclude_none=True)]
        url = f"{self.base_path}/multi?category={task.category.value}"
        if task.parent_id is not None:
            url = f"{url}&parentId={task.parent_id}"
        response = self.session.post(url=url, json=payload)
        task_data = response.json()[0]
        return TaskAdapter.validate_python(task_data)

    @validate_call
    def create_with_combinations(
        self,
        *,
        task: PropertyTask,
        wait: bool = True,
    ) -> PropertyTask:
        """Create a Property task and generate interval combinations across all its blocks (🧪 Beta).

        Provides an all-in-one method to create a Property task and materialize
        combination variants for every block:
        1. Automatically saves any unsaved [`Workflow`][albert.resources.workflows.Workflow]
           objects defined on the task blocks, preserving block ordering.
        2. Sets ``intervals_start_from="all"`` (exclude mode) on any blocks where the
           mode is not explicitly configured.
        3. Creates the task and saves any configured block rules ([`ExclusionRule`][albert.resources.interval_combinations.ExclusionRule])
           or overrides ([`CombinationOverride`][albert.resources.interval_combinations.CombinationOverride]).
        4. Sequentially triggers combination generation for each block, pacing requests
           to ensure steady platform processing.
        5. If ``wait=True`` (the default), waits for combination generation to complete across
           all blocks and returns the refreshed task with combination details populated.
           If ``wait=False``, returns immediately after launching generation, leaving
           job tracking identifiers on each block.

        To view the generated combinations after creation, use
        [`get_block_combinations`][albert.collections.tasks.TaskCollection.get_block_combinations].
        To update rules or regenerate combinations on an existing task later, use
        [`set_block_rules`][albert.collections.tasks.TaskCollection.set_block_rules] and
        [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations].

        !!! warning "Beta Feature!"
            Increased intervals combination support is currently in beta and behind a platform
            feature flag. Please do not use in production or without explicit guidance from
            Albert. You might otherwise have a bad experience. This feature currently falls
            outside of the Albert support contract, but we'd love your feedback!

        !!! example
            ```python
            from albert import Albert
            from albert.resources.tasks import Block, PropertyTask

            client = Albert()
            task = client.tasks.create_with_combinations(
                task=PropertyTask(
                    name="Viscosity screen",
                    parent_id="PROA123",
                    blocks=[
                        Block(
                            data_template=[{"id": "DAT123"}],
                            workflow=[{"id": "WFL456"}],
                        ),
                    ],
                ),
                wait=True,
            )
            task.id
            # 'TASFOR1'
            ```

        Parameters
        ----------
        task : PropertyTask
            The Property task definition to create, containing one or more
            [`Block`][albert.resources.tasks.Block] instances. Each block must have a
            data template and a workflow (either an existing workflow ID or a new
            [`Workflow`][albert.resources.workflows.Workflow] object), plus optional rules
            and overrides.
        wait : bool, default True
            Whether to wait for combination generation to complete across all blocks.
            If False, returns immediately after submitting generation jobs.

        Returns
        -------
        PropertyTask
            The created Property task. If ``wait=True``, returns the re-fetched task with
            combinations populated. If ``wait=False``, returns the task with job identifiers
            assigned on each block.

        Raises
        ------
        TypeError
            If ``task`` is not a ``PropertyTask``.
        CombinationGenerationError
            If ``wait=True`` and combination generation fails on one or more blocks.
            The exception carries the created task (``err.task``) and failed block IDs
            (``err.failed_blocks``) so callers can inspect or retry specific blocks using
            [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations].
        """
        if not isinstance(task, PropertyTask):
            raise TypeError("task must be a PropertyTask")

        task = task.model_copy(deep=True)
        workflow_collection = WorkflowCollection(session=self.session)

        # 1. Ensure all workflows have an ID (create unsaved workflows if needed)
        if task.blocks:
            for i, block in enumerate(task.blocks):
                if not block.workflow:
                    continue
                for w in block.workflow:
                    if isinstance(w, Workflow) and not w.id:
                        w.block_mapping = str(i)
                        created_wfls = workflow_collection.create(workflows=[w])
                        w.id = created_wfls[0].id

            # 2. Fill intervals_start_from on any block where it is unset
            for block in task.blocks:
                if block.intervals_start_from is None:
                    block.intervals_start_from = "all"

        # 3. Create the task via standard create
        created_task = self.create(task=task)
        if not isinstance(created_task, PropertyTask):
            raise TypeError(f"Created task {created_task.id} is not a PropertyTask")

        if not created_task.blocks:
            return created_task

        # 4. Persist rules and overrides if specified on any block
        rules_payload = []
        for orig_b, created_b in zip(task.blocks, created_task.blocks, strict=False):
            if orig_b.rules or orig_b.overrides:
                rules_payload.append(
                    {
                        "blockId": created_b.id,
                        "rules": [
                            r.model_dump(by_alias=True, mode="json", exclude_none=True)
                            for r in (orig_b.rules or [])
                        ],
                        "overrides": [
                            o.model_dump(by_alias=True, mode="json", exclude_none=True)
                            for o in (orig_b.overrides or [])
                        ],
                    }
                )
        if rules_payload:
            self.session.put(f"{self.base_path}/{created_task.id}/rules", json=rules_payload)

        # 5. Sequentially trigger generate_block_combinations for each block with paced delay
        jobs: dict[str, WorkerJob] = {}
        last_job_time = 0.0

        for i, created_b in enumerate(created_task.blocks):
            if i > 0 and last_job_time > 0:
                elapsed = time.time() - last_job_time
                remaining = _BLOCK_COMBINATION_JOB_GAP_SECONDS - elapsed
                if remaining > 0:
                    time.sleep(remaining)

            job = self.generate_block_combinations(
                task_id=created_task.id,
                block_id=created_b.id,
                old_workflow_id=None,
                wait=False,
            )
            last_job_time = time.time()
            jobs[created_b.id] = job

        # 6. Handle wait semantics
        if wait:
            failed_blocks: list[str] = []
            job_states: dict[str, str] = {}
            for blk_id, job in jobs.items():
                try:
                    completed_job = poll_worker_job(
                        session=self.session,
                        job_id=job.albert_id,
                        raise_on_failure=False,
                        job_description=f"Create child workflows for task {created_task.id} block {blk_id}",
                    )
                    job_states[blk_id] = completed_job.state.value
                    if completed_job.state != WorkerJobState.SUCCESSFUL:
                        failed_blocks.append(blk_id)
                except (TimeoutError, AlbertException):
                    failed_blocks.append(blk_id)
                    job_states[blk_id] = "failed"

            if failed_blocks:
                refetched = self.get_by_id(id=created_task.id)
                raise CombinationGenerationError(
                    f"Combination generation failed for blocks: {', '.join(failed_blocks)}",
                    task=refetched,
                    failed_blocks=failed_blocks,
                    job_states=job_states,
                )

            refetched = self.get_by_id(id=created_task.id)
            if not isinstance(refetched, PropertyTask):
                raise TypeError(f"Refetched task {refetched.id} is not a PropertyTask")
            return refetched

        for blk in created_task.blocks:
            if blk.id in jobs:
                blk.job_id = jobs[blk.id].albert_id
                blk.job_state = jobs[blk.id].state.value
        return created_task

    @validate_call
    def add_block(
        self, *, task_id: TaskId, data_template_id: DataTemplateId, workflow_id: WorkflowId
    ) -> None:
        """Add a Block to a Property or Batch task.

        A Block pairs a Data Template (the results/data columns to capture) with a
        Workflow (the parameter conditions to run under). A task can hold multiple
        blocks, e.g. one per test. Once a block exists, results are written against
        it through the Property Data collection.

        !!! example
            ```python
            client.tasks.add_block(
                task_id="TASFOR1", data_template_id="DAT9999999", workflow_id="WFL1"
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task to add the block to (format ``TAS...``).
        data_template_id : DataTemplateId
            The Data Template supplying the block's results/data columns
            (format ``DAT...``).
        workflow_id : WorkflowId
            The Workflow supplying the block's parameter conditions
            (format ``WFL...``). When no parameter groups apply, use ``WFL1``, the
            platform default ("No Parameter Group").

        Returns
        -------
        None

        See Also
        --------
        remove_block : Remove a block from a task.
        update_block_workflow : Change the workflow on an existing block.
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

        !!! example
            ```python
            client.tasks.update_block_workflow(
                task_id="TASFOR1", block_id="BLK1", workflow_id="WFL2"
            )
            ```

        Parameters
        ----------
        task_id : TaskId
            The task containing the block (format ``TAS...``).
        block_id : BlockId
            The block to update (format ``BLK...``).
        workflow_id : WorkflowId
            The new Workflow to assign to the block (format ``WFL...``). When no
            parameter groups apply, use ``WFL1``, the platform default ("No Parameter Group").

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
        """
        url = f"{self.base_path}/{task_id}"
        task = self.get_by_id(id=task_id)
        if not isinstance(task, PropertyTask | BatchTask):
            logger.error(f"Task {task_id} is not a PropertyTask or BatchTask")
            raise TypeError(f"Task {task_id} is not a PropertyTask or BatchTask")
        existing_workflow_id: str | None = None
        initial_workflow_id: str | None = None
        for b in task.blocks:
            if b.id != block_id:
                continue
            for w in b.workflow:
                if w.name == "No Parameter Group" and len(b.workflow) > 1:
                    # hardcoded default workflow
                    continue
                if w.category == "INITIAL":
                    if initial_workflow_id is None:
                        initial_workflow_id = w.id
                else:
                    existing_workflow_id = w.id
            if existing_workflow_id is None:
                existing_workflow_id = initial_workflow_id
            break
        if existing_workflow_id is None:
            logger.error(f"No workflow found for block {block_id} on task {task_id}")
            raise ValueError(f"No workflow found for block {block_id} on task {task_id}")
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
    def get_block_combinations(
        self, *, task_id: TaskId, block_id: BlockId, max_items: int | None = None
    ) -> Iterator[IntervalCombinationItem]:
        """Get the child-workflow interval combinations of a task block (🧪 Beta).

        Retrieves the combinations generated for a task block by
        [`create_with_combinations`][albert.collections.tasks.TaskCollection.create_with_combinations]
        or [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations].

        Always use this method rather than reading combinations directly from the task
        or block record: for blocks with 500 or more combinations, embedded combination
        lists on the block are truncated or omitted.

        Results are returned as a lazily paginated iterator. Do not infer the end
        of results from page size: a page can under-return while more combinations
        remain.

        !!! warning "Beta Feature!"
            Increased intervals combination support is currently in beta and behind a platform
            feature flag. Please do not use in production or without explicit guidance from
            Albert. You might otherwise have a bad experience. This feature currently falls
            outside of the Albert support contract, but we'd love your feedback!

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            combos = client.tasks.get_block_combinations(
                task_id="TASFOR1", block_id="BLK1"
            )
            [(c.id, c.interval_barcode) for c in combos]
            # [('WFL999', 'OhI8ap0HY')]
            ```

        Parameters
        ----------
        task_id : TaskId
            The Property task ID containing the block (format ``TAS...``), obtained
            from [`create`][albert.collections.tasks.TaskCollection.create],
            [`create_with_combinations`][albert.collections.tasks.TaskCollection.create_with_combinations],
            or [`get_by_id`][albert.collections.tasks.TaskCollection.get_by_id].
        block_id : BlockId
            The block ID whose combinations to list (format ``BLK...``), obtained
            from ``task.blocks[i].id`` on a fetched task.
        max_items : int, optional
            Maximum number of combinations to return. If None, iterates over all
            combinations.

        Returns
        -------
        Iterator[IntervalCombinationItem]
            A lazily paginated iterator of combinations. After iteration,
            ``has_more`` is True when ``max_items`` stopped the iterator and more
            combinations remain.
        """
        return _BlockCombinationsPaginator(
            mode=PaginationMode.KEY,
            path=f"{self.base_path}/{task_id}/blocks/{block_id}/combinations",
            session=self.session,
            max_items=max_items,
            deserialize=lambda items: [IntervalCombinationItem(**item) for item in items],
        )

    @validate_call
    def get_block_rules(
        self,
        *,
        task_id: TaskId,
        block_id: BlockId,
    ) -> BlockRules:
        """Get combination rules and overrides for a task block (🧪 Beta).

        Returns the rules ([`ExclusionRule`][albert.resources.interval_combinations.ExclusionRule])
        and overrides ([`CombinationOverride`][albert.resources.interval_combinations.CombinationOverride])
        currently configured on the specified block.

        Use this method to inspect existing rules before updating them with
        [`set_block_rules`][albert.collections.tasks.TaskCollection.set_block_rules].
        Note that modifying rules on a block does not change its generated combinations
        until [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations]
        is run.

        !!! warning "Beta Feature!"
            Increased intervals combination support is currently in beta and behind a platform
            feature flag. Please do not use in production or without explicit guidance from
            Albert. You might otherwise have a bad experience. This feature currently falls
            outside of the Albert support contract, but we'd love your feedback!

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            rules_data = client.tasks.get_block_rules(
                task_id="TASFOR1", block_id="BLK1"
            )
            for rule in rules_data.rules:
                print(rule.name, rule.conditions)
            for override in rules_data.overrides:
                print(override.key, override.action)
            ```

        Parameters
        ----------
        task_id : TaskId
            The Property task ID containing the block (format ``TAS...``), obtained
            from [`create`][albert.collections.tasks.TaskCollection.create],
            [`create_with_combinations`][albert.collections.tasks.TaskCollection.create_with_combinations],
            or [`get_by_id`][albert.collections.tasks.TaskCollection.get_by_id].
        block_id : BlockId
            The block ID whose rules to retrieve (format ``BLK...``), obtained
            from ``task.blocks[i].id`` on a fetched task.

        Returns
        -------
        BlockRules
            The rules and overrides configured on the block.
        """
        url = f"{self.base_path}/{task_id}/blocks/{block_id}/rules"
        response = self.session.get(url)
        data = response.json()

        all_rules = list(data.get("rules", {}).get("items", []))
        last_key = data.get("rules", {}).get("lastKey")
        while last_key:
            next_resp = self.session.get(url, params={"startKey": last_key})
            next_data = next_resp.json()
            rules_obj = next_data.get("rules", {})
            all_rules.extend(rules_obj.get("items", []))
            last_key = rules_obj.get("lastKey")

        return BlockRules(
            task_id=data["taskId"],
            block_id=data["blockId"],
            rules=all_rules,
            overrides=data.get("overrides", []),
        )

    @staticmethod
    def _get_block_current_workflow_id(block: Block) -> str | None:
        """Resolve the active/final workflow ID for a block."""
        new_workflow_id: str | None = None
        unset_category_ids: list[str] = []
        for w in block.workflow or []:
            if getattr(w, "name", None) == "No Parameter Group" and len(block.workflow) > 1:
                continue
            category = getattr(w, "category", None)
            if category == "FINAL":
                return w.id
            if category == "INITIAL":
                continue
            if category is None:
                unset_category_ids.append(w.id)
            else:
                new_workflow_id = w.id
        if new_workflow_id is None and unset_category_ids:
            # Before the worker assigns categories, FINAL is conventionally first on the block.
            return unset_category_ids[0]
        if new_workflow_id is None and block.workflow:
            return block.workflow[0].id
        return new_workflow_id

    @validate_call
    def set_block_rules(
        self,
        *,
        task_id: TaskId,
        block_id: BlockId,
        rules: list[ExclusionRule] | None = None,
        overrides: list[CombinationOverride] | None = None,
        generate_combinations: bool = True,
        old_workflow_id: WorkflowId | None = None,
        wait: bool = True,
    ) -> BlockRules:
        """Set combination rules and overrides for a task block (🧪 Beta).

        Configures or replaces exclusion rules and overrides on the specified block, and
        by default immediately recomputes and regenerates child-workflow combinations on
        Albert Invent.

        Follows the unset-is-not-empty convention:
        - Omitting ``rules`` (or leaving it as ``None``) leaves existing rules untouched.
        - Passing an empty list (``rules=[]``) clears all rules on the block.
        - The same convention applies to ``overrides``.
        - At least one of ``rules`` or ``overrides`` must be provided.

        When ``generate_combinations=True`` (the default), the method persists the rules and
        immediately triggers [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations],
        passing the block's current workflow as ``old_workflow_id`` so that unchanged barcodes
        are preserved and obsolete combinations are voided. Set ``generate_combinations=False``
        to save rule definitions only without triggering combination regeneration.

        Rules and overrides can be constructed easily from parameter names and values using
        [`Workflow.build_rule`][albert.resources.workflows.Workflow.build_rule] and
        [`Workflow.build_override`][albert.resources.workflows.Workflow.build_override]
        on the block's parent workflow. Override keys can also be computed directly using
        [`Workflow.get_override_key`][albert.resources.workflows.Workflow.get_override_key].

        !!! warning "Beta Feature!"
            Increased intervals combination support is currently in beta and behind a platform
            feature flag. Please do not use in production or without explicit guidance from
            Albert. You might otherwise have a bad experience. This feature currently falls
            outside of the Albert support contract, but we'd love your feedback!

        !!! example
            ```python
            from albert import Albert
            from albert.resources.interval_combinations import (
                CombinationOverride,
                ExclusionRule,
                OverrideAction,
                RuleCondition,
                RuleOperator,
            )

            client = Albert()
            block_rules = client.tasks.set_block_rules(
                task_id="TASFOR1",
                block_id="BLK1",
                rules=[
                    ExclusionRule(
                        name="Exclude high temp and high speed",
                        conditions=[
                            RuleCondition(
                                parameter_group_id="PRG247776",
                                parameter_id="PRM100",
                                row_id="ROW2",
                                operator=RuleOperator.GTE,
                                value="90",
                                unit_id="UNI1",
                            ),
                            RuleCondition(
                                parameter_group_id="PRG247776",
                                parameter_id="PRM200",
                                row_id="ROW5",
                                operator=RuleOperator.GTE,
                                value="1500",
                                unit_id="UNI2",
                            ),
                        ],
                    )
                ],
                overrides=[
                    CombinationOverride(
                        key="PRG247776#PRM100#ROW4-PRG247776#PRM200#ROW9",
                        action=OverrideAction.SKIP,
                    ),
                ],
            )
            # Combinations are regenerated automatically:
            print(block_rules.job.state)
            # 'successful'
            ```

        Parameters
        ----------
        task_id : TaskId
            The Property task ID containing the block (format ``TAS...``), obtained
            from [`create`][albert.collections.tasks.TaskCollection.create],
            [`create_with_combinations`][albert.collections.tasks.TaskCollection.create_with_combinations],
            or [`get_by_id`][albert.collections.tasks.TaskCollection.get_by_id].
        block_id : BlockId
            The block ID whose rules to set (format ``BLK...``), obtained
            from ``task.blocks[i].id`` on a fetched task.
        rules : list[ExclusionRule], optional
            Replacement rules for the block. If omitted (``None``), existing rules
            are left untouched. If an empty list (``[]``), existing rules are cleared.
        overrides : list[CombinationOverride], optional
            Replacement overrides for the block. If omitted (``None``), existing
            overrides are left untouched. If an empty list (``[]``), existing
            overrides are cleared. Override keys can be generated via
            [`Workflow.get_override_key`][albert.resources.workflows.Workflow.get_override_key].
        generate_combinations : bool, default True
            Whether to automatically regenerate child-workflow combinations after saving
            rules. Defaults to True.
        old_workflow_id : WorkflowId, optional
            Prior workflow ID to pass to the generation job for barcode preservation
            and voiding obsolete combinations. Defaults to the block's current workflow ID.
        wait : bool, default True
            Whether to wait for the background generation worker job to finish when
            ``generate_combinations=True``. If False, returns immediately after submitting
            the job.

        Returns
        -------
        BlockRules
            The updated rules and overrides for the block. If ``generate_combinations=True``,
            the [`job`][albert.resources.interval_combinations.BlockRules.job] attribute contains
            the completed (or in-progress) background worker job.

        Raises
        ------
        ValueError
            If both ``rules`` and ``overrides`` are omitted, or if the block is not found.
        TypeError
            If the task is not a PropertyTask.
        AlbertException
            If combination generation fails or exceeds platform caps.
        """
        if rules is None and overrides is None:
            raise ValueError("At least one of 'rules' or 'overrides' must be provided.")

        block_payload: dict[str, Any] = {"blockId": block_id}

        if rules is not None:
            block_payload["rules"] = [
                r.model_dump(by_alias=True, mode="json", exclude_none=True) for r in rules
            ]

        if overrides is not None:
            block_payload["overrides"] = [
                o.model_dump(by_alias=True, mode="json", exclude_none=True) for o in overrides
            ]

        url = f"{self.base_path}/{task_id}/rules"
        response = self.session.put(url, json=[block_payload])
        resp_data = response.json()

        block_data = next((item for item in resp_data if item.get("blockId") == block_id), {})
        block_rules = BlockRules(
            task_id=task_id,
            block_id=block_id,
            rules=block_data.get("rules", []),
            overrides=block_data.get("overrides", []),
        )

        if generate_combinations:
            target_old_workflow_id = old_workflow_id
            if target_old_workflow_id is None:
                task = self.get_by_id(id=task_id)
                if not isinstance(task, PropertyTask):
                    raise TypeError(f"Task {task_id} must be a PropertyTask")
                target_block = next((b for b in task.blocks if b.id == block_id), None)
                if target_block is None:
                    raise ValueError(f"Block {block_id} not found on task {task_id}")
                target_old_workflow_id = self._get_block_current_workflow_id(target_block)

            block_rules.job = self.generate_block_combinations(
                task_id=task_id,
                block_id=block_id,
                old_workflow_id=target_old_workflow_id,
                wait=wait,
            )

        return block_rules

    @validate_call
    def generate_block_combinations(
        self,
        *,
        task_id: TaskId,
        block_id: BlockId,
        old_workflow_id: WorkflowId | None = None,
        wait: bool = True,
    ) -> WorkerJob:
        """Generate child-workflow interval combinations for a task block (🧪 Beta).

        Calculates combination variants from the block's workflow, rules, and overrides,
        then launches a background generation job to materialize the child workflows
        on the platform.

        How to set ``old_workflow_id`` across common caller scenarios:
        - **First-time generation** (or retrying after a failed create job): leave
          ``old_workflow_id=None`` (the default).
        - **Regenerating after updating rules**: pass the block's current workflow ID
          (e.g. from ``block.workflow[0].id``).
        - **Regenerating after swapping a workflow**: pass the previous workflow ID
          that was replaced (the one passed to
          [`update_block_workflow`][albert.collections.tasks.TaskCollection.update_block_workflow]).

        Once generation finishes, retrieve the resulting combinations using
        [`get_block_combinations`][albert.collections.tasks.TaskCollection.get_block_combinations].

        !!! warning "Beta Feature!"
            Increased intervals combination support is currently in beta and behind a platform
            feature flag. Please do not use in production or without explicit guidance from
            Albert. You might otherwise have a bad experience. This feature currently falls
            outside of the Albert support contract, but we'd love your feedback!

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            job = client.tasks.generate_block_combinations(
                task_id="TASFOR1",
                block_id="BLK1",
                wait=True,
            )
            job.state
            # 'successful'

            combos = list(client.tasks.get_block_combinations(task_id="TASFOR1", block_id="BLK1"))
            ```

        Parameters
        ----------
        task_id : TaskId
            The Property task ID containing the block (format ``TAS...``), obtained
            from [`create`][albert.collections.tasks.TaskCollection.create],
            [`create_with_combinations`][albert.collections.tasks.TaskCollection.create_with_combinations],
            or [`get_by_id`][albert.collections.tasks.TaskCollection.get_by_id].
        block_id : BlockId
            The block ID whose combinations to generate (format ``BLK...``), obtained
            from ``task.blocks[i].id`` on a fetched task.
        old_workflow_id : WorkflowId, optional
            The ID of the workflow being replaced or re-evaluated (format ``WFL...``).
            Leave None for first-time generation or create retries. Pass the block's
            current workflow ID when re-evaluating rules on an existing block.
        wait : bool, default True
            Whether to wait until background generation reaches a terminal state.
            If False, returns immediately after the generation job is submitted.

        Returns
        -------
        WorkerJob
            The background worker job representing child workflow generation, with
            fields like ``state`` (e.g. ``"successful"``) and ``albert_id``.

        Notes
        -----
        When triggering combination generation across multiple blocks sequentially on the
        same task, pace consecutive calls by at least 10 seconds to avoid backend task lock
        contention during worker job initialization.

        Raises
        ------
        ValueError
            If the block is not found or has no assigned workflow.
        TypeError
            If the task is not a PropertyTask.
        AlbertException
            If the generated combinations exceed the platform cap of 2,000, or if
            ``wait=True`` and the background generation job fails.
        """
        task = self.get_by_id(id=task_id)
        if not isinstance(task, PropertyTask):
            raise TypeError(f"Task {task_id} must be a PropertyTask")

        target_block = next((b for b in task.blocks if b.id == block_id), None)
        if target_block is None:
            raise ValueError(f"Block {block_id} not found on task {task_id}")

        new_workflow_id = self._get_block_current_workflow_id(target_block)
        if not new_workflow_id:
            raise ValueError(f"No workflow found for block {block_id} on task {task_id}")

        # Fetch the full parent workflow with setpoints and intervals
        wfl_response = self.session.get(f"/api/v3/workflows/{new_workflow_id}")
        parent_workflow = Workflow.model_validate(wfl_response.json())

        # Fetch block rules and overrides
        block_rules = self.get_block_rules(task_id=task_id, block_id=block_id)
        start_from = target_block.intervals_start_from or "all"

        # Check if the parent workflow has any intervalized parameters
        has_interval_params = any(
            any(
                bool(getattr(sp, "intervals", None))
                for sp in getattr(g, "parameter_setpoints", [])
            )
            for g in (parent_workflow.parameter_group_setpoints or [])
        )

        s3_url: str | None = None
        if has_interval_params:
            combinations_payload = generate_interval_combinations(
                workflow=parent_workflow,
                rules=block_rules.rules,
                overrides=block_rules.overrides,
                intervals_start_from=start_from,
            )

            if combinations_payload.combinations:
                file_key = (
                    f"intervalcombinations/{task_id}/{block_id}/{uuid.uuid4().hex[:10]}.json"
                )
                sign_payload = {
                    "files": [
                        {
                            "name": file_key,
                            "namespace": "result",
                            "contentType": "application/json",
                        }
                    ]
                }
                sign_resp = self.session.post("/api/v3/files/sign", json=sign_payload)
                signed_url = sign_resp.json()[0]["URL"]

                payload_bytes = combinations_payload.model_dump_json(
                    by_alias=True, exclude_none=True
                ).encode("utf-8")
                s3_resp = requests.put(
                    signed_url,
                    data=payload_bytes,
                    headers={"Content-Type": "application/json"},
                )
                s3_resp.raise_for_status()
                s3_url = file_key

        worker_metadata = WorkerJobMetadata(
            parent_type="TAS",
            albert_id=task_id,
            block_id=block_id,
            new_workflow_id=new_workflow_id,
            old_workflow_id=old_workflow_id,
            s3_url=s3_url,
        )
        worker_req = WorkerJobCreateRequest(
            job_type="createChildWorkflows",
            metadata=worker_metadata,
        )
        job_resp = self.session.post(
            "/api/v3/worker-jobs",
            json=worker_req.model_dump(by_alias=True, mode="json", exclude_none=True),
        )
        resp_data = job_resp.json()
        if isinstance(resp_data, list):
            resp_data = resp_data[0]
        job = WorkerJob.model_validate(resp_data)

        if wait:
            job = poll_worker_job(
                session=self.session,
                job_id=job.albert_id,
                raise_on_failure=True,
                job_description=f"Create child workflows for task {task_id} block {block_id}",
            )

        return job

    @validate_call
    def remove_block(self, *, task_id: TaskId, block_id: BlockId) -> None:
        """Remove a Block from a Property or Batch task.

        Removing a block also removes the results captured against it. To keep the
        block but change its conditions, use [`update_block_workflow`][albert.collections.tasks.TaskCollection.update_block_workflow] instead.

        !!! example
            ```python
            client.tasks.remove_block(task_id="TASFOR1234", block_id="BLK1")
            ```

        Parameters
        ----------
        task_id : TaskId
            The task to remove the block from (e.g. ``"TASFOR1234"``).
        block_id : BlockId
            The block to remove (e.g. ``"BLK1"``).

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

        !!! example
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
        with suppress(NotFoundError):
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

        !!! example
            ```python
            client.tasks.delete(id="TASFOR1")
            ```

        Parameters
        ----------
        id : TaskId
            The task to delete (format ``TAS...``).

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def get_by_id(self, *, id: TaskId) -> BaseTask:
        """Get a single, fully populated task by its ID.

        The returned object is the concrete type matching the task's category:
        ``PropertyTask``, ``BatchTask``, or ``GeneralTask``. For a PropertyTask
        this includes its blocks.

        !!! example
            ```python
            task = client.tasks.get_by_id(id="TASFOR1")
            task.name
            # 'Viscosity screen'
            ```

        Parameters
        ----------
        id : TaskId
            The task to retrieve (format ``TAS...``).

        Returns
        -------
        BaseTask
            The fully populated task.
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
        assigned_to_id: list[str] | None = None,
        location: list[str] | None = None,
        priority: list[str] | None = None,
        status: list[str] | None = None,
        parameter_group: list[str] | None = None,
        created_by: list[str] | None = None,
        project_id: ProjectId | None = None,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        updated_by: str | list[str] | None = None,
        from_updated_at: str | None = None,
        to_updated_at: str | None = None,
        additional_field: str | list[str] | None = None,
        collaborator_pop_up: bool | None = None,
        contains_field: list[str] | None = None,
        contains_text: list[str] | None = None,
        due_date_duration: str | None = None,
        facet_field: str | None = None,
        facet_text: str | None = None,
        has_attachment: str | list[str] | None = None,
        has_notes: str | list[str] | None = None,
        linked_to: list[str] | None = None,
        source_field: str | list[str] | None = None,
        witness_status: list[str] | None = None,
        metadata_filters: dict[str, Any] | None = None,
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

        !!! example
            ```python
            from albert.resources.tasks import TaskCategory
            hits = client.tasks.search(
                category=TaskCategory.PROPERTY, status=["Open"], max_items=20
            )
            for t in hits:
                print(t.id, t.name)
            ```

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
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``).
        project_id : ProjectId, optional
            ID of the parent project for filtering tasks.
        from_created_at : str, optional
            Only include items created on or after this date (ISO 8601).
        to_created_at : str, optional
            Only include items created on or before this date (ISO 8601).
        updated_by : str or list[str], optional
            Filter by user(s) who last updated the tasks. Accepts UserId(s) only
            (e.g. ``"USR4227"``), not display names.
        from_updated_at : str, optional
            Only include items updated on or after this date (ISO 8601).
        to_updated_at : str, optional
            Only include items updated on or before this date (ISO 8601).
        assigned_to_id : list[str], optional
            Filter by assigned user ID(s) (e.g. ``"USR4227"``).
        additional_field : str or list[str], optional
            Request additional columns from the search index.
        collaborator_pop_up : bool, optional
            When True, restrict results for the collaborator pop-up UI.
        contains_field : list[str], optional
            Fields to search inside.
        contains_text : list[str], optional
            Values to search for within ``contains_field``.
        due_date_duration : str, optional
            Filter by due date duration bucket.
        facet_field : str, optional
            Facet field to filter on.
        facet_text : str, optional
            Facet text to search for.
        has_attachment : str or list[str], optional
            Filter tasks by attachment presence.
        has_notes : str or list[str], optional
            Filter tasks by note presence.
        linked_to : list[str], optional
            Filter by linked entity ID(s).
        source_field : str or list[str], optional
            Restrict which fields are returned in the response.
        witness_status : list[str], optional
            Filter by witness status (e.g. ``"witnessed"``).
        metadata_filters : dict[str, Any], optional
            Filter by custom field (metadata) values.
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
            "assignedToId": assigned_to_id,
            "location": location,
            "priority": priority,
            "status": status,
            "parameterGroup": parameter_group,
            "createdBy": created_by,
            "projectId": project_id,
            "fromCreatedAt": from_created_at,
            "toCreatedAt": to_created_at,
            "updatedBy": ensure_list(updated_by),
            "fromUpdatedAt": from_updated_at,
            "toUpdatedAt": to_updated_at,
            "additionalField": ensure_list(additional_field),
            "collaboratorPopUp": collaborator_pop_up,
            "containsField": contains_field,
            "containsText": contains_text,
            "dueDateDuration": due_date_duration,
            "facetField": facet_field,
            "facetText": facet_text,
            "hasAttachment": ensure_list(has_attachment),
            "hasNotes": ensure_list(has_notes),
            "linkedTo": linked_to,
            "sourceField": ensure_list(source_field),
            "witnessStatus": witness_status,
        }

        category_values = ensure_list(category)
        params["category"] = category_values if category_values else None

        deserialize = lambda items: [
            TaskSearchItem(**item)._bind_collection(self) for item in items
        ]

        # TODO(SDK-89): always POST task search once POST SearchTask accepts
        # updatedBy, fromUpdatedAt, and toUpdatedAt.

        if metadata_filters is not None:
            payload: dict[str, Any] = {
                **params,
                "metadataFilters": {"metadata": metadata_filters},
            }
            return AlbertPaginator(
                mode=PaginationMode.OFFSET,
                path=f"{self.base_path}/search",
                session=self.session,
                max_items=max_items,
                deserialize=deserialize,
                method="POST",
                json=payload,
            )

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=deserialize,
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
        assigned_to_id: list[str] | None = None,
        location: list[str] | None = None,
        priority: list[str] | None = None,
        status: list[str] | None = None,
        parameter_group: list[str] | None = None,
        created_by: list[str] | None = None,
        project_id: ProjectId | None = None,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        updated_by: str | list[str] | None = None,
        from_updated_at: str | None = None,
        to_updated_at: str | None = None,
        additional_field: str | list[str] | None = None,
        collaborator_pop_up: bool | None = None,
        contains_field: list[str] | None = None,
        contains_text: list[str] | None = None,
        due_date_duration: str | None = None,
        facet_field: str | None = None,
        facet_text: str | None = None,
        has_attachment: str | list[str] | None = None,
        has_notes: str | list[str] | None = None,
        linked_to: list[str] | None = None,
        source_field: str | list[str] | None = None,
        witness_status: list[str] | None = None,
        metadata_filters: dict[str, Any] | None = None,
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

        !!! example
            ```python
            from albert.resources.tasks import TaskCategory
            for task in client.tasks.get_all(
                category=TaskCategory.PROPERTY, max_items=50
            ):
                print(task.id, task.name)
            ```

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
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``).
        project_id : ProjectId, optional
            ID of the parent project for filtering tasks.
        from_created_at : str, optional
            Only include items created on or after this date (ISO 8601).
        to_created_at : str, optional
            Only include items created on or before this date (ISO 8601).
        updated_by : str or list[str], optional
            Filter by user(s) who last updated the tasks. Accepts UserId(s) only
            (e.g. ``"USR4227"``), not display names.
        from_updated_at : str, optional
            Only include items updated on or after this date (ISO 8601).
        to_updated_at : str, optional
            Only include items updated on or before this date (ISO 8601).
        assigned_to_id : list[str], optional
            Filter by assigned user ID(s) (e.g. ``"USR4227"``).
        additional_field : str or list[str], optional
            Request additional columns from the search index.
        collaborator_pop_up : bool, optional
            When True, restrict results for the collaborator pop-up UI.
        contains_field : list[str], optional
            Fields to search inside.
        contains_text : list[str], optional
            Values to search for within ``contains_field``.
        due_date_duration : str, optional
            Filter by due date duration bucket.
        facet_field : str, optional
            Facet field to filter on.
        facet_text : str, optional
            Facet text to search for.
        has_attachment : str or list[str], optional
            Filter tasks by attachment presence.
        has_notes : str or list[str], optional
            Filter tasks by note presence.
        linked_to : list[str], optional
            Filter by linked entity ID(s).
        source_field : str or list[str], optional
            Restrict which fields are returned in the response.
        witness_status : list[str], optional
            Filter by witness status (e.g. ``"witnessed"``).
        metadata_filters : dict[str, Any], optional
            Filter by custom field (metadata) values.
        order_by : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        sort_by : str, optional
            Attribute to sort tasks by (e.g. ``createdAt``, ``name``).
        max_items : int, optional
            Maximum number of tasks to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[BaseTask]
            Fully populated tasks. Preserves ``has_more`` / ``total`` from the
            underlying search paginator.
        """

        def _hydrate(task: TaskSearchItem) -> BaseTask | None:
            hydrate_id = getattr(task, "id", None)
            if not hydrate_id:
                return None
            try:
                return self.get_by_id(id=hydrate_id)
            except (AlbertHTTPError, RetryError) as e:
                logger.warning(f"Error fetching task '{hydrate_id}': {e}")
                return None

        return MappedPaginator(
            self.search(
                text=text,
                tags=tags,
                task_id=task_id,
                linked_task=linked_task,
                category=category,
                albert_id=albert_id,
                data_template=data_template,
                assigned_to=assigned_to,
                assigned_to_id=assigned_to_id,
                location=location,
                priority=priority,
                status=status,
                parameter_group=parameter_group,
                created_by=created_by,
                project_id=project_id,
                from_created_at=from_created_at,
                to_created_at=to_created_at,
                updated_by=updated_by,
                from_updated_at=from_updated_at,
                to_updated_at=to_updated_at,
                additional_field=additional_field,
                collaborator_pop_up=collaborator_pop_up,
                contains_field=contains_field,
                contains_text=contains_text,
                due_date_duration=due_date_duration,
                facet_field=facet_field,
                facet_text=facet_text,
                has_attachment=has_attachment,
                has_notes=has_notes,
                linked_to=linked_to,
                source_field=source_field,
                witness_status=witness_status,
                metadata_filters=metadata_filters,
                order_by=order_by,
                sort_by=sort_by,
                max_items=max_items,
                offset=offset,
            ),
            _hydrate,
        )

    def update(self, *, task: BaseTask) -> BaseTask:
        """Update an existing task.

        Fetch the task (e.g. with [`get_by_id`][albert.collections.tasks.TaskCollection.get_by_id]), modify the updatable fields,
        then pass it here. Only the fields listed in Notes are applied. To change a
        task's blocks, use [`add_block`][albert.collections.tasks.TaskCollection.add_block], [`remove_block`][albert.collections.tasks.TaskCollection.remove_block], or
        [`update_block_workflow`][albert.collections.tasks.TaskCollection.update_block_workflow] instead.

        !!! example
            ```python
            from albert.resources.tasks import TaskPriority
            task = client.tasks.get_by_id(id="TASFOR1")
            task.priority = TaskPriority.HIGH
            updated = client.tasks.update(task=task)
            ```

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

        !!! example
            ```python
            history = client.tasks.get_history(id="TASFOR1")
            len(history.items)
            # 12
            ```

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
