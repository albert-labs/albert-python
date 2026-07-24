from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass
from albert.core.shared.identifiers import InventoryId, LotId, TaskId
from albert.core.shared.models.patch import PatchPayload
from albert.core.shared.types import (
    MetadataItem,
    SerializeAsEntityLink,
    SerializeAsEntityLinkWithName,
)
from albert.resources._mixins import HydrationMixin
from albert.resources.data_templates import DataTemplate
from albert.resources.locations import Location
from albert.resources.projects import Project
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.teams import Team
from albert.resources.users import User
from albert.resources.workflows import Workflow


class TaskCategory(str, Enum):
    """The kind of lab work a task represents.

    The category determines which concrete task class is used and is set
    automatically by that subclass; you normally do not set it by hand.

    Attributes
    ----------
    PROPERTY : str
        Testing and documenting the properties of products, formulas, or raw
        materials. Corresponds to [`PropertyTask`][albert.resources.tasks.PropertyTask].
    BATCH : str
        Manufacturing a batch of a formulation inside Albert. Corresponds to
        [`BatchTask`][albert.resources.tasks.BatchTask].
    GENERAL : str
        Any lab work that is not a batch or property task (for example
        equipment calibration). Corresponds to [`GeneralTask`][albert.resources.tasks.GeneralTask].
    BATCH_WITH_QC : str
        A batch task that also carries quality-control data. A variant of
        [`BatchTask`][albert.resources.tasks.BatchTask].
    """

    PROPERTY = "Property"
    BATCH = "Batch"
    GENERAL = "General"
    BATCH_WITH_QC = "BatchWithQC"


class BatchSizeUnit(str, Enum):
    """Unit of measure for the size of a batch made in a [`BatchTask`][albert.resources.tasks.BatchTask].

    Attributes
    ----------
    GRAMS : str
        Grams (``"g"``).
    KILOGRAMS : str
        Kilograms (``"Kg"``).
    POUNDS : str
        Pounds (``"lbs"``).
    """

    GRAMS = "g"
    KILOGRAMS = "Kg"
    POUNDS = "lbs"


class TaskSourceType(str, Enum):
    """What kind of thing a task was created from.

    Attributes
    ----------
    TASK : str
        The task was created from another existing task (``"task"``).
    TEMPLATE : str
        The task was created from a task template (``"template"``).
    """

    TASK = "task"
    TEMPLATE = "template"


class TaskSource(BaseAlbertModel):
    """A reference to the task or template a task was created from.

    Recorded in [`sources`][albert.resources.tasks.BaseTask.sources] to trace where a task originated."""

    id: str
    """The ID of the originating task or template."""

    type: TaskSourceType
    """Whether ``id`` points to a task or a template."""


class TaskPriority(str, Enum):
    """How urgent a task is, used for triage and sorting work queues.

    Attributes
    ----------
    HIGH : str
        Highest urgency (``"High"``).
    MEDIUM : str
        Normal urgency (``"Medium"``).
    LOW : str
        Lowest urgency (``"Low"``).
    """

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class HistoryEntity(str, Enum):
    """The kind of entity a task-history query is scoped to.

    Used when requesting the change history of a task (see
    [`get_history`][albert.collections.tasks.TaskCollection.get_history]).

    Attributes
    ----------
    WORKFLOW : str
        Limit history to workflow-related changes (``"workflow"``).
    """

    WORKFLOW = "workflow"


class IntervalId(BaseAlbertModel):
    id: str


class BlockLevelInventoryInformation(BaseAlbertModel):
    id: str
    lot_id: str | None = Field(default=None, alias="lotId")
    inv_lot_unique_id: str | None = Field(default=None, alias="invLotUniqueId")


class BlockState(BaseAlbertModel):
    id: str = Field(description="The ID of the block.")
    expanded: bool | None = Field(default=None, alias="expand")
    intervals: list[IntervalId] | None = Field(
        default=None,
        alias="Interval",
        description="The IDs of the interval (e.g., id: ROW2XROW4)",
    )
    inventory: list[BlockLevelInventoryInformation] | None = Field(default=None, alias="Inventory")


