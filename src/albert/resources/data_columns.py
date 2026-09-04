from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import Status
from albert.core.shared.identifiers import DataColumnId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem
from albert.resources._mixins import HydrationMixin


class DataColumn(BaseResource):
    """The definition of a single measured result variable in Albert.

    A Data Column (DAC) defines one direct output variable that a task can
    measure, such as ``Viscosity`` or ``APHA Color``. Data columns are the
    reusable building blocks of a Data Template's results: a
    [`DataTemplate`][albert.resources.data_templates.DataTemplate] references data columns
    through its ``data_column_values``, and the values recorded against a data
    column during experiments are stored as Property Data.

    Data columns are identified by a Data Column ID (format ``DAC...``, e.g.
    ``"DAC9999999"``) and are managed through
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
        # 'DAC9999999'
        ```"""

    name: str
    """The name of the data column (e.g. ``"Viscosity"``)."""

    defalt: bool = False
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    """Custom metadata keyed by field name. Values may be strings, numbers, or entity links."""

    id: str = Field(default=None, alias="albertId")
    """The Data Column ID assigned by Albert (format ``DAC...``). Populated by the server on creation; leave unset when building a column to create."""


class DataColumnSearchItemDataTemplate(BaseAlbertModel):
    """A lightweight data template reference within a data column search result."""

    id: str | None = Field(default=None, alias="albertId")
    """The Albert ID of the data template (format ``DAT...``)."""

    name: str | None = None
    """The name of the data template."""

    status: Status | None = None
    """The status of the data template."""


class DataColumnSearchItem(BaseAlbertModel, HydrationMixin[DataColumn]):
    """Lightweight representation of a DataColumn returned from search.

    Returned by
    [`search`][albert.collections.data_columns.DataColumnCollection.search],
    this carries only summary fields for fast listing. Call ``hydrate()`` (or fetch
    by ``id`` via
    [`get_by_id`][albert.collections.data_columns.DataColumnCollection.get_by_id])
    to obtain the fully populated
    [`DataColumn`][albert.resources.data_columns.DataColumn]."""

    id: DataColumnId = Field(alias="albertId")
    """The Data Column ID (format ``DAC...``)."""

    name: str | None = None
    """The name of the data column."""

    status: Status | None = None
    """The status of the data column."""

    created_by_name: str | None = Field(default=None, alias="createdByName")
    """The name of the user who created the data column."""

    created_by: str | None = Field(default=None, alias="createdBy")
    """The ID of the user who created the data column."""

    created_at: str | None = Field(default=None, alias="createdAt")
    """ISO 8601 timestamp of when the data column was created."""

    updated_at: str | None = Field(default=None, alias="updatedAt")
    """ISO 8601 timestamp of when the data column was last updated."""

    metadata: dict[str, Any] | None = Field(default=None, alias="Metadata")
    """Custom metadata attached to the data column."""

    data_templates: list[DataColumnSearchItemDataTemplate] | None = Field(
        default=None, alias="DataTemplates"
    )
    """The data templates that reference this data column."""

    type: str | None = None
    """The composite type of the data column (e.g. ``composite``, ``sub``), when applicable."""

    parent_data_column: "DataColumnSearchItem | None" = Field(
        default=None, alias="parentDataColumn"
    )
    """The parent data column, present on composite sub-column rows."""

    sub_data_columns: "list[DataColumnSearchItem] | None" = Field(
        default=None, alias="subDataColumns"
    )
    """The sub data columns, present on composite parent rows."""
