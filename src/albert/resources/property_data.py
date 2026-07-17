from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
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
from albert.core.shared.models.base import BaseResource
from albert.core.shared.models.patch import PatchDatum
from albert.core.shared.types import SerializeAsEntityLink
from albert.resources.data_templates import (
    CurveDBMetadata,
    DataTemplate,
    ImportMode,
    StorageKeyReference,
)
from albert.resources.lots import Lot
from albert.resources.units import Unit
from albert.resources.workflows import Workflow

########################## Supporting GET Classes ##########################


class PropertyDataStatus(str, Enum):
    """Outcome status of a property data write operation.

    Reported by the API on create/update responses (for example on
    [`InventoryPropertyDataCreate`][albert.resources.property_data.InventoryPropertyDataCreate]) to indicate whether the values were
    persisted.

    Attributes
    ----------
    SUCCESS : str
        The property data was written successfully.
    FAILURE : str
        The property data write failed. Serialized as ``"Failed"``.
    """

    SUCCESS = "Success"
    FAILURE = "Failed"


class DataEntity(str, Enum):
    """The kind of entity that a piece of property data is attached to.

    Selects how the values are keyed and where they live in the platform.

    Attributes
    ----------
    TASK : str
        Data measured on a task, organized per block, interval combination, and
        trial. Task results roll up to the associated inventory item.
    WORKFLOW : str
        Data keyed to a workflow (a specific set of parameter setpoints).
    INVENTORY : str
        Data stored directly on an inventory item, independent of any task.
    """

    TASK = "task"
    WORKFLOW = "workflow"
    INVENTORY = "inventory"


# TODO: replace with StorageKeyReference in a future release
class PropertyDataStorageKey(BaseAlbertModel):
    """Storage references (preview, thumbnail, original) for an uploaded media file."""

    preview: str | None = Field(default=None)
    thumb: str | None = Field(default=None)
    original: str | None = Field(default=None)


class PropertyData(BaseAlbertModel):
    """A single stored result value together with any rich-media backing data.

    Returned by the API as part of a [`PropertyValue`][albert.resources.property_data.PropertyValue]. For simple numeric or
    text results only ``value`` is populated; for image and curve data columns the
    additional fields carry the uploaded file references and processing metadata."""

    id: PropertyDataId | None = Field(default=None)
    """The Albert ID of this property data record (format ``PTD...``)."""
    value: str | None = Field(default=None)
    """The stored result value. All values are stored as strings in Albert."""
    value_type: str | None = Field(default=None, alias="valueType")
    """The type of the value (e.g. numeric, string, image, curve). Serialized as ``valueType``."""
    storage_key: PropertyDataStorageKey | StorageKeyReference | None = Field(
        default=None, alias="s3Key"
    )
    """Storage references for uploaded media (image previews/thumbnails or curve files). Serialized as ``s3Key``."""
    job: dict[str, Any] | None = Field(default=None)
    """Processing job metadata, used for curve/image ingestion."""
    csv_mapping: dict[str, str] | None = Field(default=None, alias="csvMapping")
    """Mapping from CSV headers to curve result identifiers, for curve data. Serialized as ``csvMapping``."""
    curve_remarks: dict[str, Any] | None = Field(default=None, alias="curveRemarks")
    """Remarks associated with curve data. Serialized as ``curveRemarks``."""
    athena: dict[str, Any] | None = Field(default=None)
    """Backing analytical store metadata for curve data. See Also --------"""


