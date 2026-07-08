from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import BTDatasetId, ProjectId
from albert.core.shared.models.base import BaseResource, EntityLink


class BTDatasetTargetReference(BaseAlbertModel):
    """A target output referenced by a Breakthrough dataset.

    Attributes
    ----------
    data_column_id : str
        The composite data template + data column identifier of the target output.
    unit_id : str | None
        The unit selected for the target output, if any.
    """

    data_column_id: str
    unit_id: str | None = Field(default=None)


class BTDatasetReferences(BaseAlbertModel):
    project_ids: list[str]
    data_column_ids: list[str] | None = Field(default=None)
    targets: list[BTDatasetTargetReference] | None = Field(default=None)
    target_ids: list[str] | None = Field(default=None)
    sheet_ids: list[str] | None = Field(default=None)
    filter: dict[str, Any] | None = Field(default=None)


class BTDataset(BaseResource):
    name: str
    id: BTDatasetId | None = Field(default=None, alias="albertId")
    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    key: str | None = Field(default=None)
    file_name: str | None = Field(default=None, alias="fileName")
    report: EntityLink | None = Field(default=None, alias="Report")
    references: BTDatasetReferences | None = Field(default=None, alias="References")
