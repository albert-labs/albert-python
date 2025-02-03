from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from albert.resources.base import BaseAlbertModel, BaseResource
from albert.resources.data_templates import DataTemplate
from albert.resources.identifiers import (
    DataColumnId,
    DataTemplateId,
    InventoryId,
    ParameterGroupId,
    ProjectId,
    PropertyDataId,
    TaskId,
    UnitId,
    WorkflowId,
)
from albert.resources.lots import Lot
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.units import Unit
from albert.resources.workflows import Workflow
from albert.utils.patches import PatchDatum

########################## Supporting GET Classes ##########################


class PropertyDataStatus(str, Enum):
    """The status of a resource"""

    SUCCESS = "Success"
    FAILURE = "Failed"


class DataEntity(str, Enum):
    TASK = "task"
    WORKFLOW = "workflow"
    INVENTORY = "inventory"


class PropertyData(BaseAlbertModel):
    id: PropertyDataId | None = Field(default=None)
    value: str | None = Field(default=None)


class PropertyValue(BaseAlbertModel):
    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    sequence: str | None = Field(default=None)
    calculation: str | None = Field(default=None)
    numeric_value: float | None = Field(default=None, alias="valueNumeric")
    string_value: str | None = Field(default=None, alias="valueString")
    unit: SerializeAsEntityLink[Unit] | dict = Field(default_factory=dict, alias="Unit")
    property_data: PropertyData | None = Field(default=None, alias="PropertyData")
    data_column_unique_id: str | None = Field(default=None, alias="dataColumnUniqueId")
    hidden: bool | None = Field(default=False)


class Trial(BaseAlbertModel):
    trial_number: int = Field(alias="trialNo")
    visible_trial_number: int = Field(default=1, alias="visibleTrialNo")
    void: bool = Field(default=False)
    data_columns: list[PropertyValue] = Field(default_factory=list, alias="DataColumns")


class DataInterval(BaseAlbertModel):
    interval_combination: str = Field(alias="intervalCombination")
    void: bool = Field(default=False)
    trials: list[Trial] = Field(default_factory=list, alias="Trials")
    name: str | None = Field(default=None)


class TaskData(BaseAlbertModel):
    task_id: TaskId = Field(alias="id")
    task_name: str = Field(alias="name")
    qc_task: bool | None = Field(alias="qcTask", default=None)
    initial_workflow: SerializeAsEntityLink[Workflow] = Field(alias="InitialWorkflow")
    finial_workflow: SerializeAsEntityLink[Workflow] = Field(alias="FinalWorkflow")
    data_template: SerializeAsEntityLink[DataTemplate] = Field(alias="Datatemplate")
    data: list[DataInterval] = Field(default_factory=list, alias="Data")


class CustomInventoryDataColumn(BaseAlbertModel):
    data_column_id: DataColumnId = Field(alias="id")
    data_column_name: str = Field(alias="name")
    property_data: PropertyValue = Field(alias="PropertyData")
    unit: SerializeAsEntityLink[Unit] | None | dict = Field(alias="Unit", default_factory=dict)


class CustomData(BaseAlbertModel):
    lot: SerializeAsEntityLink[Lot] | None | dict = Field(alias="Lot", default_factory=dict)
    data_column: CustomInventoryDataColumn = Field(alias="DataColumn")


class InventoryInformation(BaseAlbertModel):
    inventory_id: str | None = Field(alias="id", default=None)
    lot_id: str | None = Field(alias="lotId", default=None)


################# Returned from GET /api/v3/propertydata ##################


class CheckPropertyData(BaseResource):
    block_id: str | None = Field(default=None, alias="blockId")
    interval_id: str | None = Field(default=None, alias="intervalId")
    inventory_id: str | None = Field(default=None, alias="inventoryId")
    lot_id: str | None = Field(default=None, alias="lotId")
    data_exists: bool | None = Field(default=None, alias="dataExists")
    message: str | None = Field(default=None)


class InventoryPropertyData(BaseResource):
    inventory_id: str = Field(alias="inventoryId")
    inventory_name: str | None = Field(default=None, alias="inventoryName")
    task_property_data: list[TaskData] = Field(default_factory=list, alias="Task")
    custom_property_data: list[CustomData] = Field(default_factory=list, alias="NoTask")