class PropertyValue(BaseAlbertModel):
    """A measured result for one data column, with its value, unit, and metadata.

    Appears inside a [`Trial`][albert.resources.property_data.Trial] (as one of its ``data_columns``) and represents
    the value captured for a single data column of a data template. Both a numeric
    and a string form of the value may be present depending on the column type."""

    id: str | None = Field(default=None)
    """Identifier of the result within the trial."""
    name: str | None = Field(default=None)
    """The data column / result name."""
    sequence: str | None = Field(default=None)
    """Pointer to the specific data (result) column; more unique than a data column ID because a data column can be repeated within a Data Template (analogous to a parameter repeated in a Parameter Group)."""
    calculation: str | None = Field(default=None)
    """Optional calculation expression used in place of a fixed value; may reference other result columns (e.g. ``=((COL3-COL1)/COL2)*100``). The result is computed and shown in the UI."""
    numeric_value: float | None = Field(default=None, alias="valueNumeric")
    """The numeric form of the value. Serialized as ``valueNumeric``."""
    string_value: str | None = Field(default=None, alias="valueString")
    """The string form of the value. Serialized as ``valueString``."""
    value: str | None = Field(default=None)
    """The stored value."""
    unit: SerializeAsEntityLink[Unit] | dict = Field(default_factory=dict, alias="Unit")
    """The unit of measure for the value, as an entity link. Serialized as ``Unit``."""
    property_data: PropertyData | None = Field(default=None, alias="PropertyData")
    """The backing stored value / media record. Serialized as ``PropertyData``."""
    data_column_unique_id: str | None = Field(default=None, alias="dataColumnUniqueId")
    """The unique ID of the data column this result captures. Serialized as ``dataColumnUniqueId``."""
    hidden: bool | None = Field(default=False)
    """Whether the result is hidden. See Also --------"""


class Trial(BaseAlbertModel):
    """One replicate measurement of a given interval combination.

    A trial holds the set of [`PropertyValue`][albert.resources.property_data.PropertyValue] results recorded for one row of
    data under a [`DataInterval`][albert.resources.property_data.DataInterval]. Multiple trials under the same interval are
    repeat measurements of the same parameter setpoints."""

    trial_number: int = Field(alias="trialNo")
    """The trial (row) number. Serialized as ``trialNo``."""
    visible_trial_number: int = Field(default=1, alias="visibleTrialNo")
    """The relative row number shown to users. Serialized as ``visibleTrialNo``."""
    void: bool = Field(default=False)
    """Whether this trial has been voided."""
    back_end_trial_number: str | None = Field(default=None, alias="backEndTrialNo")
    """Internal trial identifier. Serialized as ``backEndTrialNo``."""
    data_columns: list[PropertyValue] = Field(default_factory=list, alias="DataColumns")
    """The results measured in this trial, one per data column. Serialized as ``DataColumns``. See Also --------"""


class DataInterval(BaseAlbertModel):
    """All trials recorded for one interval combination within a block.

    An interval combination is one specific set of parameter setpoints, identified
    by an interval ID such as ``ROW1``, ``ROW1XROW2``, or the literal ``"default"``
    when the block has no intervalized parameters. Build the ID with
    [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id]."""

    interval_combination: str = Field(alias="intervalCombination")
    """The interval ID this data belongs to (e.g. ``"default"``, ``"ROW1"``, ``"ROW1XROW2"``). Serialized as ``intervalCombination``."""
    void: bool = Field(default=False)
    """Whether this interval's data has been voided."""
    trials: list[Trial] = Field(default_factory=list, alias="Trials")
    """The replicate measurements recorded for this interval. Serialized as ``Trials``."""
    name: str | None = Field(default=None)
    """An optional display name for the interval. See Also --------"""


class TaskData(BaseAlbertModel):
    """The measured results captured on a task under a single data template.

    Groups the interval data recorded for one block of a task. Returned as part of
    [`InventoryPropertyData`][albert.resources.property_data.InventoryPropertyData] (under ``task_property_data``), where
    task-measured results roll up to the associated inventory item."""

    task_id: TaskId = Field(alias="id")
    """The task the data was measured on (format ``TAS...``). Serialized as ``id``."""
    task_name: str = Field(alias="name")
    """The task name. Serialized as ``name``."""
    qc_task: bool | None = Field(alias="qcTask", default=None)
    """Whether the task is a QC task. Serialized as ``qcTask``."""
    initial_workflow: SerializeAsEntityLink[Workflow] = Field(alias="InitialWorkflow")
    """The workflow at the start of the task. Serialized as ``InitialWorkflow``."""
    finial_workflow: SerializeAsEntityLink[Workflow] = Field(alias="FinalWorkflow")
    """The workflow at task completion. Serialized as ``FinalWorkflow``."""
    data_template: SerializeAsEntityLink[DataTemplate] = Field(alias="Datatemplate")
    """The data template whose columns were measured (format ``DAT...``). Serialized as ``Datatemplate``."""
    data: list[DataInterval] = Field(default_factory=list, alias="Data")
    """The interval data recorded, one entry per interval combination. Serialized as ``Data``. See Also --------"""