class PageState(BaseAlbertModel):
    left_panel_expanded: bool | None = Field(default=None, alias="leftPanelExpand")
    blocks: list[BlockState] | None = Field(default=None, alias="Block")


class Target(BaseAlbertModel):
    data_column_unique_id: str | None = Field(alias="dataColumnUniqueId", default=None)
    value: str | None = Field(default=None)


class DataTemplateAndTargets(BaseAlbertModel):
    id: str
    targets: list[Target]


class Standard(BaseAlbertModel):
    id: str = Field(frozen=True)
    standard_id: str | None = Field(alias="standardId", frozen=True, default=None)
    name: str | None = Field(default=None, frozen=True)
    standard_organization: str | None = Field(
        alias="standardOrganization", default=None, frozen=True
    )
    standard_organization_id: int | None = Field(
        alias="standardOrganizationId", default=None, frozen=True
    )


class BlockDataTemplateInfo(BaseAlbertModel):
    id: str = Field(alias="id")
    name: str
    full_name: str | None = Field(alias="fullName", default=None)
    standards: Standard | None = Field(default=None, alias="Standards")
    targets: list[Target] | None = Field(default=None, alias="Targets")


class TaskState(str, Enum):
    """Where a task is in its lifecycle, from creation through completion.

    The state generally advances as work progresses: an unclaimed task is
    picked up, started, finished, and eventually closed (or cancelled).

    Attributes
    ----------
    UNCLAIMED : str
        Created but not yet assigned to or claimed by anyone.
    NOT_STARTED : str
        Claimed or assigned, but work has not begun.
    IN_PROGRESS : str
        Work is actively underway.
    COMPLETED : str
        The work has been finished.
    CLOSED : str
        Finalized and no longer active.
    CANCELLED : str
        Abandoned before completion.
    """

    UNCLAIMED = "Unclaimed"
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class TaskInventoryInformation(BaseAlbertModel):
    """Which inventory item (and optionally which lot) a task acts on.

    Every task references one or more inventory items through this model, stored
    on [`inventory_information`][albert.resources.tasks.BaseTask.inventory_information]. What is required depends on the
    task type:

    - [`BatchTask`][albert.resources.tasks.BatchTask]: ``inventory_id`` and ``batch_size`` are required
      (you are making a quantity of that item).
    - [`PropertyTask`][albert.resources.tasks.PropertyTask] and [`GeneralTask`][albert.resources.tasks.GeneralTask]: ``inventory_id`` is
      required and ``lot_id`` is recommended (the specific physical lot tested)."""

    inventory_id: InventoryId = Field(alias="id")
    """The ID of the inventory item used in the task (serialized as ``id``)."""

    lot_id: LotId | None = Field(alias="lotId", default=None)
    """The ID of the specific lot used. Recommended for property and general tasks so results attach to the right physical material."""

    lot_number: str | None = Field(default=None, alias="lotNumber")
    """The human-readable lot number of the item."""

    inv_lot_unique_id: str | None = Field(alias="invLotUniqueId", default=None)
    """A combined inventory-and-lot identifier used internally."""

    batch_size: float | None = Field(alias="batchSize", default=None)
    """The quantity to make of the related inventory item. Required for [`BatchTask`][albert.resources.tasks.BatchTask]; the unit is given by [`batch_size_unit`][albert.resources.tasks.BatchTask.batch_size_unit]."""

    selected_lot: bool | None = Field(alias="selectedLot", exclude=True, frozen=True, default=None)
    """Read-only. Whether this lot is the one selected for the task."""

    barcode_id: str | None = Field(alias="barcodeId", default=None)
    """The barcode identifier of the physical item, if scanned."""

    quantity_used: float | None = Field(alias="quantityUsed", default=None)
    """The amount of the item consumed by the task."""

    selected_lot: bool | None = Field(alias="selectedLot", default=None, exclude=True)
    """Read-only. Whether this lot is the one selected for the task."""


