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
    :class:`InventoryPropertyDataCreate`) to indicate whether the values were
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

    Returned by the API as part of a :class:`PropertyValue`. For simple numeric or
    text results only ``value`` is populated; for image and curve data columns the
    additional fields carry the uploaded file references and processing metadata.

    Attributes
    ----------
    id : PropertyDataId | None
        The Albert ID of this property data record (format ``PTD...``).
    value : str | None
        The stored result value. All values are stored as strings in Albert.
    value_type : str | None
        The type of the value (e.g. numeric, string, image, curve). Serialized as
        ``valueType``.
    storage_key : PropertyDataStorageKey | StorageKeyReference | None
        Storage references for uploaded media (image previews/thumbnails or curve
        files). Serialized as ``s3Key``.
    job : dict[str, Any] | None
        Processing job metadata, used for curve/image ingestion.
    csv_mapping : dict[str, str] | None
        Mapping from CSV headers to curve result identifiers, for curve data.
        Serialized as ``csvMapping``.
    curve_remarks : dict[str, Any] | None
        Remarks associated with curve data. Serialized as ``curveRemarks``.
    athena : dict[str, Any] | None
        Backing analytical store metadata for curve data.

    See Also
    --------
    PropertyValue : Wraps this record with the human-readable result fields.
    """

    id: PropertyDataId | None = Field(default=None)
    value: str | None = Field(default=None)
    value_type: str | None = Field(default=None, alias="valueType")
    storage_key: PropertyDataStorageKey | StorageKeyReference | None = Field(
        default=None, alias="s3Key"
    )
    job: dict[str, Any] | None = Field(default=None)
    csv_mapping: dict[str, str] | None = Field(default=None, alias="csvMapping")
    curve_remarks: dict[str, Any] | None = Field(default=None, alias="curveRemarks")
    athena: dict[str, Any] | None = Field(default=None)


class PropertyValue(BaseAlbertModel):
    """A measured result for one data column, with its value, unit, and metadata.

    Appears inside a :class:`Trial` (as one of its ``data_columns``) and represents
    the value captured for a single data column of a data template. Both a numeric
    and a string form of the value may be present depending on the column type.

    Attributes
    ----------
    id : str | None
        Identifier of the result within the trial.
    name : str | None
        The data column / result name.
    sequence : str | None
        Pointer to the specific data (result) column; more unique than a data column
        ID because a data column can be repeated within a Data Template (analogous to a
        parameter repeated in a Parameter Group).
    calculation : str | None
        Optional calculation expression used in place of a fixed value; may reference
        other result columns (e.g. ``=((COL3-COL1)/COL2)*100``). The result is computed
        and shown in the UI.
    numeric_value : float | None
        The numeric form of the value. Serialized as ``valueNumeric``.
    string_value : str | None
        The string form of the value. Serialized as ``valueString``.
    value : str | None
        The stored value.
    unit : SerializeAsEntityLink[Unit] | dict
        The unit of measure for the value, as an entity link. Serialized as ``Unit``.
    property_data : PropertyData | None
        The backing stored value / media record. Serialized as ``PropertyData``.
    data_column_unique_id : str | None
        The unique ID of the data column this result captures. Serialized as
        ``dataColumnUniqueId``.
    hidden : bool | None
        Whether the result is hidden.

    See Also
    --------
    Trial : Groups the property values measured in one replicate.
    PropertyData : The backing stored value record.
    """

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
    """One replicate measurement of a given interval combination.

    A trial holds the set of :class:`PropertyValue` results recorded for one row of
    data under a :class:`DataInterval`. Multiple trials under the same interval are
    repeat measurements of the same parameter setpoints.

    Attributes
    ----------
    trial_number : int
        The trial (row) number. Serialized as ``trialNo``.
    visible_trial_number : int
        The relative row number shown to users. Serialized as ``visibleTrialNo``.
    void : bool
        Whether this trial has been voided.
    back_end_trial_number : str | None
        Internal trial identifier. Serialized as ``backEndTrialNo``.
    data_columns : list[PropertyValue]
        The results measured in this trial, one per data column. Serialized as
        ``DataColumns``.

    See Also
    --------
    DataInterval : Groups the trials recorded for one interval combination.
    """

    trial_number: int = Field(alias="trialNo")
    visible_trial_number: int = Field(default=1, alias="visibleTrialNo")
    void: bool = Field(default=False)
    back_end_trial_number: str | None = Field(default=None, alias="backEndTrialNo")
    data_columns: list[PropertyValue] = Field(default_factory=list, alias="DataColumns")


class DataInterval(BaseAlbertModel):
    """All trials recorded for one interval combination within a block.

    An interval combination is one specific set of parameter setpoints, identified
    by an interval ID such as ``ROW1``, ``ROW1XROW2``, or the literal ``"default"``
    when the block has no intervalized parameters. Build the ID with
    :meth:`~albert.resources.workflows.Workflow.get_interval_id`.

    Attributes
    ----------
    interval_combination : str
        The interval ID this data belongs to (e.g. ``"default"``, ``"ROW1"``,
        ``"ROW1XROW2"``). Serialized as ``intervalCombination``.
    void : bool
        Whether this interval's data has been voided.
    trials : list[Trial]
        The replicate measurements recorded for this interval. Serialized as
        ``Trials``.
    name : str | None
        An optional display name for the interval.

    See Also
    --------
    Trial : One replicate measurement within this interval.
    TaskData : Groups the intervals measured for a task under one data template.
    """

    interval_combination: str = Field(alias="intervalCombination")
    void: bool = Field(default=False)
    trials: list[Trial] = Field(default_factory=list, alias="Trials")
    name: str | None = Field(default=None)


class TaskData(BaseAlbertModel):
    """The measured results captured on a task under a single data template.

    Groups the interval data recorded for one block of a task. Returned as part of
    :class:`InventoryPropertyData` (under ``task_property_data``), where
    task-measured results roll up to the associated inventory item.

    Attributes
    ----------
    task_id : TaskId
        The task the data was measured on (format ``TAS...``). Serialized as ``id``.
    task_name : str
        The task name. Serialized as ``name``.
    qc_task : bool | None
        Whether the task is a QC task. Serialized as ``qcTask``.
    initial_workflow : SerializeAsEntityLink[Workflow]
        The workflow at the start of the task. Serialized as ``InitialWorkflow``.
    finial_workflow : SerializeAsEntityLink[Workflow]
        The workflow at task completion. Serialized as ``FinalWorkflow``.
    data_template : SerializeAsEntityLink[DataTemplate]
        The data template whose columns were measured (format ``DAT...``).
        Serialized as ``Datatemplate``.
    data : list[DataInterval]
        The interval data recorded, one entry per interval combination. Serialized
        as ``Data``.

    See Also
    --------
    InventoryPropertyData : Container returning both task and non-task property data.
    DataInterval : One interval combination's trials within this data.
    """

    task_id: TaskId = Field(alias="id")
    task_name: str = Field(alias="name")
    qc_task: bool | None = Field(alias="qcTask", default=None)
    initial_workflow: SerializeAsEntityLink[Workflow] = Field(alias="InitialWorkflow")
    finial_workflow: SerializeAsEntityLink[Workflow] = Field(alias="FinalWorkflow")
    data_template: SerializeAsEntityLink[DataTemplate] = Field(alias="Datatemplate")
    data: list[DataInterval] = Field(default_factory=list, alias="Data")


class CustomInventoryDataColumn(BaseAlbertModel):
    """A single custom (non-task) property value stored on an inventory item."""

    data_column_id: DataColumnId = Field(alias="id")
    data_column_name: str = Field(alias="name")
    property_data: PropertyValue = Field(alias="PropertyData")
    unit: SerializeAsEntityLink[Unit] | None | dict = Field(alias="Unit", default_factory=dict)


class CustomData(BaseAlbertModel):
    """A property value stored directly on an inventory item, not from a task.

    Returned inside :class:`InventoryPropertyData` under ``custom_property_data``.
    Represents a value entered against an inventory item independently of any task
    measurement (for example a supplier-stated value), optionally tied to a lot.

    Attributes
    ----------
    lot : SerializeAsEntityLink[Lot] | None | dict
        The lot the value applies to, if any. Serialized as ``Lot``.
    data_column : CustomInventoryDataColumn
        The data column and its stored value. Serialized as ``DataColumn``.

    See Also
    --------
    InventoryPropertyData : Container returning both task and non-task property data.
    """

    lot: SerializeAsEntityLink[Lot] | None | dict = Field(alias="Lot", default_factory=dict)
    data_column: CustomInventoryDataColumn = Field(alias="DataColumn")


class PropertyDataInventoryInformation(BaseAlbertModel):
    """The inventory item and lot a task's property data was measured against."""

    inventory_id: str | None = Field(alias="id", default=None)
    lot_id: str | None = Field(alias="lotId", default=None)