class CustomInventoryDataColumn(BaseAlbertModel):
    """A single custom (non-task) property value stored on an inventory item."""

    data_column_id: DataColumnId = Field(alias="id")
    data_column_name: str = Field(alias="name")
    property_data: PropertyValue = Field(alias="PropertyData")
    unit: SerializeAsEntityLink[Unit] | None | dict = Field(alias="Unit", default_factory=dict)


class CustomData(BaseAlbertModel):
    """A property value stored directly on an inventory item, not from a task.

    Returned inside [`InventoryPropertyData`][albert.resources.property_data.InventoryPropertyData] under ``custom_property_data``.
    Represents a value entered against an inventory item independently of any task
    measurement (for example a supplier-stated value), optionally tied to a lot."""

    lot: SerializeAsEntityLink[Lot] | None | dict = Field(alias="Lot", default_factory=dict)
    """The lot the value applies to, if any. Serialized as ``Lot``."""
    data_column: CustomInventoryDataColumn = Field(alias="DataColumn")
    """The data column and its stored value. Serialized as ``DataColumn``. See Also --------"""


class PropertyDataInventoryInformation(BaseAlbertModel):
    """The inventory item and lot a task's property data was measured against."""

    inventory_id: str | None = Field(alias="id", default=None)
    lot_id: str | None = Field(alias="lotId", default=None)


################# Returned from GET /api/v3/propertydata ##################


class CheckPropertyData(BaseResource):
    """Result of checking whether property data exists for a task/block/interval.

    Returned by
    [`check_for_task_data`][albert.collections.property_data.PropertyDataCollection.check_for_task_data]
    and
    [`check_block_interval_for_data`][albert.collections.property_data.PropertyDataCollection.check_block_interval_for_data]
    to report whether values have already been recorded for a given location."""

    block_id: str | None = Field(default=None, alias="blockId")
    """The block checked (format ``BLK...``). Serialized as ``blockId``."""
    interval_id: str | None = Field(default=None, alias="interval")
    """The interval combination checked. Serialized as ``interval``."""
    inventory_id: str | None = Field(default=None, alias="inventoryId")
    """The inventory item checked (format ``INV...``). Serialized as ``inventoryId``."""
    lot_id: str | None = Field(default=None, alias="lotId")
    """The lot checked, if any. Serialized as ``lotId``."""
    data_exists: bool | None = Field(default=None, alias="dataExist")
    """Whether property data exists at the checked location. Serialized as ``dataExist``."""
    message: str | None = Field(default=None)
    """A human-readable message describing the result."""


class InventoryPropertyData(BaseResource):
    """All property data associated with one inventory item.

    Returned by
    [`get_properties_on_inventory`][albert.collections.property_data.PropertyDataCollection.get_properties_on_inventory].
    Separates results that rolled up from tasks from custom values entered directly
    on the item."""

    inventory_id: str = Field(alias="inventoryId")
    """The inventory item (format ``INV...``). Serialized as ``inventoryId``."""
    inventory_name: str | None = Field(default=None, alias="inventoryName")
    """The inventory item name. Serialized as ``inventoryName``."""
    task_property_data: list[TaskData] = Field(default_factory=list, alias="Task")
    """Results measured on tasks that roll up to this item. Serialized as ``Task``."""
    custom_property_data: list[CustomData] = Field(default_factory=list, alias="NoTask")
    """Values entered directly on the item, independent of any task. Serialized as ``NoTask``. See Also --------"""