class Block(BaseAlbertModel):
    """A single unit of testing within a property or batch task.

    A block pairs a [`DataTemplate`][albert.resources.data_templates.DataTemplate]
    (the results/data columns to capture) with a
    [`Workflow`][albert.resources.workflows.Workflow] (the parameter conditions
    under which the data is collected). A [`PropertyTask`][albert.resources.tasks.PropertyTask] or
    [`BatchTask`][albert.resources.tasks.BatchTask] can hold multiple blocks. Block IDs look like
    ``"BLK..."``.

    Blocks are normally created and modified through the task collection rather
    than constructed directly; see
    [`add_block`][albert.collections.tasks.TaskCollection.add_block],
    [`update_block_workflow`][albert.collections.tasks.TaskCollection.update_block_workflow], and
    [`remove_block`][albert.collections.tasks.TaskCollection.remove_block]. Measured
    results for a block are recorded through
    [`PropertyDataCollection`][albert.collections.property_data.PropertyDataCollection]."""

    id: str | None = Field(default=None)
    """The block's ID (``"BLK..."``). Assigned by Albert; ``None`` before the block is created."""

    workflow: list[SerializeAsEntityLink[Workflow]] = Field(alias="Workflow", min_length=1)
    """The workflow(s) defining the parameter conditions for the block. At least one is required. Workflows must be independently created and Workflows with a returned ID must be used."""

    data_template: (
        list[BlockDataTemplateInfo]
        | DataTemplateAndTargets
        | list[SerializeAsEntityLink[DataTemplate]]
    ) = Field(alias="Datatemplate", min_length=1, max_length=1)
    """The single data template describing the data columns to capture, and any associated targets."""

    parameter_quantity_used: dict | None = Field(
        alias="parameterQuantityUsed", default=None, exclude=True
    )
    """Read-only internal mapping of parameter quantities consumed by the block."""

    def model_dump(self, *args, **kwargs):
        # Use default serialization with customized field output.
        # Workflow and DataTemplate are both lists of length one, which is annoying to
        data = super().model_dump(*args, **kwargs)
        data["Workflow"] = [data["Workflow"]] if "Workflow" in data else None
        data["Datatemplate"] = [data["Datatemplate"]] if "Datatemplate" in data else None
        return data


class QCTarget(BaseAlbertModel):
    formula_id: str | None = Field(alias="formulaId", default=None)
    target: str | None = Field(default=None)


class QCWorkflowTargets(BaseAlbertModel):
    workflow_id: str | None = Field(alias="id", default=None)
    task_name: str | None = Field(alias="taskName", default=None)
    targets: list[QCTarget] | None = Field(alias="Targets", default=None)


class QCTaskData(BaseAlbertModel):
    data_template_id: str = Field(alias="datatemplateId")
    workflows: list[QCWorkflowTargets] | None = Field(alias="Workflows", default=None)


class TaskEntityType(BaseAlbertModel):
    id: str | None = Field(default=None)
    custom_category: str = Field(default=None, alias="customCategory", exclude=True, frozen=True)