################# Returned from GET /api/v3/propertydata ##################


class CheckPropertyData(BaseResource):
    """Result of checking whether property data exists for a task/block/interval.

    Returned by
    :meth:`~albert.collections.property_data.PropertyDataCollection.check_for_task_data`
    and
    :meth:`~albert.collections.property_data.PropertyDataCollection.check_block_interval_for_data`
    to report whether values have already been recorded for a given location.

    Attributes
    ----------
    block_id : str | None
        The block checked (format ``BLK...``). Serialized as ``blockId``.
    interval_id : str | None
        The interval combination checked. Serialized as ``interval``.
    inventory_id : str | None
        The inventory item checked (format ``INV...``). Serialized as ``inventoryId``.
    lot_id : str | None
        The lot checked, if any. Serialized as ``lotId``.
    data_exists : bool | None
        Whether property data exists at the checked location. Serialized as
        ``dataExist``.
    message : str | None
        A human-readable message describing the result.
    """

    block_id: str | None = Field(default=None, alias="blockId")
    interval_id: str | None = Field(default=None, alias="interval")
    inventory_id: str | None = Field(default=None, alias="inventoryId")
    lot_id: str | None = Field(default=None, alias="lotId")
    data_exists: bool | None = Field(default=None, alias="dataExist")
    message: str | None = Field(default=None)


