from pydantic import Field

from albert.resources.base import BaseResource, EntityLinkConvertible


class DataColumn(BaseResource, EntityLinkConvertible):
    name: str
    defalt: bool = False
    id: str = Field(None, alias="albertId")
