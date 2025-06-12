from enum import Enum
from typing import Literal

import pandas as pd
from pydantic import Field, field_validator, model_validator

from albert.resources.base import BaseAlbertModel, BaseResource
from albert.resources.data_templates import DataTemplate
from albert.resources.identifiers import (
    DataColumnId,
    DataTemplateId,
    InventoryId,
    ParameterGroupId,
    ParameterId,
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
from albert.utils.patch_types import PatchDatum

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
    value: str | None = Field(default=None)
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
    interval_id: str | None = Field(default=None, alias="interval")
    inventory_id: str | None = Field(default=None, alias="inventoryId")
    lot_id: str | None = Field(default=None, alias="lotId")
    data_exists: bool | None = Field(default=None, alias="dataExist")
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


class BulkPropertyDataColumn(BaseAlbertModel):
    """A Simple Data Structure representing all the rows of data in a block's data column."""

    data_column_name: str = Field(
        default=None, description="The name of the data column (case sensitive)."
    )
    data_series: list[str] = Field(
        default_factory=list,
        description="The values, in order of row number, for the data column.",
    )


class BulkPropertyData(BaseAlbertModel):
    """A Simple Data Structure representing all the columns of data in a block's data column."""

    columns: list[BulkPropertyDataColumn] = Field(
        default_factory=list,
        description="The columns of data in the block's data column.",
    )

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "BulkPropertyData":
        """
        Converts a DataFrame to a BulkPropertyData object.

        Parameters
        ----------
        df : pd.DataFrame
            The DataFrame to convert.

        Returns
        -------
        BulkPropertyData
            The BulkPropertyData object that represents the data in the DataFrame.
        """
        # Convert all the values to strings, since all albert values are string typed in Albert
        df = df.fillna("").astype(str)
        columns = []
        for column in df.columns:
            data_column = BulkPropertyDataColumn(
                data_column_name=column, data_series=df[column].tolist()
            )
            columns.append(data_column)
        return BulkPropertyData(columns=columns)


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
    """
    Represents a task property to be created.

    This class is used to create new task properties. Users can use the `Workflowe.get_interval_id`
    method to find the correct interval given the names and setpoints of the parameters.


    Notes
    -----
    - Users can use `Workflow.get_interval_id(parameter_values={"name1":"value1", "name2":"value2"})`
      to find the correct interval given the names and setpoints of the parameters.
    - Leave `trial_number` blank to create a new row/trial.
    - `visible_trial_number` can be used to set the relative row number, allowing you to pass multiple rows of data at once.
    """

    entity: Literal[DataEntity.TASK] = Field(
        default=DataEntity.TASK,
        description="The entity type, which is always `DataEntity.TASK` for task properties.",
    )
    interval_combination: str = Field(
        alias="intervalCombination",
        examples=["default", "ROW4XROW2", "ROW2"],
        default="default",
        description="The interval combination, which can be found using `Workflow.get_interval_id`.",
    )
    data_column: TaskDataColumn = Field(
        ..., alias="DataColumns", description="The data column associated with the task property."
    )
    value: str | None = Field(default=None, description="The value of the task property.")
    trial_number: int = Field(
        alias="trialNo",
        default=None,
        description="The trial number/ row number. Leave blank to create a new row/trial.",
    )
    data_template: SerializeAsEntityLink[DataTemplate] = Field(
        ...,
        alias="DataTemplate",
        description="The data template associated with the task property.",
    )
    visible_trial_number: int | None = Field(
        alias="visibleTrialNo",
        default=None,
        description="Can be used to set the relative row number, allowing you to pass multiple rows of data at once.",
    )

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
    property_column_id: DataColumnId | PropertyDataId = Field(alias="id")


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
    id: ParameterId
    value: str | None = Field(default=None)
    parameter_group_id: ParameterGroupId | None = Field(default=None, alias="parameterGroupId")
    value_numeric: float | None = Field(default=None, alias="valueNumeric")
    unit_name: str | None = Field(default=None, alias="unitName")
    unit_id: UnitId | None = Field(default=None, alias="unitId")


class PropertyDataResult(BaseAlbertModel):
    value_numeric: float | None = Field(None, alias="valueNumeric")
    name: str
    # This is not the actual PTD id it is the DAC this result is capturing
    data_column_id: DataColumnId = Field(..., alias="id")
    value: str | None = None
    trial: str
    value_string: str | None = Field(None, alias="valueString")


class PropertyDataSearchItem(BaseAlbertModel):
    id: PropertyDataId
    category: str
    workflow: list[WorkflowItem]
    result: PropertyDataResult
    data_template_id: DataTemplateId = Field(..., alias="dataTemplateId")
    workflow_name: str | None = Field(default=None, alias="workflowName")
    parent_id: TaskId | InventoryId = Field(..., alias="parentId")
    data_template_name: str = Field(..., alias="dataTemplateName")
    created_by: str = Field(..., alias="createdBy")
    inventory_id: InventoryId = Field(..., alias="inventoryId")
    project_id: ProjectId = Field(..., alias="projectId")
    workflow_id: WorkflowId = Field(..., alias="workflowId")
    task_id: TaskId | None = Field(default=None, alias="taskId")