class InventoryPropertyData(BaseResource):
    """All property data associated with one inventory item.

    Returned by
    :meth:`~albert.collections.property_data.PropertyDataCollection.get_properties_on_inventory`.
    Separates results that rolled up from tasks from custom values entered directly
    on the item.

    Attributes
    ----------
    inventory_id : str
        The inventory item (format ``INV...``). Serialized as ``inventoryId``.
    inventory_name : str | None
        The inventory item name. Serialized as ``inventoryName``.
    task_property_data : list[TaskData]
        Results measured on tasks that roll up to this item. Serialized as ``Task``.
    custom_property_data : list[CustomData]
        Values entered directly on the item, independent of any task. Serialized as
        ``NoTask``.

    See Also
    --------
    TaskData : Task-measured results that roll up to the item.
    CustomData : Non-task values stored on the item.
    """

    inventory_id: str = Field(alias="inventoryId")
    inventory_name: str | None = Field(default=None, alias="inventoryName")
    task_property_data: list[TaskData] = Field(default_factory=list, alias="Task")
    custom_property_data: list[CustomData] = Field(default_factory=list, alias="NoTask")


class TaskPropertyData(BaseResource):
    """The property data recorded on a task, for one block and data template.

    Returned by
    :meth:`~albert.collections.property_data.PropertyDataCollection.get_task_block_properties`
    and
    :meth:`~albert.collections.property_data.PropertyDataCollection.get_all_task_properties`.
    Carries the interval/trial data along with the task's workflows and the
    inventory item the results apply to.

    Attributes
    ----------
    entity : Literal[DataEntity.TASK]
        Always :attr:`DataEntity.TASK`.
    parent_id : str
        Governs the ACL model: associates the property data with a controlling parent
        (e.g. a task or inventory item). Serialized as ``parentId``.
    task_id : str | None
        The task (format ``TAS...``). Serialized as ``id``.
    inventory : PropertyDataInventoryInformation | None
        The inventory item and lot the data applies to. Serialized as ``Inventory``.
    category : DataEntity | None
        The data entity category.
    initial_workflow : SerializeAsEntityLink[Workflow] | None
        The workflow at the start of the task. Serialized as ``InitialWorkflow``.
    finial_workflow : SerializeAsEntityLink[Workflow] | None
        The workflow at task completion. Serialized as ``FinalWorkflow``.
    data_template : SerializeAsEntityLink[DataTemplate] | None
        The data template whose columns were measured (format ``DAT...``).
        Serialized as ``DataTemplate``.
    data : list[DataInterval]
        The interval data recorded, one entry per interval combination. Serialized
        as ``Data``.
    block_id : str | None
        The block the data belongs to (format ``BLK...``). Serialized as ``blockId``.

    See Also
    --------
    DataInterval : One interval combination's trials within this data.
    TaskPropertyCreate : Input model for writing new task property values.
    """

    entity: Literal[DataEntity.TASK] = DataEntity.TASK
    parent_id: str = Field(..., alias="parentId")
    task_id: str | None = Field(default=None, alias="id")
    inventory: PropertyDataInventoryInformation | None = Field(default=None, alias="Inventory")
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
    data: list[DataInterval] = Field(default_factory=list, alias="Data")
    block_id: str | None = Field(alias="blockId", default=None)