class BaseTask(BaseTaggedResource):
    """Shared fields and behavior for every kind of task.

    A task is a unit of lab work. This base class is not used directly; instead
    pick the concrete type that matches the work:

    - [`PropertyTask`][albert.resources.tasks.PropertyTask]: test and document properties of products,
      formulas, or raw materials. Holds [`Block`][albert.resources.tasks.Block] objects and captures
      measured property data.
    - [`BatchTask`][albert.resources.tasks.BatchTask]: manufacture a batch of a formulation inside Albert.
    - [`GeneralTask`][albert.resources.tasks.GeneralTask]: any other lab work (for example equipment
      calibration) that is neither a batch nor a property task.

    Tasks are managed through
    [`TaskCollection`][albert.collections.tasks.TaskCollection] (``client.tasks``). The
    [`category`][albert.resources.tasks.BaseTask.category] field distinguishes the subclasses and is set
    automatically by each one. Task IDs look like ``"TAS..."``."""

    id: str | None = Field(alias="albertId", default=None)
    """The task's ID (``"TAS..."``, serialized as ``albertId``). Assigned by Albert; ``None`` before the task is created."""

    name: str
    """Human-readable name of the task. Required."""

    category: TaskCategory
    """The task type. Set automatically by the concrete subclass."""

    parent_id: str | None = Field(alias="parentId", default=None)
    """The ID of the parent project this task belongs to."""

    metadata: dict[str, MetadataItem] = Field(alias="Metadata", default_factory=dict)
    """Custom metadata fields keyed by name."""

    sources: list[TaskSource] | None = Field(default_factory=list, alias="Sources")
    """The task(s) or template(s) this task was created from."""

    inventory_information: list[TaskInventoryInformation] = Field(
        alias="Inventories", default=None
    )
    """The inventory item(s) (and optionally lot(s)) the task acts on."""

    location: SerializeAsEntityLink[Location] | None = Field(default=None, alias="Location")
    """Where the task is performed."""

    priority: TaskPriority | None = Field(default=None)
    """The task's urgency."""

    security_class: SecurityClass | None = Field(alias="class", default=None)
    """Access-control classification (serialized as ``class``)."""

    pass_fail: bool | None = Field(alias="passOrFail", default=None)
    """Whether the task is evaluated as pass/fail."""

    notes: str | None = Field(default=None)
    """Free-text notes."""

    start_date: str | None = Field(alias="startDate", default=None)
    """Read-only. Date work started (``YYYY-MM-DD``)."""

    due_date: str | None = Field(alias="dueDate", default=None)
    """Target completion date (``YYYY-MM-DD``)."""

    claimed_date: str | None = Field(alias="claimedDate", default=None)
    """Read-only. Date the task was claimed."""

    completed_date: str | None = Field(alias="completedDate", default=None)
    """Read-only. Date the task was completed."""

    closed_date: str | None = Field(alias="closedDate", default=None)
    """Read-only. Date the task was closed."""

    result: str | None = Field(default=None)
    """Overall result summary for the task."""

    state: TaskState | None = Field(default=None)
    """Current lifecycle state of the task."""

    project: SerializeAsEntityLink[Project] | list[SerializeAsEntityLink[Project]] | None = Field(
        default=None, alias="Project"
    )
    """The project(s) the task is associated with."""

    assigned_to: (
        SerializeAsEntityLinkWithName[User] | SerializeAsEntityLinkWithName[Team] | None
    ) = Field(default=None, alias="AssignedTo")
    """The user or team responsible for the task."""

    page_state: PageState | None = Field(
        alias="PageState",
        default=None,
    )
    """Internal UI layout state for the task page."""

    entity_type: TaskEntityType | None = Field(default=None, alias="EntityType")
    """Internal entity-type classification. See Also --------"""


class PropertyTask(BaseTask):
    """A task that tests and documents the properties of a material.

    Use a property task to measure and record properties of products, formulas,
    or raw materials. A property task holds one or more [`Block`][albert.resources.tasks.Block] objects,
    each pairing a data template (what to capture) with a workflow (the
    conditions). Measured results are recorded per block, interval, and trial
    through [`PropertyDataCollection`][albert.collections.property_data.PropertyDataCollection]
    (``client.property_data``) and roll up to the associated inventory item's
    properties.

    Inherits all shared fields from [`BaseTask`][albert.resources.tasks.BaseTask]. Its [`category`][albert.resources.tasks.PropertyTask.category] is
    always [`PROPERTY`][albert.resources.tasks.TaskCategory.PROPERTY]. Create and manage property tasks with
    [`TaskCollection`][albert.collections.tasks.TaskCollection] (``client.tasks``); add
    blocks with [`add_block`][albert.collections.tasks.TaskCollection.add_block].

    !!! example
        ```python
        from albert.resources.tasks import PropertyTask

        task = PropertyTask(name="Viscosity screen", parent_id="PRO1")
        ```
    Notes
    -----
    All other fields (``location``, ``priority``, ``due_date``, ``state``,
    ``assigned_to``, dates, and so on) are inherited from [`BaseTask`][albert.resources.tasks.BaseTask].
    """

    category: Literal[TaskCategory.PROPERTY] = TaskCategory.PROPERTY
    blocks: list[Block] | None = Field(alias="Blocks", default=None)
    """The blocks (data template + workflow pairs) that define what data the task captures."""

    qc_task: bool | None = Field(alias="qcTask", default=None)
    """Whether this property task is a quality-control task."""

    batch_task_id: str | None = Field(alias="batchTaskId", default=None)
    """The ID of a related batch task, if this task tests material made by one."""

    target: str | None = Field(default=None)
    """A target value or specification associated with the task. Notes ----- All other fields (``location``, ``priority``, ``due_date``, ``state``, ``assigned_to``, dates, and so on) are inherited from [`BaseTask`][albert.resources.tasks.BaseTask]."""


