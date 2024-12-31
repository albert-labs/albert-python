from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from albert.resources.base import BaseAlbertModel, MetadataItem, SecurityClass
from albert.resources.data_templates import DataTemplate
from albert.resources.locations import Location
from albert.resources.projects import Project
from albert.resources.serialization import EntityLinkConvertible, SerializeAsEntityLink
from albert.resources.tagged_base import BaseTaggedEntity
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


class Target(BaseAlbertModel):
    data_column_unique_id: str | None = Field(alias="dataColumnUniqueId", default=None)
    value: str | None = Field(default=None)


class DataTemplateAndTargets(BaseAlbertModel):
    id: str
    targets: list[Target]


class TaskState(str, Enum):
    UNCLAIMED = "Unclaimed"
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"


class InventoryInformation(BaseAlbertModel):
    """Represents the Inventory information needed for a task. For a Batch task, inventory_id and batch_size are required.
    For Property and general tasks, inventory_id and lot_id is recomended is required.

    Attributes
    ----------
    inventory_id : str
        The inventory id of the item to be used in the task.
    lot_id : str, optional
        The lot id of the item to be used in the task. Reccomended for Property and General tasks.
    batch_size : float, optional
        The batch size to make of the related InventoryItem. Required for Batch tasks.
    selected_lot : bool, read only
        Whether the lot is selected for the task. Default is None.
    """

    inventory_id: str = Field(alias="id")
    lot_id: str | None = Field(alias="lotId", default=None)
    inv_lot_unique_id: str | None = Field(alias="invLotUniqueId", default=None)
    batch_size: float | None = Field(alias="batchSize", default=None)
    selected_lot: bool | None = Field(alias="selectedLot", exclude=True, frozen=True, default=None)
    barcode_id: str | None = Field(alias="barcodeId", default=None)
    quantity_used: float | None = Field(alias="quantityUsed", default=None)
    selected_lot: bool | None = Field(alias="selectedLot", default=None)


class Block(BaseAlbertModel):
    id: str | None = Field(default=None)
    workflow: list[SerializeAsEntityLink[Workflow]] = Field(alias="Workflow", min_length=1)
    data_template: list[SerializeAsEntityLink[DataTemplate]] | DataTemplateAndTargets = Field(
        alias="Datatemplate", min_length=1, max_length=1
    )
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


class BaseTask(BaseTaggedEntity, EntityLinkConvertible):
    """Base class for all task types. Use PropertyTask, BatchTask, or GeneralTask for specific task types."""

    id: str | None = Field(alias="albertId", default=None)
    name: str
    category: TaskCategory
    parent_id: str | None = Field(alias="parentId", default=None)
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    sources: list[TaskSource] | None = Field(default_factory=list, alias="Sources")
    inventory_information: list[InventoryInformation] = Field(alias="Inventories", default=None)
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
    assigned_to: SerializeAsEntityLink[User] | None = Field(default=None, alias="AssignedTo")


class PropertyTask(BaseTask):
    category: Literal[TaskCategory.PROPERTY] = TaskCategory.PROPERTY
    blocks: list[Block] | None = Field(alias="Blocks", default=None)
    qc_task: bool | None = Field(alias="qcTask", default=None)
    batch_task_id: str | None = Field(alias="batchTaskId", default=None)
    target: str | None = Field(default=None)


class BatchTask(BaseTask):
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