class BulkPropertyDataColumn(BaseAlbertModel):
    """All row values for a single data column of a block, in row order.

    A simple, tabular representation of one column's data used for bulk loading.
    Collected into a :class:`BulkPropertyData` (one entry per column) and consumed by
    :meth:`~albert.collections.property_data.PropertyDataCollection.bulk_load_task_properties`.

    Attributes
    ----------
    data_column_name : str
        The name of the data column (case sensitive).
    data_series : list[str]
        The values, in order of row number, for the data column.

    See Also
    --------
    BulkPropertyData : Groups the columns of a block for bulk loading.
    """

    data_column_name: str = Field(
        default=None, description="The name of the data column (case sensitive)."
    )
    data_series: list[str] = Field(
        default_factory=list,
        description="The values, in order of row number, for the data column.",
    )


class BulkPropertyData(BaseAlbertModel):
    """A block's data as a set of columns, for bulk loading property values.

    A simple tabular structure: one :class:`BulkPropertyDataColumn` per data column,
    each holding that column's values in row order. Construct it directly, or from a
    :class:`pandas.DataFrame` with :meth:`from_dataframe`, then pass it to
    :meth:`~albert.collections.property_data.PropertyDataCollection.bulk_load_task_properties`.

    Attributes
    ----------
    columns : list[BulkPropertyDataColumn]
        The columns of data in the block.

    See Also
    --------
    BulkPropertyDataColumn : One column's row values.

    Examples
    --------
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
        ```
    """

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

    Pass as the ``value`` of a :class:`TaskPropertyCreate` when the target data
    column stores an image. The file is uploaded when the property is created.

    Attributes
    ----------
    file_path : str | Path
        Local path to the image file to upload.

    See Also
    --------
    TaskPropertyCreate : Uses this as its ``value`` for image data columns.
    CurvePropertyValue : The equivalent input for curve data columns.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.property_data import ImagePropertyValue

        image = ImagePropertyValue(file_path="results/sample.png")
        ```
    """

    file_path: str | Path


class CurvePropertyValue(BaseAlbertModel):
    """Curve (CSV) file input for a curve-type data column.

    Pass as the ``value`` of a :class:`TaskPropertyCreate` when the target data
    column stores curve data. The CSV is uploaded and ingested when the property is
    created.

    Attributes
    ----------
    file_path : str | Path
        Local path to the CSV file containing curve data.
    mode : ImportMode
        Import mode for the curve data. Defaults to ``ImportMode.CSV``.
    field_mapping : dict[str, str] | None
        Optional mapping from CSV headers to curve result identifiers.

    See Also
    --------
    TaskPropertyCreate : Uses this as its ``value`` for curve data columns.
    ImagePropertyValue : The equivalent input for image data columns.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.property_data import CurvePropertyValue

        curve = CurvePropertyValue(file_path="results/dsc_curve.csv")
        ```
    """

    file_path: str | Path
    mode: ImportMode = ImportMode.CSV
    field_mapping: dict[str, str] | None = None


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
    :class:`TaskPropertyCreate` to say which column of a block a value belongs to;
    the identifiers are typically read off an existing block returned by
    :meth:`~albert.collections.property_data.PropertyDataCollection.get_task_block_properties`.

    Attributes
    ----------
    data_column_id : DataColumnId
        The data column (format ``DAC...``). Serialized as ``id``.
    column_sequence : str | None
        The column's sequence identifier within the block. Serialized as ``columnId``.

    See Also
    --------
    TaskPropertyCreate : Uses this to target a value at a specific data column.
    """

    data_column_id: DataColumnId = Field(alias="id")
    column_sequence: str | None = Field(default=None, alias="columnId")


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
    :meth:`~albert.collections.property_data.PropertyDataCollection.add_properties_to_inventory`
    and
    :meth:`~albert.collections.property_data.PropertyDataCollection.update_property_on_inventory`.

    Attributes
    ----------
    data_column_id : DataColumnId | None
        The data column to write to (format ``DAC...``). Serialized as ``id``.
    value : str | None
        The value to store.

    See Also
    --------
    InventoryPropertyDataCreate : Wraps these columns for the create request.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.property_data import InventoryDataColumn

        prop = InventoryDataColumn(data_column_id="DAC1", value="1.2")
        ```
    """

    data_column_id: DataColumnId | None = Field(alias="id", default=None)
    value: str | None = Field(default=None)


########################## Task Property POST Classes ##########################


class TaskPropertyCreate(BaseResource):
    """Input model for writing one measured value to a task.

    Targets a specific data column + interval combination + trial on a task's block,
    with a required link to the block's data template, and carries the value to
    store. Pass a list of these to
    :meth:`~albert.collections.property_data.PropertyDataCollection.add_properties_to_task`
    or
    :meth:`~albert.collections.property_data.PropertyDataCollection.update_or_create_task_properties`.

    Use :meth:`~albert.resources.workflows.Workflow.get_interval_id` to build the
    ``interval_combination`` from parameter setpoints. For image data columns pass an
    :class:`ImagePropertyValue` as ``value``; for curve data columns pass a
    :class:`CurvePropertyValue`; numeric values are coerced to strings.

    Attributes
    ----------
    entity : Literal[DataEntity.TASK]
        The entity type, always :attr:`DataEntity.TASK`.
    interval_combination : str
        The interval combination to write to (e.g. ``"default"``, ``"ROW2"``,
        ``"ROW4XROW2"``), found with
        :meth:`~albert.resources.workflows.Workflow.get_interval_id`. Serialized as
        ``intervalCombination``.
    data_column : TaskDataColumn
        The data column to write to. Serialized as ``DataColumns``.
    value : str | int | float | ImagePropertyValue | CurvePropertyValue | None
        The value to store. Use :class:`ImagePropertyValue` for image data columns or
        :class:`CurvePropertyValue` for curve data columns; numeric values are coerced
        to strings.
    trial_number : int
        The trial (row) number. Supply an existing trial number to write to it; leave
        unset to create a new trial. Serialized as ``trialNo``.
    data_template : SerializeAsEntityLink[DataTemplate]
        The data template the value belongs to (format ``DAT...``). Required.
        Serialized as ``DataTemplate``.
    visible_trial_number : int | None
        The relative row number, letting you pass multiple rows of data at once.
        Defaults from ``trial_number`` when unset. Serialized as ``visibleTrialNo``.

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

    Examples
    --------
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

    Extends :class:`~albert.core.shared.models.patch.PatchDatum` with the ID of the
    property (or data column) to change. Pass a list of these to
    :meth:`~albert.collections.property_data.PropertyDataCollection.update_property_on_task`.

    Attributes
    ----------
    property_column_id : DataColumnId | PropertyDataId
        The property data record (``PTD...``) or data column (``DAC...``) to patch.
        Serialized as ``id``.
    operation : str
        The patch operation to perform (see
        :class:`~albert.core.shared.models.patch.PatchOperation`).
    attribute : str
        The attribute to change (e.g. ``"value"``).
    new_value : Any | None
        The new value. Serialized as ``newValue``.
    old_value : Any | None
        The previous value. Serialized as ``oldValue``.

    Examples
    --------
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
        ```
    """

    property_column_id: DataColumnId | PropertyDataId = Field(alias="id")


class InventoryPropertyDataCreate(BaseResource):
    """Request/response body for writing custom property data to an inventory item.

    Built internally by
    :meth:`~albert.collections.property_data.PropertyDataCollection.add_properties_to_inventory`
    (one data column per request) and returned to report the registered value. Most
    users pass :class:`InventoryDataColumn` objects to that method rather than
    constructing this directly.

    Attributes
    ----------
    entity : Literal[DataEntity.INVENTORY]
        Always :attr:`DataEntity.INVENTORY`.
    inventory_id : InventoryId
        The inventory item (format ``INV...``). Serialized as ``parentId``.
    data_columns : list[InventoryDataColumn]
        The property to write. At most one column per request. Serialized as
        ``DataColumn``.
    status : PropertyDataStatus | None
        The outcome status reported by the API.

    See Also
    --------
    InventoryDataColumn : The data column + value to write.
    """

    entity: Literal[DataEntity.INVENTORY] = Field(default=DataEntity.INVENTORY)
    inventory_id: InventoryId = Field(alias="parentId")
    data_columns: list[InventoryDataColumn] = Field(
        default_factory=list, max_length=1, alias="DataColumn"
    )
    status: PropertyDataStatus | None = Field(default=None)


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
    """The single measured result carried by a :class:`PropertyDataSearchItem`."""

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
    :meth:`~albert.collections.property_data.PropertyDataCollection.search`. Flattens
    a single measured result together with the workflow setpoints, data template, and
    the task/inventory/project it belongs to.

    Attributes
    ----------
    id : PropertyDataId
        The property data record ID (format ``PTD...``).
    category : str
        The data entity category (e.g. task or inventory).
    workflow : list[WorkflowItem]
        The parameter setpoints in effect for this result.
    result : PropertyDataResult
        The measured result value.
    data_template_id : DataTemplateId
        The data template (format ``DAT...``). Serialized as ``dataTemplateId``.
    workflow_name : str | None
        The workflow name. Serialized as ``workflowName``.
    parent_id : TaskId | InventoryId
        The entity the data was recorded on. Serialized as ``parentId``.
    data_template_name : str
        The data template name. Serialized as ``dataTemplateName``.
    created_by : str
        The user who created the record. Serialized as ``createdBy``.
    inventory_id : InventoryId
        The inventory item the result applies to (format ``INV...``). Serialized as
        ``inventoryId``.
    project_id : ProjectId
        The project the data belongs to (format ``PRO...``). Serialized as
        ``projectId``.
    workflow_id : WorkflowId
        The workflow (format ``WFL...``). Serialized as ``workflowId``.
    task_id : TaskId | None
        The task the result was measured on, if any (format ``TAS...``). Serialized as
        ``taskId``.

    See Also
    --------
    PropertyDataResult : The measured result carried by this item.
    """

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


ReturnScope = Literal["task", "block", "none"]