class TaskPropertyData(BaseResource):
    """The property data recorded on a task, for one block and data template.

    Returned by
    [`get_task_block_properties`][albert.collections.property_data.PropertyDataCollection.get_task_block_properties]
    and
    [`get_all_task_properties`][albert.collections.property_data.PropertyDataCollection.get_all_task_properties].
    Carries the interval/trial data along with the task's workflows and the
    inventory item the results apply to."""

    entity: Literal[DataEntity.TASK] = DataEntity.TASK
    """Always [`TASK`][albert.resources.property_data.DataEntity.TASK]."""
    parent_id: str = Field(..., alias="parentId")
    """Governs the ACL model: associates the property data with a controlling parent (e.g. a task or inventory item). Serialized as ``parentId``."""
    task_id: str | None = Field(default=None, alias="id")
    """The task (format ``TAS...``). Serialized as ``id``."""
    inventory: PropertyDataInventoryInformation | None = Field(default=None, alias="Inventory")
    """The inventory item and lot the data applies to. Serialized as ``Inventory``."""
    category: DataEntity | None = Field(default=None)
    """The data entity category."""
    initial_workflow: SerializeAsEntityLink[Workflow] | None = Field(
        default=None, alias="InitialWorkflow"
    )
    """The workflow at the start of the task. Serialized as ``InitialWorkflow``."""
    finial_workflow: SerializeAsEntityLink[Workflow] | None = Field(
        default=None, alias="FinalWorkflow"
    )
    """The workflow at task completion. Serialized as ``FinalWorkflow``."""
    data_template: SerializeAsEntityLink[DataTemplate] | None = Field(
        default=None, alias="DataTemplate"
    )
    """The data template whose columns were measured (format ``DAT...``). Serialized as ``DataTemplate``."""
    data: list[DataInterval] = Field(default_factory=list, alias="Data")
    """The interval data recorded, one entry per interval combination. Serialized as ``Data``."""
    block_id: str | None = Field(alias="blockId", default=None)
    """The block the data belongs to (format ``BLK...``). Serialized as ``blockId``. See Also --------"""


class BulkPropertyDataColumn(BaseAlbertModel):
    """All row values for a single data column of a block, in row order.

    A simple, tabular representation of one column's data used for bulk loading.
    Collected into a [`BulkPropertyData`][albert.resources.property_data.BulkPropertyData] (one entry per column) and consumed by
    [`bulk_load_task_properties`][albert.collections.property_data.PropertyDataCollection.bulk_load_task_properties]."""

    data_column_name: str = Field(
        default=None, description="The name of the data column (case sensitive)."
    )
    data_series: list[str] = Field(
        default_factory=list,
        description="The values, in order of row number, for the data column.",
    )


class BulkPropertyData(BaseAlbertModel):
    """A block's data as a set of columns, for bulk loading property values.

    A simple tabular structure: one [`BulkPropertyDataColumn`][albert.resources.property_data.BulkPropertyDataColumn] per data column,
    each holding that column's values in row order. Construct it directly, or from a
    [`DataFrame`][albert.resources.property_data.pandas.DataFrame] with [`from_dataframe`][albert.resources.property_data.BulkPropertyData.from_dataframe], then pass it to
    [`bulk_load_task_properties`][albert.collections.property_data.PropertyDataCollection.bulk_load_task_properties].

    !!! example
        ```python
        import pandas as pd
        from albert.resources.property_data import (
            BulkPropertyData,
            BulkPropertyDataColumn,
        )

        # Construct directly from columns
        bulk = BulkPropertyData(
            columns=[
                BulkPropertyDataColumn(
                    data_column_name="Viscosity", data_series=["1.1", "1.2"]
                ),
            ]
        )

        # Or build from a DataFrame (values are coerced to strings)
        bulk = BulkPropertyData.from_dataframe(pd.DataFrame({"Viscosity": [1.1, 1.2]}))
        ```"""

    columns: list[BulkPropertyDataColumn] = Field(
        default_factory=list,
        description="The columns of data in the block's data column.",
    )

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> BulkPropertyData:
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
    """A single value wrapper for a task data column result."""

    value: str | None = Field(default=None)


