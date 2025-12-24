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
from albert.resources.users import User
from albert.resources.workflows import Workflow


class TaskCategory(str, Enum):
    PROPERTY = "Property"
    BATCH = "Batch"
    GENERAL = "General"
    BATCH_WITH_QC = "BatchWithQC"


class BatchSizeUnit(str, Enum):
    GRAMS = "g"
    KILOGRAMS = "Kg"
    POUNDS = "lbs"


class TaskSourceType(str, Enum):
    TASK = "task"
    TEMPLATE = "template"


class TaskSource(BaseAlbertModel):
    id: str
    type: TaskSourceType


class TaskPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class HistoryEntity(str, Enum):
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
    UNCLAIMED = "Unclaimed"
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class TaskInventoryInformation(BaseAlbertModel):
    """Represents the Inventory information needed for a task. For a Batch task, inventory_id and batch_size are required.
    For Property and general tasks, inventory_id and lot_id is recomended is required.

    Attributes
    ----------
    inventory_id : str
        The inventory id of the item to be used in the task.
    lot_id : str, optional
        The lot id of the item to be used in the task. Reccomended for Property and General tasks.
    lot_number : str, optional
        The lot number of the item to be used in the task. Optional.
    batch_size : float, Required for Batch tasks, otherwise optional.
        The batch size to make of the related InventoryItem. Required for Batch tasks.
    selected_lot : bool, read only
        Whether the lot is selected for the task. Default is None.
    """

    inventory_id: InventoryId = Field(alias="id")
    lot_id: LotId | None = Field(alias="lotId", default=None)
    lot_number: str | None = Field(default=None, alias="lotNumber")
    inv_lot_unique_id: str | None = Field(alias="invLotUniqueId", default=None)
    batch_size: float | None = Field(alias="batchSize", default=None)
    selected_lot: bool | None = Field(alias="selectedLot", exclude=True, frozen=True, default=None)
    barcode_id: str | None = Field(alias="barcodeId", default=None)
    quantity_used: float | None = Field(alias="quantityUsed", default=None)
    selected_lot: bool | None = Field(alias="selectedLot", default=None, exclude=True)


class Block(BaseAlbertModel):
    id: str | None = Field(default=None)
    workflow: list[SerializeAsEntityLink[Workflow]] = Field(alias="Workflow", min_length=1)
    data_template: (
        list[BlockDataTemplateInfo]
        | DataTemplateAndTargets
        | list[SerializeAsEntityLink[DataTemplate]]
    ) = Field(alias="Datatemplate", min_length=1, max_length=1)
    parameter_quantity_used: dict | None = Field(
        alias="parameterQuantityUsed", default=None, exclude=True
    )

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
    """Base class for all task types. Use PropertyTask, BatchTask, or GeneralTask for specific task types."""

    id: str | None = Field(alias="albertId", default=None)
    name: str
    category: TaskCategory
    parent_id: str | None = Field(alias="parentId", default=None)
    metadata: dict[str, MetadataItem] = Field(alias="Metadata", default_factory=dict)
    sources: list[TaskSource] | None = Field(default_factory=list, alias="Sources")
    inventory_information: list[TaskInventoryInformation] = Field(
        alias="Inventories", default=None
    )
    location: SerializeAsEntityLink[Location] | None = Field(default=None, alias="Location")
    priority: TaskPriority | None = Field(default=None)
    security_class: SecurityClass | None = Field(alias="class", default=None)
    pass_fail: bool | None = Field(alias="passOrFail", default=None)
    notes: str | None = Field(default=None)
    start_date: str | None = Field(alias="startDate", default=None)
    due_date: str | None = Field(alias="dueDate", default=None)
    claimed_date: str | None = Field(alias="claimedDate", default=None)
    completed_date: str | None = Field(alias="completedDate", default=None)
    closed_date: str | None = Field(alias="closedDate", default=None)
    result: str | None = Field(default=None)
    state: TaskState | None = Field(default=None)
    project: SerializeAsEntityLink[Project] | list[SerializeAsEntityLink[Project]] | None = Field(
        default=None, alias="Project"
    )
    assigned_to: SerializeAsEntityLinkWithName[User] | None = Field(
        default=None, alias="AssignedTo"
    )
    page_state: PageState | None = Field(
        alias="PageState",
        default=None,
    )
    entity_type: TaskEntityType | None = Field(default=None, alias="EntityType")


