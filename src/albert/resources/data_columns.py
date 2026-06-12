from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


class DataColumn(BaseResource):
    """A data column definition used in data templates.

    Attributes
    ----------
    name : str
        The name of the data column.
    defalt : bool
        Whether this column is the default column. Defaults to ``False``.
    metadata : dict[str, MetadataItem] | None
        Custom metadata attached to the data column.
    id : str
        The Albert ID of the data column.
    """

    name: str
    defalt: bool = False
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    id: str = Field(default=None, alias="albertId")