class TaskPropertyData(BaseResource):
    entity: Literal[DataEntity.TASK] = DataEntity.TASK
    parent_id: str = Field(..., alias="parentId")
    task_id: str | None = Field(default=None, alias="id")
    inventory: InventoryInformation | None = Field(default=None, alias="Inventory")
    category: DataEntity | None = Field(default=None)
    initial_workflow: SerializeAsEntityLink[Workflow] | None = Field(
        default=None, alias="InitialWorkflow"
    )
    finial_workflow: SerializeAsEntityLink[Workflow] | None = Field(
        default=None, alias="FinalWorkflow"
    )
    data_template: SerializeAsEntityLink[DataTemplate] | None = Field(
        default=None, alias="DataTemplate"
    )
    data: list[DataInterval] = Field(alias="Data", frozen=True, exclude=True)
    block_id: str | None = Field(alias="blockId", default=None)


########################## Supporting POST Classes ##########################


class TaskPropertyValue(BaseAlbertModel):
    value: str | None = Field(default=None)


class TaskDataColumn(BaseAlbertModel):
    data_column_id: DataColumnId = Field(alias="id")
    column_sequence: str | None = Field(default=None, alias="columnId")


class TaskDataColumnValue(TaskDataColumn):
    value: TaskPropertyValue = Field(alias="Value")

    @field_validator("value", mode="before")
    def set_string_value(cls, v):
        """
        Converts a string to TaskPropertyValue if the input is a string.
        """
        if isinstance(v, str):
            return TaskPropertyValue(value=v)
        return v


class TaskTrialData(BaseAlbertModel):
    trial_number: int | None = Field(alias="trialNo", default=None)
    data_columns: list[TaskDataColumnValue] = Field(alias="DataColumns", default_factory=list)


class InventoryDataColumn(BaseAlbertModel):
    data_column_id: DataColumnId | None = Field(alias="id", default=None)
    value: str | None = Field(default=None)


########################## Task Property POST Classes ##########################


class TaskPropertyCreate(BaseResource):
    entity: Literal[DataEntity.TASK] = Field(default=DataEntity.TASK)
    interval_combination: str = Field(
        alias="intervalCombination",
        examples=["default", "ROW4XROW2", "ROW2"],
        default="default",
    )
    data_column: TaskDataColumn = Field(..., alias="DataColumns")
    value: str | None = Field(default=None)
    visible_trial_number: int | None = Field(alias="visibleTrialNo", default=None)
    trial_number: int = Field(alias="trialNo", default=None)
    data_template: SerializeAsEntityLink[DataTemplate] = Field(..., alias="DataTemplate")

    @model_validator(mode="after")
    def set_visible_trial_number(self) -> "TaskPropertyCreate":
        if self.visible_trial_number is None:
            if self.trial_number is not None:
                self.visible_trial_number = self.trial_number
            else:
                self.visible_trial_number = "1"
        return self


########################## Inventory Custom Property POST Class ##########################


class PropertyDataPatchDatum(PatchDatum):
    property_column_id: DataColumnId = Field(alias="id")


class InventoryPropertyDataCreate(BaseResource):
    entity: Literal[DataEntity.INVENTORY] = Field(default=DataEntity.INVENTORY)
    inventory_id: InventoryId = Field(alias="parentId")
    data_columns: list[InventoryDataColumn] = Field(
        default_factory=list, max_length=1, alias="DataColumn"
    )
    status: PropertyDataStatus | None = Field(default=None)


####### Property Data Search #######


class WorkflowItem(BaseAlbertModel):
    name: str
    id: WorkflowId
    value: str
    parameter_group_id: ParameterGroupId = Field(..., alias="parameterGroupId")
    value_numeric: float | None = Field(None, alias="valueNumeric")
    unit_name: str | None = Field(None, alias="unitName")
    unit_id: UnitId | None = Field(None, alias="unitId")


class PropertyDataResult(BaseAlbertModel):
    value_numeric: float | None = Field(None, alias="valueNumeric")
    name: str
    # This is not the actual PTD id it is the DAC this result is capturing
    data_column_id: DataColumnId = Field(..., alias="id")
    value: str | None = None
    trial: str
    value_string: str | None = Field(None, alias="valueString")


class PropertyDataSearchItem(BaseAlbertModel):
    workflow: list[WorkflowItem]
    data_template_id: DataTemplateId = Field(..., alias="dataTemplateId")
    workflow_name: str | None = Field(None, alias="workflowName")
    parent_id: TaskId = Field(..., alias="parentId")
    data_template_name: str = Field(..., alias="dataTemplateName")
    result: PropertyDataResult
    created_by: str = Field(..., alias="createdBy")
    inventory_id: InventoryId = Field(..., alias="inventoryId")
    id: PropertyDataId
    category: str
    project_id: ProjectId = Field(..., alias="projectId")
    workflow_id: WorkflowId = Field(..., alias="workflowId")
    task_id: TaskId = Field(..., alias="taskId")