class BatchTask(BaseTask):
    """A task that manufactures a batch of a formulation inside Albert.

    Use a batch task after creating a new formulation to make a physical
    quantity of it. The item to make and the amount are given through
    [`inventory_information`][albert.resources.tasks.BatchTask.inventory_information] (``inventory_id`` and ``batch_size`` are
    required for batch tasks), with the unit set by [`batch_size_unit`][albert.resources.tasks.BatchTask.batch_size_unit].

    Inherits all shared fields from [`BaseTask`][albert.resources.tasks.BaseTask]. Its [`category`][albert.resources.tasks.BatchTask.category] is
    [`BATCH`][albert.resources.tasks.TaskCategory.BATCH] (or [`BATCH_WITH_QC`][albert.resources.tasks.TaskCategory.BATCH_WITH_QC] when
    quality-control data is attached). Create and manage batch tasks with
    [`TaskCollection`][albert.collections.tasks.TaskCollection] (``client.tasks``).

    !!! example
        ```python
        from albert.resources.tasks import BatchTask
        from albert.resources.tasks import TaskInventoryInformation

        task = BatchTask(
            name="Make 500 g of Formula A",
            parent_id="PRO1",
            inventory_information=[
                TaskInventoryInformation(inventory_id="INVEXP1", batch_size=500)
            ],
        )
        ```
    Notes
    -----
    All other fields (``location``, ``priority``, ``due_date``, ``state``,
    ``assigned_to``, dates, and so on) are inherited from [`BaseTask`][albert.resources.tasks.BaseTask].
    """

    category: Literal[TaskCategory.BATCH, TaskCategory.BATCH_WITH_QC] = TaskCategory.BATCH
    batch_size_unit: BatchSizeUnit | None = Field(alias="batchSizeUnit", default=None)
    """The unit of measure for the batch size (grams, kilograms, or pounds)."""

    qc_task: bool | None = Field(alias="qcTask", default=None)
    """Whether this is a quality-control batch task."""

    batch_task_id: str | None = Field(alias="batchTaskId", default=None)
    """The ID of a related batch task."""

    target: str | None = Field(default=None)
    """A target value or specification associated with the task."""

    qc_task_data: list[QCTaskData] | None = Field(alias="QCTaskData", default=None)
    """Quality-control data associated with the batch task. Notes ----- All other fields (``location``, ``priority``, ``due_date``, ``state``, ``assigned_to``, dates, and so on) are inherited from [`BaseTask`][albert.resources.tasks.BaseTask]."""

    workflows: list[SerializeAsEntityLink[Workflow]] | None = Field(alias="Workflow", default=None)
    """Workflow(s) associated with the batch task. These must be independently created and Workflows with a returned ID must be used."""

    blocks: list[Block] | None = Field(alias="Blocks", default=None)
    """Blocks associated with the batch task, when it captures data."""


class GeneralTask(BaseTask):
    """A task for lab work that is neither a batch nor a property task.

    Use a general task for anything that does not fit the other two types, such
    as equipment calibration or maintenance. General tasks do not hold blocks
    and capture no property data.

    Inherits all fields from [`BaseTask`][albert.resources.tasks.BaseTask]; its [`category`][albert.resources.tasks.GeneralTask.category] is always
    [`GENERAL`][albert.resources.tasks.TaskCategory.GENERAL]. Only [`name`][albert.resources.tasks.BaseTask.name] is required.
    Create and manage general tasks with
    [`TaskCollection`][albert.collections.tasks.TaskCollection] (``client.tasks``).

    !!! example
        ```python
        from albert.resources.tasks import GeneralTask

        task = GeneralTask(name="Calibrate rheometer")
        ```
    """

    category: Literal[TaskCategory.GENERAL] = TaskCategory.GENERAL


TaskUnion = Annotated[PropertyTask | BatchTask | GeneralTask, Field(..., discriminator="category")]
TaskAdapter = TypeAdapter(TaskUnion)