class ImagePropertyValue(BaseAlbertModel):
    """Image file input for an image-type data column.

    Pass as the ``value`` of a [`TaskPropertyCreate`][albert.resources.property_data.TaskPropertyCreate] when the target data
    column stores an image. The file is uploaded when the property is created.

    !!! example
        ```python
        from albert.resources.property_data import ImagePropertyValue

        image = ImagePropertyValue(file_path="results/sample.png")
        ```"""

    file_path: str | Path
    """Local path to the image file to upload. See Also --------"""


class CurvePropertyValue(BaseAlbertModel):
    """Curve (CSV) file input for a curve-type data column.

    Pass as the ``value`` of a [`TaskPropertyCreate`][albert.resources.property_data.TaskPropertyCreate] when the target data
    column stores curve data. The CSV is uploaded and ingested when the property is
    created.

    !!! example
        ```python
        from albert.resources.property_data import CurvePropertyValue

        curve = CurvePropertyValue(file_path="results/dsc_curve.csv")
        ```"""

    file_path: str | Path
    """Local path to the CSV file containing curve data."""
    mode: ImportMode = ImportMode.CSV
    """Import mode for the curve data. Defaults to ``ImportMode.CSV``."""
    field_mapping: dict[str, str] | None = None
    """Optional mapping from CSV headers to curve result identifiers. See Also --------"""


class ImagePropertyValuePayload(BaseAlbertModel):
    """Internal upload payload for an image property value (file name + storage key)."""

    file_name: str = Field(alias="fileName")
    s3_key: StorageKeyReference = Field(alias="s3Key")


class CurvePropertyValuePayload(BaseAlbertModel):
    """Internal upload payload for a curve property value (file, storage key, job, mapping)."""

    file_name: str = Field(alias="fileName")
    s3_key: StorageKeyReference = Field(alias="s3Key")
    job_id: str = Field(alias="jobId")
    csv_mapping: dict[str, str] = Field(alias="csvMapping")
    athena: CurveDBMetadata


class TaskDataColumn(BaseAlbertModel):
    """A reference to a data column of a task's data template.

    Identifies which data column a value targets. Used inside
    [`TaskPropertyCreate`][albert.resources.property_data.TaskPropertyCreate] to say which column of a block a value belongs to;
    the identifiers are typically read off an existing block returned by
    [`get_task_block_properties`][albert.collections.property_data.PropertyDataCollection.get_task_block_properties]."""

    data_column_id: DataColumnId = Field(alias="id")
    """The data column (format ``DAC...``). Serialized as ``id``."""
    column_sequence: str | None = Field(default=None, alias="columnId")
    """The column's sequence identifier within the block. Serialized as ``columnId``. See Also --------"""


class TaskDataColumnValue(TaskDataColumn):
    """A task data column reference paired with its value."""

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
    """A trial's worth of task data column values for writing to a task."""

    trial_number: int | None = Field(alias="trialNo", default=None)
    data_columns: list[TaskDataColumnValue] = Field(alias="DataColumns", default_factory=list)


class InventoryDataColumn(BaseAlbertModel):
    """A data column and value to store on an inventory item.

    The input unit for adding or updating a property directly on an inventory item
    via
    [`add_properties_to_inventory`][albert.collections.property_data.PropertyDataCollection.add_properties_to_inventory]
    and
    [`update_property_on_inventory`][albert.collections.property_data.PropertyDataCollection.update_property_on_inventory].

    !!! example
        ```python
        from albert.resources.property_data import InventoryDataColumn

        prop = InventoryDataColumn(data_column_id="DAC1", value="1.2")
        ```"""

    data_column_id: DataColumnId | None = Field(alias="id", default=None)
    """The data column to write to (format ``DAC...``). Serialized as ``id``."""
    value: str | None = Field(default=None)
    """The value to store. See Also --------"""


