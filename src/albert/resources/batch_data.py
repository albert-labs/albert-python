from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import Status
from albert.core.shared.identifiers import TaskId
from albert.core.shared.models.base import BaseResource


class BatchValuePatchDatum(BaseAlbertModel):
    attribute: str = Field(default="lotId")
    lot_id: str | None = Field(default=None, alias="lotId")
    new_value: str | None = Field(default=None, alias="newValue")
    old_value: str | None = Field(default=None, alias="oldValue")
    operation: str


class BatchValueId(BaseAlbertModel):
    col_id: str | None = Field(default=None, alias="colId")
    row_id: str = Field(alias="rowId")


class BatchValuePatchPayload(BaseAlbertModel):
    id: BatchValueId = Field(alias="Id")
    data: list[BatchValuePatchDatum] = Field(default_factory=list)
    lot_id: str | None = Field(default=None, alias="lotId")


class BatchDataType(str, Enum):
    TASK_ID = "taskId"


class BatchDataValue(BaseAlbertModel):
    id: str | None = Field(default=None)
    col_id: str | None = Field(default=None, alias="colId")
    type: str | None = Field(default=None)
    name: str | None = Field(default=None)
    value: str | None = Field(default=None)
    is_editable: bool | None = Field(default=None, alias="isEditable")
    unit_category: str | None = Field(default=None, alias="unitCategory")
    reference_value: str | None = Field(default=None, alias="referenceValue")


class BatchDataRow(BaseAlbertModel):
    id: str | None = Field(default=None)
    row_id: str | None = Field(default=None, alias="rowId")
    type: str | None = Field(default=None)
    name: str | None = Field(default=None)
    manufacturer: str | None = Field(default=None)
    unit_category: str | None = Field(default=None, alias="unitCategory")
    category: str | None = Field(default=None)
    is_formula: bool | None = Field(default=None, alias="isFormula")
    is_lot_parent: bool | None = Field(default=None, alias="isLotParent")
    values: list[BatchDataValue] = Field(default_factory=list, alias="Values")
    child_rows: list["BatchDataRow"] = Field(default_factory=list, alias="ChildRows")


class BatchDataColumn(BaseAlbertModel):
    # TODO: Once SignatureOverrideMeta removed, use BaseAlbertModel instead of BaseModel
    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    col_id: str | None = Field(default=None, alias="colId")
    batch_total: str | None = Field(default=None, alias="batchTotal")
    reference_total: str | None = Field(default=None, alias="referenceTotal")
    status: Status | None = Field(default=None)
    product_total: float | None = Field(default=None, alias="productTotal")
    parent_id: str | None = Field(default=None, alias="parentId")
    design_col_id: str | None = Field(default=None, alias="designColId")
    lots: list["BatchDataColumn"] = Field(default_factory=list, alias="Lots")


class BatchData(BaseResource):
    id: TaskId | None = Field(default=None, alias="albertId")
    size: int | None = Field(default=None)
    last_key: str | None = Field(default=None, alias="lastKey")
    product: list[BatchDataColumn] | None = Field(default=None, alias="Product")
    rows: list[BatchDataRow] | None = Field(default=None, alias="Rows")