class TaskHistoryEvent(BaseAlbertModel):
    state: str
    action: str
    action_at: datetime = Field(alias="actionAt")
    user: SerializeAsEntityLink[User] = Field(alias="User")
    old_value: Any | None = Field(default=None, alias="oldValue")
    new_value: Any | None = Field(default=None, alias="newValue")


class TaskHistory(BaseAlbertModel):
    """The chronological record of changes made to a task.

    Returned by [`get_history`][albert.collections.tasks.TaskCollection.get_history],
    this wraps the individual change events (state changes, field edits, and so
    on) recorded for a task."""

    items: list[TaskHistoryEvent] = Field(alias="Items")
    """The history events, each describing one change (its action, timestamp, acting user, and old/new values)."""


class TaskPatchPayload(PatchPayload):
    """A payload for a PATCH request to update a Task."""

    id: str
    """The id of the Task to be updated."""


class TaskSearchInventory(BaseAlbertModel):
    id: str | None = None
    name: str | None = None
    albert_id_and_name: str | None = Field(default=None, alias="albertIdAndName")


class TaskSearchDataTemplate(BaseAlbertModel):
    id: str | None = None
    name: str


class TaskSearchLot(BaseAlbertModel):
    number: str | None = None
    selected_lot: bool | None = Field(default=None, alias="selectedLot")


class TaskSearchLocation(BaseAlbertModel):
    name: str


class TaskSearchTag(BaseAlbertModel):
    tag_name: str = Field(alias="tagName")


class TaskSearchWorkflow(BaseAlbertModel):
    id: str
    name: str | None = None
    category: str


class TaskSearchItem(BaseAlbertModel, HydrationMixin[BaseTask]):
    """Lightweight representation of a Task returned from unhydrated search()."""

    id: TaskId = Field(alias="albertId")
    name: str
    category: str
    priority: str | None = None
    state: str | None = None
    assigned_to: str | None = Field(default=None, alias="assignedTo")
    assigned_to_user_id: str | None = Field(default=None, alias="assignedToUserId")
    created_by_name: str | None = Field(default=None, alias="createdByName")
    created_at: str | None = Field(default=None, alias="createdAt")
    due_date: str | None = Field(default=None, alias="dueDate")
    completed_date: str | None = Field(default=None, alias="completedDate")
    start_date: str | None = Field(default=None, alias="startDate")
    closed_date: str | None = Field(default=None, alias="closedDate")

    location: list[TaskSearchLocation] | None = None
    inventory: list[TaskSearchInventory] | None = None
    tags: list[TaskSearchTag] | None = None
    lot: list[TaskSearchLot] | None = None
    data_template: list[TaskSearchDataTemplate] | None = Field(default=None, alias="dataTemplate")
    workflow: list[TaskSearchWorkflow] | None = None
    project_id: list[str] | None = Field(default=None, alias="projectId")
    is_qc_task: bool | None = Field(default=None, alias="isQCTask")
    parent_batch_status: str | None = Field(default=None, alias="parentBatchStatus")


# TODO: refactor TaskMetadata models to reuse existing models where possible
class TaskMetadataDataTemplate(BaseAlbertModel):
    """Metadata summary describing a data template on the task."""

    id: str
    name: str | None = None
    full_name: str | None = Field(default=None, alias="fullName")
    property_id: str | None = Field(default=None, alias="propertyId")
    isload_grid: bool | None = Field(default=None, alias="isloadGrid")
    standards: Standard | None = Field(default=None, alias="Standards")


class TaskMetadataIntervalDetail(BaseAlbertModel):
    """Displays a single interval detail for workflow metadata."""

    name: str | None = None
    value: str | None = None
    unit_name: str | None = Field(default=None, alias="unitName")


class TaskMetadataInterval(BaseAlbertModel):
    """Represents an interval attached to a workflow step."""

    interval: str | None = None
    interval_params: str | None = Field(default=None, alias="intervalParams")
    interval_string: str | None = Field(default=None, alias="intervalString")
    interval_details: list[TaskMetadataIntervalDetail] = Field(
        default_factory=list, alias="intervalDetails"
    )
    sequence: int | None = None