########################## Task Property POST Classes ##########################


class TaskPropertyCreate(BaseResource):
    """Input model for writing one measured value to a task.

    Targets a specific data column + interval combination + trial on a task's block,
    with a required link to the block's data template, and carries the value to
    store. Pass a list of these to
    [`add_properties_to_task`][albert.collections.property_data.PropertyDataCollection.add_properties_to_task]
    or
    [`update_or_create_task_properties`][albert.collections.property_data.PropertyDataCollection.update_or_create_task_properties].

    Use [`get_interval_id`][albert.resources.workflows.Workflow.get_interval_id] to build the
    ``interval_combination`` from parameter setpoints. For image data columns pass an
    [`ImagePropertyValue`][albert.resources.property_data.ImagePropertyValue] as ``value``; for curve data columns pass a
    [`CurvePropertyValue`][albert.resources.property_data.CurvePropertyValue]; numeric values are coerced to strings.

    !!! example
        ```python
        from albert.resources.property_data import TaskPropertyCreate, TaskDataColumn

        # Derive the data column and template from the existing block
        block = client.property_data.get_task_block_properties(
            inventory_id="INVA1", task_id="TASFOR1", block_id="BLK1"
        )
        column = block.data[0].trials[0].data_columns[0]
        new_value = TaskPropertyCreate(
            interval_combination="default",
            data_column=TaskDataColumn(
                data_column_id=column.id, column_sequence=column.sequence
            ),
            value="33.3",
            data_template=block.data_template,
        )
        ```
    Notes
    -----
    - Use ``Workflow.get_interval_id(parameter_values={"name1": "value1", ...})`` to
      find the correct interval given the parameter names and setpoints.
    - Leave ``trial_number`` blank to create a new row/trial; create new trials one at
      a time.
    - ``visible_trial_number`` can set the relative row number, allowing you to pass
      multiple rows of data at once.

    See Also
    --------
    TaskDataColumn : Identifies the data column a value targets.
    ImagePropertyValue : Value input for image data columns.
    CurvePropertyValue : Value input for curve data columns.
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
        alias="DataColumns", description="The data column associated with the task property."
    )
    value: str | int | float | ImagePropertyValue | CurvePropertyValue | None = Field(
        default=None,
        description=(
            "The value of the task property. Use ImagePropertyValue for image data columns or "
            "CurvePropertyValue for curve data columns. Numeric values are coerced to strings."
        ),
    )
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

    @field_validator("value", mode="before")
    @classmethod
    def coerce_numeric_value(cls, v):
        if isinstance(v, bool):
            raise ValueError("Boolean values are not supported for TaskPropertyCreate.value.")
        if isinstance(v, int | float):
            return str(v)
        return v

    @model_validator(mode="after")
    def set_visible_trial_number(self) -> TaskPropertyCreate:
        if self.visible_trial_number is None:
            if self.trial_number is not None:
                self.visible_trial_number = self.trial_number
            else:
                self.visible_trial_number = "1"
        return self


########################## Inventory Custom Property POST Class ##########################


class PropertyDataPatchDatum(PatchDatum):
    """A single patch operation for updating a task property value.

    Extends [`PatchDatum`][albert.core.shared.models.patch.PatchDatum] with the ID of the
    property (or data column) to change. Pass a list of these to
    [`update_property_on_task`][albert.collections.property_data.PropertyDataCollection.update_property_on_task].

    !!! example
        ```python
        from albert.resources.property_data import PropertyDataPatchDatum
        from albert.core.shared.models.patch import PatchOperation

        patch = PropertyDataPatchDatum(
            operation=PatchOperation.UPDATE,
            id="PTD1",
            attribute="value",
            new_value="1.5",
            old_value="1.2",
        )
        ```"""

    property_column_id: DataColumnId | PropertyDataId = Field(alias="id")
    """The property data record (``PTD...``) or data column (``DAC...``) to patch. Serialized as ``id``."""


class InventoryPropertyDataCreate(BaseResource):
    """Request/response body for writing custom property data to an inventory item.

    Built internally by
    [`add_properties_to_inventory`][albert.collections.property_data.PropertyDataCollection.add_properties_to_inventory]
    (one data column per request) and returned to report the registered value. Most
    users pass [`InventoryDataColumn`][albert.resources.property_data.InventoryDataColumn] objects to that method rather than
    constructing this directly."""

    entity: Literal[DataEntity.INVENTORY] = Field(default=DataEntity.INVENTORY)
    """Always [`INVENTORY`][albert.resources.property_data.DataEntity.INVENTORY]."""
    inventory_id: InventoryId = Field(alias="parentId")
    """The inventory item (format ``INV...``). Serialized as ``parentId``."""
    data_columns: list[InventoryDataColumn] = Field(
        default_factory=list, max_length=1, alias="DataColumn"
    )
    """The property to write. At most one column per request. Serialized as ``DataColumn``."""
    status: PropertyDataStatus | None = Field(default=None)
    """The outcome status reported by the API. See Also --------"""


####### Property Data Search #######


class WorkflowItem(BaseAlbertModel):
    """One parameter setpoint captured in a property data search result's workflow."""

    name: str
    id: ParameterId
    value: str | None = Field(default=None)
    parameter_group_id: ParameterGroupId | None = Field(default=None, alias="parameterGroupId")
    value_numeric: float | None = Field(default=None, alias="valueNumeric")
    unit_name: str | None = Field(default=None, alias="unitName")
    unit_id: UnitId | None = Field(default=None, alias="unitId")


