from pydantic import Field

from albert.resources.base import BaseResource, EntityLink
from albert.utils.types import BaseAlbertModel


class BTDatasetReferences(BaseAlbertModel):
    project_ids: list[str]
    data_column_ids: list[str]


class BTDataset(BaseResource):
    name: str
    id: str | None = Field(default=None, alias="albertId")
    key: str | None = Field(default=None)
    file_name: str | None = Field(default=None, alias="fileName")
    report: EntityLink | None = Field(default=None, alias="Report")
    references: BTDatasetReferences | None = Field(default=None, alias="References")
