from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, field_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    ProjectId,
    SmartDatasetId,
    TargetId,
    WorksheetId,
)
from albert.core.shared.models.base import BaseResource
from albert.utils.dataframes import OrientTightDataFrame


class SmartDatasetBuildState(str, Enum):
    """The build state of a smart dataset.

    A smart dataset is populated asynchronously; its build state reports where it
    is in that process. Data can only be retrieved once the state is ``READY``.

    Attributes
    ----------
    BUILDING : str
        The dataset is still being assembled from its scope; data is not yet
        available.
    READY : str
        The dataset has finished building and its experiment data matrix can be
        retrieved.
    FAILED : str
        The build did not complete successfully.
    """

    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"


class SmartDatasetScope(BaseAlbertModel):
    """The scope defining which experiment data a smart dataset draws from.

    The scope selects the source of the dataset's records: the projects to
    include, any specific targets, and optionally the worksheets to restrict to.
    It is the main input supplied when creating or re-scoping a dataset.

    Attributes
    ----------
    project_ids : list[ProjectId]
        The projects whose experiments feed the dataset.
    target_ids : list[TargetId]
        Specific targets to include.
    sheet_ids : list[WorksheetId] | None
        The worksheets to restrict to. If None, all worksheets in the selected
        projects are used.
    target_parent_ids : dict[TargetId, ProjectId] | None
        Optional mapping from target ID to a parent project ID. When set, the target
        inherits its ACL policy from the referenced project.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.smart_datasets import SmartDatasetScope

        scope = SmartDatasetScope(
            project_ids=["PRO123"],
            sheet_ids=["WKS456"],
        )
        ```
    """

    project_ids: list[ProjectId] = Field(default_factory=list, alias="projectIds")
    target_ids: list[TargetId] = Field(default_factory=list, alias="targetIds")
    sheet_ids: list[WorksheetId] | None = Field(default=None, alias="sheetIds")
    target_parent_ids: dict[TargetId, ProjectId] | None = Field(
        default_factory=dict, alias="targetParentIds"
    )

    # NOTE: temporary filter to remove invalid sheet IDs due to invalid legacy data
    @field_validator("sheet_ids", mode="before")
    @classmethod
    def filter_invalid_sheet_ids(cls, v):
        if v is None:
            return v
        valid = [sid for sid in v if isinstance(sid, str) and sid.upper().startswith("WKS")]
        return valid or None


class SmartDataset(BaseResource):
    """A smart dataset: a scoped, built matrix of experiment data.

    A smart dataset is created from a :class:`SmartDatasetScope` and built
    asynchronously by Albert. Its experiment data matrix is retrieved separately
    (see
    :meth:`~albert.collections.smart_datasets.SmartDatasetCollection.get_data`)
    rather than being carried on this object.

    A ``SmartDataset`` and a :class:`~albert.resources.btdataset.BTDataset` are
    distinct entities that share an ETL engine (Zeus stored procedures) but are not
    interchangeable: a ``SmartDataset`` is a Smart Projects entity (S3-backed, via
    ``storage_key`` and ``schema_``), while a ``BTDataset`` is a Breakthrough
    pointer record. A SmartDataset is not itself an input to Albert Breakthrough.

    Attributes
    ----------
    id : SmartDatasetId | None
        The unique identifier of the smart dataset (format ``SDT...``).
    parent_id : ProjectId | None
        The ID of the parent project this smart dataset belongs to. When set,
        the smart dataset inherits its ACL policy from the referenced project.
    build_state : SmartDatasetBuildState | None
        Where the dataset is in its build lifecycle. Data is available once this
        is ``ready``.
    scope : SmartDatasetScope | None
        The scope defining which projects, targets, and worksheets the dataset
        draws its experiment data from.
    schema_ : dict | None
        Serialized dataset schema (from the dataset's ``get_schema()``): variable
        metadata for the experiments/mixtures/inventory tables.
    storage_key : str | None
        S3 key for the built dataset JSON.
    """

    type: Literal["smart"] = "smart"
    id: SmartDatasetId | None = Field(default=None)
    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    build_state: SmartDatasetBuildState | None = Field(default=None, alias="buildState")
    scope: SmartDatasetScope | None = Field(default=None)
    schema_: dict | None = Field(default=None, alias="schema")
    storage_key: str | None = Field(default=None, alias="storageKey")


class SmartDatasetAggregateBy(str, Enum):
    """The aggregation level for smart dataset experiment data.

    Controls what each row (record) in the returned matrix represents, from the
    coarsest (one row per inventory item) to the finest (one row per measurement).

    Attributes
    ----------
    INV : str
        Aggregate to one record per inventory item.
    LOT : str
        Aggregate to one record per lot.
    WFL : str
        Aggregate to one record per workflow (experiment).
    PTD : str
        Finest granularity: one record per measurement (API value ``measurement``);
        record identifiers at this level include ``property_data_id``.
    """

    INV = "inv"
    LOT = "lot"
    WFL = "wfl"
    PTD = "ptd"

    def to_api_value(self) -> str:
        return {
            SmartDatasetAggregateBy.INV: "inventory",
            SmartDatasetAggregateBy.LOT: "lot",
            SmartDatasetAggregateBy.WFL: "workflow",
            SmartDatasetAggregateBy.PTD: "measurement",
        }[self.value]

    @staticmethod
    def from_api_value(value: str) -> "SmartDatasetAggregateBy":
        return {
            "inventory": SmartDatasetAggregateBy.INV,
            "lot": SmartDatasetAggregateBy.LOT,
            "workflow": SmartDatasetAggregateBy.WFL,
            "measurement": SmartDatasetAggregateBy.PTD,
        }[value]


