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
    """The build state of a smart dataset."""

    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"


class SmartDatasetScope(BaseAlbertModel):
    """
    Represents the scope of a smart dataset.

    Attributes
    ----------
    project_ids : list[ProjectId]
        List of project IDs.
    target_ids : list[TargetId]
        List of target IDs.
    sheet_ids : list[WorksheetId] | None
        List of worksheet IDs. If None, all worksheets in the projects will be used.
    """

    project_ids: list[ProjectId] = Field(default_factory=list, alias="projectIds")
    target_ids: list[TargetId] = Field(default_factory=list, alias="targetIds")
    sheet_ids: list[WorksheetId] | None = Field(default=None, alias="sheetIds")

    # NOTE: temporary filter to remove invalid sheet IDs due to invalid legacy data
    @field_validator("sheet_ids", mode="before")
    @classmethod
    def filter_invalid_sheet_ids(cls, v):
        if v is None:
            return v
        valid = [sid for sid in v if isinstance(sid, str) and sid.upper().startswith("WKS")]
        return valid or None


class SmartDataset(BaseResource):
    """
    Represents a smart dataset entity.

    Attributes
    ----------
    id : SmartDatasetId | None
        The unique identifier of the smart dataset.
    scope : SmartDatasetScope | None
        The dataset scope containing project, target, and sheet IDs.
    schema_ : dict | None
        The dataset schema.
    storage_key : str | None
        The storage key for the dataset.
    """

    type: Literal["smart"] = "smart"
    id: SmartDatasetId | None = Field(default=None)
    build_state: SmartDatasetBuildState | None = Field(default=None, alias="buildState")
    scope: SmartDatasetScope | None = Field(default=None)
    schema_: dict | None = Field(default=None, alias="schema")
    storage_key: str | None = Field(default=None, alias="storageKey")


class SmartDatasetAggregateBy(str, Enum):
    """The aggregation level for smart dataset experiment data."""

    INV = "inv"
    LOT = "lot"
    WFL = "wfl"
    PTD = "ptd"

    def to_api_value(self) -> str:
        return {
            SmartDatasetAggregateBy.INV: "inventory",
            SmartDatasetAggregateBy.LOT: "lot",
            SmartDatasetAggregateBy.WFL: "workflow_interval",
            SmartDatasetAggregateBy.PTD: "measurement",
        }[self.value]

    @staticmethod
    def from_api_value(value: str) -> "SmartDatasetAggregateBy":
        return {
            "inventory": SmartDatasetAggregateBy.INV,
            "lot": SmartDatasetAggregateBy.LOT,
            "workflow_interval": SmartDatasetAggregateBy.WFL,
            "measurement": SmartDatasetAggregateBy.PTD,
        }[value]


class SmartDatasetVariableDataType(str, Enum):
    """The data type of a smart dataset variable."""

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
    """A material amount variable."""

    type: Literal["material_amount"] = "material_amount"
    data_type: Literal[SmartDatasetVariableDataType.NUMERIC] = SmartDatasetVariableDataType.NUMERIC


class ParameterVariable(_BaseVariable):
    """A parameter variable."""

    type: Literal["parameter"] = "parameter"
    data_type: SmartDatasetVariableDataType
    sources: list[Literal["property", "batch", "process_design"]] = Field(default_factory=list)


class MoleculeVariable(_BaseVariable):
    """A molecule variable."""

    type: Literal["molecule"] = "molecule"
    data_type: Literal[SmartDatasetVariableDataType.MOLECULAR] = (
        SmartDatasetVariableDataType.MOLECULAR
    )


class PropertyVariable(_BaseVariable):
    """A property variable."""

    type: Literal["property"] = "property"
    data_type: SmartDatasetVariableDataType


SmartDatasetVariable = Annotated[
    MaterialAmountVariable | ParameterVariable | MoleculeVariable | PropertyVariable,
    Field(discriminator="type"),
]


class SmartDatasetData(BaseAlbertModel):
    """
    The experiment data matrix for a smart dataset.

    Attributes
    ----------
    aggregate_by : SmartDatasetAggregateBy
        The aggregation level of the returned data.
    identifiers : list[SmartDatasetRecordIdentifier]
        The identifier metadata for each row index entry.
    variables : list[SmartDatasetVariable]
        The variable metadata for each column entry.
    data : OrientTightDataFrame
        The experiment data values.
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