class PropertyDataResult(BaseAlbertModel):
    """The single measured result carried by a [`PropertyDataSearchItem`][albert.resources.property_data.PropertyDataSearchItem]."""

    value_numeric: float | None = Field(None, alias="valueNumeric")
    name: str
    # This is not the actual PTD id it is the DAC this result is capturing
    data_column_id: DataColumnId = Field(..., alias="id")
    value: str | None = None
    trial: Any = None
    value_string: str | None = Field(None, alias="valueString")


class PropertyDataSearchItem(BaseAlbertModel):
    """One property data record returned by a property data search.

    Yielded by
    [`search`][albert.collections.property_data.PropertyDataCollection.search]. Flattens
    a single measured result together with the workflow setpoints, data template, and
    the task/inventory/project it belongs to."""

    id: PropertyDataId
    """The property data record ID (format ``PTD...``)."""
    category: str
    """The data entity category (e.g. task or inventory)."""
    workflow: list[WorkflowItem]
    """The parameter setpoints in effect for this result."""
    result: PropertyDataResult
    """The measured result value."""
    data_template_id: DataTemplateId = Field(..., alias="dataTemplateId")
    """The data template (format ``DAT...``). Serialized as ``dataTemplateId``."""
    workflow_name: str | None = Field(default=None, alias="workflowName")
    """The workflow name. Serialized as ``workflowName``."""
    parent_id: TaskId | InventoryId = Field(..., alias="parentId")
    """The entity the data was recorded on. Serialized as ``parentId``."""
    data_template_name: str = Field(..., alias="dataTemplateName")
    """The data template name. Serialized as ``dataTemplateName``."""
    created_by: str = Field(..., alias="createdBy")
    """The user who created the record. Serialized as ``createdBy``."""
    inventory_id: InventoryId = Field(..., alias="inventoryId")
    """The inventory item the result applies to (format ``INV...``). Serialized as ``inventoryId``."""
    project_id: ProjectId = Field(..., alias="projectId")
    """The project the data belongs to (format ``PRO...``). Serialized as ``projectId``."""
    workflow_id: WorkflowId = Field(..., alias="workflowId")
    """The workflow (format ``WFL...``). Serialized as ``workflowId``."""
    task_id: TaskId | None = Field(default=None, alias="taskId")
    """The task the result was measured on, if any (format ``TAS...``). Serialized as ``taskId``. See Also --------"""


ReturnScope = Literal["task", "block", "none"]
