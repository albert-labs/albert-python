from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import BTDatasetId, ProjectId
from albert.core.shared.models.base import BaseResource, EntityLink


class BTDatasetReferences(BaseAlbertModel):
    """Scope references used to build a Breakthrough dataset.

    Attributes
    ----------
    project_ids : list[str]
        The project IDs included in the dataset.
    data_column_ids : list[str]
        The data column IDs included in the dataset.
    sheet_ids : list[str] | None
        The sheet IDs to restrict the dataset to. If None, all sheets are included.
    filter : dict[str, Any] | None
        Additional filter criteria applied when building the dataset.
    """

    project_ids: list[str]
    data_column_ids: list[str]
    sheet_ids: list[str] | None = Field(default=None)
    filter: dict[str, Any] | None = Field(default=None)


class BTDataset(BaseResource):
    """A Breakthrough dataset built from project and column references.

    Attributes
    ----------
    name : str
        The name of the dataset.
    id : BTDatasetId | None
        The Albert ID of the dataset.
    parent_id : ProjectId | None
        The ID of the project this dataset belongs to.
    key : str | None
        The storage key for the dataset file.
    file_name : str | None
        The file name of the dataset.
    report : EntityLink | None
        A link to the report generated from this dataset.
    references : BTDatasetReferences | None
        The scope references used to build this dataset.
    """

    name: str
    id: BTDatasetId | None = Field(default=None, alias="albertId")
    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    key: str | None = Field(default=None)
    file_name: str | None = Field(default=None, alias="fileName")
    report: EntityLink | None = Field(default=None, alias="Report")
    references: BTDatasetReferences | None = Field(default=None, alias="References")
