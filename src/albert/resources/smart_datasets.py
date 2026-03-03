from typing import Literal

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    ProjectId,
    SmartDatasetId,
    TargetId,
    WorksheetId,
)
from albert.core.shared.models.base import BaseResource


class SmartDatasetScope(BaseAlbertModel):
    """
    Represents the scope of a smart dataset.

    Attributes
    ----------
    project_ids : list[ProjectId]
        List of project IDs.
    target_ids : list[TargetId]
        List of target IDs.
    sheet_ids : list[WorksheetId] | None
        List of worksheet IDs. If None, all worksheets in the projects will be used.
    """

    project_ids: list[ProjectId] = Field(default_factory=list, alias="projectIds")
    target_ids: list[TargetId] = Field(default_factory=list, alias="targetIds")
    sheet_ids: list[WorksheetId] | None = Field(default=None, alias="sheetIds")


class SmartDataset(BaseResource):
    """
    Represents a smart dataset entity.

    Attributes
    ----------
    id : SmartDatasetId | None
        The unique identifier of the smart dataset.
    scope : SmartDatasetScope | None
        The dataset scope containing project, target, and sheet IDs.
    schema_ : dict | None
        The dataset schema.
    storage_key : str | None
        The storage key for the dataset.
    """

    type: Literal["smart"] = "smart"
    id: SmartDatasetId | None = Field(default=None)
    scope: SmartDatasetScope | None = Field(default=None)
    schema_: dict | None = Field(default=None, alias="schema")
    storage_key: str | None = Field(default=None, alias="storageKey")
