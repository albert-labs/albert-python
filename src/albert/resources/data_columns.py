from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import DataColumnId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem
from albert.resources.parameter_groups import ValueValidation


class DataColumnType(str, Enum):
    """Type classification for a DataColumn."""

    NORMAL = "normal"
    COMPOSITE = "composite"
    SUB = "sub"


class SubDataColumnRef(BaseAlbertModel):
    """A sub-DataColumn reference, used within composite DataColumns."""

    id: DataColumnId | None = Field(default=None)
    name: str | None = Field(default=None)
    key: int | None = Field(default=None)
    required: bool = Field(default=False)
    validation: list[ValueValidation] | None = Field(default=None)
    parent_id: DataColumnId | None = Field(default=None, alias="parentId")


class DataColumn(BaseResource):
    name: str
    defalt: bool = False
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    id: str = Field(default=None, alias="albertId")
    type: DataColumnType | None = Field(default=None)
    is_system_defined: bool | None = Field(default=None, alias="isSystemDefined")
    sub_data_columns: list[SubDataColumnRef] | None = Field(default=None, alias="subDataColumns")
    parent_id: DataColumnId | None = Field(default=None, alias="parentId")
    validation: list[ValueValidation] | None = Field(default=None)


class CompositeDataColumn(DataColumn):
    """A composite DataColumn containing ordered sub-DataColumns.

    Parameters
    ----------
    name : str
        Name of the composite DataColumn.
    sub_data_columns : list[SubDataColumnRef]
        Ordered list of sub-DataColumns that make up this composite.
    is_system_defined : bool, optional
        Whether this is a system-defined column. Defaults to True for composite DACs.
    validation : list[ValueValidation], optional
        Validation rules applied at the composite level.
    """

    type: DataColumnType = Field(default=DataColumnType.COMPOSITE)
    is_system_defined: bool = Field(default=True, alias="isSystemDefined")
    sub_data_columns: list[SubDataColumnRef] = Field(alias="subDataColumns", default_factory=list)
    validation: list[ValueValidation] | None = Field(default=None)