class TaskMetadataWorkflow(BaseAlbertModel):
    """Captures workflow identifiers and interval configuration."""

    albert_id: str | None = Field(default=None, alias="albertId")
    name: str | None = Field(default=None)
    intervals: list[TaskMetadataInterval] = Field(default_factory=list, alias="Intervals")


class TaskMetadataValueItem(BaseAlbertModel):
    """Represents a selectable value reference in metadata."""

    id: str
    name: str


class TaskMetadataUnit(BaseAlbertModel):
    """Identifies the unit associated with an interval or parameter."""

    id: str
    name: str


class TaskMetadataIntervalType(BaseAlbertModel):
    """Describes a concrete interval type recorded on the task."""

    id: str
    value: str | None = None
    name: str | None = None
    row_id: str = Field(alias="rowId")
    unit: TaskMetadataUnit | None = Field(default=None, alias="Unit")


class TaskMetadataParameter(BaseAlbertModel):
    """Represents a parameter entry included in workflow metadata."""

    id: str
    name: str
    value: str | TaskMetadataValueItem | None = None
    row_id: str = Field(alias="rowId")
    unit: TaskMetadataUnit | None = Field(default=None, alias="Unit")
    short_name: str | None = Field(default=None, alias="shortName")
    category: str | None = None
    intervals: list[TaskMetadataIntervalType] = Field(default_factory=list, alias="Intervals")


class TaskMetadataParameterGroup(BaseAlbertModel):
    """Groups related parameters for metadata serialization."""

    id: str
    name: str
    prg_sequence: int | None = Field(default=None, alias="prgSequence")
    row_id: str = Field(alias="rowId")
    parameters: list[TaskMetadataParameter] = Field(default_factory=list, alias="Parameters")


class TaskMetadataWorkflowJson(BaseAlbertModel):
    """Holds the serialized workflow JSON metadata payload."""

    albert_id: str | None = Field(default=None, alias="albertId")
    name: str | None = None
    parameter_groups: list[TaskMetadataParameterGroup] = Field(
        default_factory=list, alias="ParameterGroups"
    )


class TaskMetadataBlockdata(BaseAlbertModel):
    """Aggregates block-level metadata for proxy execution."""

    id: str
    datatemplate: list[TaskMetadataDataTemplate] = Field(
        default_factory=list, alias="Datatemplate"
    )
    workflow: list[TaskMetadataWorkflow] = Field(default_factory=list, alias="Workflow")
    workflow_json: TaskMetadataWorkflowJson | dict = Field(
        default_factory=dict, alias="WorkflowJson"
    )


class TaskMetadata(BaseAlbertModel):
    """Top-level metadata describing the task context for scripts."""

    filename: str | None = None
    task_id: str | None = Field(default=None, alias="taskId")
    block_id: str | None = Field(default=None, alias="blockId")
    inventories: list[TaskInventoryInformation] = Field(default_factory=list, alias="Inventories")
    blockdata: TaskMetadataBlockdata | None = Field(default=None, alias="Blockdata")


# Models for CSV tables endpoints
class CsvTableInput(BaseAlbertModel):
    """Payload for invoking the CSV table proxy endpoint."""

    script_s3_url: str = Field(alias="scriptS3URL")
    data_s3_url: str = Field(alias="dataS3URL")
    task_metadata: TaskMetadata = Field(alias="TaskMetadata")


class CsvTableResponseItem(BaseAlbertModel):
    """Single table response emitted by the CSV table proxy."""

    data: list[dict[str, Any]] = Field(alias="Data")


class CsvCurveInput(BaseAlbertModel):
    """Payload sent to the curve CSV proxy runner."""

    script_s3_url: str = Field(alias="scriptS3URL")
    data_s3_url: str = Field(alias="dataS3URL")
    result_s3_url: str = Field(alias="resultS3URL")
    task_metadata: TaskMetadata = Field(alias="TaskMetadata")


class CsvCurveResponse(BaseAlbertModel):
    """Details about the curve CSV file produced by the runner."""

    status: str
    message: str
    e_tag: str | None = Field(default=None, alias="eTag")
    size: float | None = None
    column_headers: dict[str, Any] = Field(alias="columnHeaders")
