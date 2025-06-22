from pydantic import Field

from albert.core.models.common import BaseResource
from albert.core.models.types import MetadataItem


class DataColumn(BaseResource):
    name: str
    defalt: bool = False
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    id: str = Field(default=None, alias="albertId")
