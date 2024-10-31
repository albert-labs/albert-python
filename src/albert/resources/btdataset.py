from pydantic import Field

from albert.resources.base import BaseEntityLink, BaseResource


class BTDataset(BaseResource):
    name: str
    id: str | None = Field(default=None, alias="albertId")
    key: str | None = Field(default=None)
    file_name: str | None = Field(default=None, alias="fileName")
    report: BaseEntityLink | None = Field(default=None, alias="Report")