class SmartDatasetVariableDataType(str, Enum):
    """The data type of a smart dataset variable (column).

    Attributes
    ----------
    NUMERIC : str
        Continuous or discrete numeric values.
    CATEGORICAL : str
        Discrete, unordered category labels.
    MOLECULAR : str
        Molecular structure values (e.g. a molecule column).
    BOOLEAN : str
        True/false values.
    """

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    MOLECULAR = "molecular"
    BOOLEAN = "boolean"


class SmartDatasetRecordIdentifier(BaseAlbertModel):
    """
    An identifier for a record in a smart dataset experiment data matrix.

    The same shape is used across all aggregation levels (inventory, material,
    experiment, measurement); fields that don't apply at a given level are left
    unset.

    Attributes
    ----------
    type : str
        The identifier type (e.g., ``albert_inventory``, ``albert_material``).
    inventory_id : str
        The inventory ID of the record.
    key : str | None
        The unique key of the identifier.
    lot_id : str | None
        The lot ID, if applicable.
    workflow_interval : str | None
        The workflow interval, if applicable.
    task_id : str | None
        The task ID, if applicable.
    property_data_id : str | None
        The property data ID, if applicable.
    """

    type: str
    inventory_id: str
    key: str | None = Field(default=None)
    lot_id: str | None = Field(default=None)
    workflow_interval: str | None = Field(default=None)
    task_id: str | None = Field(default=None)
    property_data_id: str | None = Field(default=None)


class _BaseVariable(BaseAlbertModel):
    key: str
    name: str


class MaterialAmountVariable(_BaseVariable):
    """A dataset column for the amount of a material used in an experiment.

    Attributes
    ----------
    key : str
        The unique key identifying this variable (column) in the data matrix.
    name : str
        The human-readable name of the variable.
    type : str
        The variable type discriminator; always ``material_amount``.
    data_type : SmartDatasetVariableDataType
        The value type; always ``NUMERIC`` for material amounts.
    """

    type: Literal["material_amount"] = "material_amount"
    data_type: Literal[SmartDatasetVariableDataType.NUMERIC] = SmartDatasetVariableDataType.NUMERIC


class ParameterVariable(_BaseVariable):
    """A dataset column for an experiment parameter.

    Attributes
    ----------
    key : str
        The unique key identifying this variable (column) in the data matrix.
    name : str
        The human-readable name of the variable.
    type : str
        The variable type discriminator; always ``parameter``.
    data_type : SmartDatasetVariableDataType
        The value type of the parameter.
    sources : list[str]
        Which RET48 origins contributed the parameter values: ``"property"``,
        ``"batch"``, or ``"process_design"`` (overlaps resolved by the ETL, with
        batch taking precedence over process-design).
    """

    type: Literal["parameter"] = "parameter"
    data_type: SmartDatasetVariableDataType
    sources: list[Literal["property", "batch", "process_design"]] = Field(default_factory=list)


class MoleculeVariable(_BaseVariable):
    """A dataset column for a molecular structure.

    Attributes
    ----------
    key : str
        The unique key identifying this variable (column) in the data matrix.
    name : str
        The human-readable name of the variable.
    type : str
        The variable type discriminator; always ``molecule``.
    data_type : SmartDatasetVariableDataType
        The value type; always ``MOLECULAR`` for molecule variables.
    """

    type: Literal["molecule"] = "molecule"
    data_type: Literal[SmartDatasetVariableDataType.MOLECULAR] = (
        SmartDatasetVariableDataType.MOLECULAR
    )


class PropertyVariable(_BaseVariable):
    """A dataset column for a measured property.

    Attributes
    ----------
    key : str
        The unique key identifying this variable (column) in the data matrix.
    name : str
        The human-readable name of the variable.
    type : str
        The variable type discriminator; always ``property``.
    data_type : SmartDatasetVariableDataType
        The value type of the measured property.
    """

    type: Literal["property"] = "property"
    data_type: SmartDatasetVariableDataType


SmartDatasetVariable = Annotated[
    MaterialAmountVariable | ParameterVariable | MoleculeVariable | PropertyVariable,
    Field(discriminator="type"),
]


class SmartDatasetData(BaseAlbertModel):
    """The built experiment data matrix for a smart dataset.

    Rows are records (experiments, materials, lots, or measurements, depending on
    ``aggregate_by``) and columns are variables (material amounts, parameters,
    molecules, and measured properties). ``identifiers`` describes each row and
    ``variables`` describes each column, aligned with ``data``.

    Attributes
    ----------
    aggregate_by : SmartDatasetAggregateBy
        The aggregation level of the returned rows.
    identifiers : list[SmartDatasetRecordIdentifier]
        The identifier metadata for each row, aligned with the rows of ``data``.
    variables : list[SmartDatasetVariable]
        The variable metadata for each column, aligned with the columns of ``data``.
    data : OrientTightDataFrame
        The experiment data values as a record-by-variable matrix.
    uncertainty : OrientTightDataFrame | None
        The associated uncertainty values, if available.
    counts : OrientTightDataFrame | None
        The associated observation counts, if available.
    """

    aggregate_by: SmartDatasetAggregateBy
    identifiers: list[SmartDatasetRecordIdentifier] = Field(default_factory=list)
    variables: list[SmartDatasetVariable] = Field(default_factory=list)
    data: OrientTightDataFrame
    uncertainty: OrientTightDataFrame | None = Field(default=None)
    counts: OrientTightDataFrame | None = Field(default=None)