class PropertyTask(BaseTask):
    """
    Represents a property task.

    This class is used to create and manage property tasks. It includes the base task attributes
    and additional attributes specific to property tasks (e.g., blocks tied to workflows/data templates).

    Attributes
    ----------
    name : str
        The name of the property task.
    inventory_information : list[TaskInventoryInformation]
        Information about the inventory associated with the property task.
    location : SerializeAsEntityLink[Location]
        The location where the property task is performed.
    parent_id : str
        The ID of the parent project.
    blocks : list[Block]
        A list of blocks associated with the property task.
    id : str, optional
        The ID of the property task, by default None.

    metadata : dict[str, MetadataItem], optional
        Metadata associated with the property task, by default an empty dictionary.
    due_date : str, optional
        The due date of the property task. YYYY-MM-DD format, by default None.
    notes : str, optional
        Notes associated with the property task, by default None.
    priority : TaskPriority, optional
        The priority of the property task, by default None.
    assigned_to : SerializeAsEntityLink[User], optional
        The user assigned to the property task, by default None.

    state : TaskState, optional
        The state of the property task, by default None.
    sources : list[TaskSource], optional
        A list of sources associated with the property task, by default an empty list.
    security_class : SecurityClass, optional
        The security class of the property task, by default None.
    start_date : str, read only
        The start date of the property task, by default None.
    claimed_date : str, read only
        The claimed date of the property task, by default None.
    completed_date : str, read only
        The completed date of the property task, by default None.
    closed_date : str, read only
        The closed date of the property task, by default None.
    """

    category: Literal[TaskCategory.PROPERTY] = TaskCategory.PROPERTY
    blocks: list[Block] | None = Field(alias="Blocks", default=None)
    qc_task: bool | None = Field(alias="qcTask", default=None)
    batch_task_id: str | None = Field(alias="batchTaskId", default=None)
    target: str | None = Field(default=None)


class BatchTask(BaseTask):
    """
    Represents a batch task.

    This class is used to create and manage batch tasks. It includes the base task attributes
    and additional attributes specific to batch tasks.

    Attributes
    ----------
    name : str
        The name of the batch task.
    inventory_information : list[TaskInventoryInformation]
        Information about the inventory associated with the batch task.
    location : SerializeAsEntityLink[Location]
        The location where the batch task is performed.
    parent_id : str
        The ID of the parent project.
    id : str, optional
        The ID of the batch task, by default None.

    batch_size_unit : str, optional
        The unit of measurement for the batch size, by default None.
    metadata : dict[str, MetadataItem], optional
        Metadata associated with the batch task, by default an empty dictionary.
    workflows : list[SerializeAsEntityLink[Workflow]], optional
        A list of workflows associated with the batch task, by default None.
    due_date : str, optional
        The due date of the batch task. YYY-MM-DD format, by default None.
    notes : str, optional
        Notes associated with the batch task, by default None.
    priority : TaskPriority, optional
        The priority of the batch task, by default None.
    project : SerializeAsEntityLink[Project] | list[SerializeAsEntityLink[Project]], optional
        The project(s) associated with the batch task, by default None.
    assigned_to : SerializeAsEntityLink[User], optional
        The user assigned to the batch task, by default None.

    state : TaskState, optional
        The state of the batch task, by default None.
    sources : list[TaskSource], optional
        A list of sources associated with the batch task, by default an empty list.
    security_class : SecurityClass, optional
        The security class of the batch task, by default None.
    pass_fail : bool, optional
        Whether the batch task is pass/fail, by default None.
    start_date : str, read only
        The start date of the batch task, by default None.
    claimed_date : str, read only
        The claimed date of the batch task, by default None.
    completed_date : str, read only
        The completed date of the batch task, by default None.
    closed_date : str, read only
        The closed date of the batch task, by default None.
    qc_task : bool, optional
        Whether the batch task is a QC task, by default None.
    batch_task_id : str, optional
        The ID of the batch task, by default None.
    target : str, optional
        The target of the batch task, by default None.
    qc_task_data : list[QCTaskData], optional
        A list of QC task data associated with the batch task, by default None.
    """

    category: Literal[TaskCategory.BATCH, TaskCategory.BATCH_WITH_QC] = TaskCategory.BATCH
    batch_size_unit: BatchSizeUnit | None = Field(alias="batchSizeUnit", default=None)
    qc_task: bool | None = Field(alias="qcTask", default=None)
    batch_task_id: str | None = Field(alias="batchTaskId", default=None)
    target: str | None = Field(default=None)
    target: str | None = Field(default=None)
    qc_task_data: list[QCTaskData] | None = Field(alias="QCTaskData", default=None)
    workflows: list[SerializeAsEntityLink[Workflow]] | None = Field(
        alias="Workflow", default=None
    )  # not sure what QuantityUsed in the API docs means here.


class GeneralTask(BaseTask):
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
    items: list[TaskHistoryEvent] = Field(alias="Items")


class TaskPatchPayload(PatchPayload):
    """A payload for a PATCH request to update a Task.

    Attributes
    ----------
    id:  str
        The id of the Task to be updated.
    """

    id: str


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
    task_metadata: "TaskMetadata" = Field(alias="TaskMetadata")


class CsvTableResponseItem(BaseAlbertModel):
    """Single table response emitted by the CSV table proxy."""

    data: list[dict[str, Any]] = Field(alias="Data")


class CsvCurveInput(BaseAlbertModel):
    """Payload sent to the curve CSV proxy runner."""

    script_s3_url: str = Field(alias="scriptS3URL")
    data_s3_url: str = Field(alias="dataS3URL")
    result_s3_url: str = Field(alias="resultS3URL")
    task_metadata: "TaskMetadata" = Field(alias="TaskMetadata")


class CsvCurveResponse(BaseAlbertModel):
    """Details about the curve CSV file produced by the runner."""

    status: str
    message: str
    e_tag: str | None = Field(default=None, alias="eTag")
    size: float | None = None
    column_headers: dict[str, Any] = Field(alias="columnHeaders")
