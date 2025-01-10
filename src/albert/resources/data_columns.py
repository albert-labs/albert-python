from pydantic import Field

from albert.resources.base import BaseResource, MetadataItem


class DataColumn(BaseResource):
    name: str
    defalt: bool = False
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    id: str = Field(default=None, alias="albertId")
