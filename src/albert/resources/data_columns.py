from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


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
        ```

    Attributes
    ----------
    name : str
        The name of the data column (e.g. ``"Viscosity"``).
    metadata : dict[str, MetadataItem], optional
        Custom metadata keyed by field name. Values may be strings, numbers, or
        entity links.
    id : str
        The Data Column ID assigned by Albert (format ``DAC...``). Populated by the
        server on creation; leave unset when building a column to create.
    status : Status or None
        The lifecycle status of the data column.
    """

    name: str
    defalt: bool = False
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    id: str = Field(default=None, alias="albertId")
