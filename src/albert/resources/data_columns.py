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
    """The definition of a single measured result variable in Albert.

    A Data Column (DAC) defines one direct output variable that a task can
    measure, such as ``Viscosity`` or ``APHA Color``. Data columns are the
    reusable building blocks of a Data Template's results: a
    [`DataTemplate`][albert.resources.data_templates.DataTemplate] references data columns
    through its ``data_column_values``, and the values recorded against a data
    column during experiments are stored as Property Data.

    Data columns are identified by a Data Column ID (format ``DAC...``, e.g.
    ``"DAC1"``) and are managed through
    [`DataColumnCollection`][albert.collections.data_columns.DataColumnCollection], accessed as
    ``client.data_columns``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.data_columns import DataColumn
        client = Albert()
        column = DataColumn(name="Viscosity")
        created = client.data_columns.create(data_column=column)
        created.id
        # 'DAC1'
        ```"""

    name: str
    """The name of the data column (e.g. ``"Viscosity"``)."""

    defalt: bool = False
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    """Custom metadata keyed by field name. Values may be strings, numbers, or entity links."""

    id: str = Field(default=None, alias="albertId")
    """The Data Column ID assigned by Albert (format ``DAC...``). Populated by the server on creation; leave unset when building a column to create."""
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
