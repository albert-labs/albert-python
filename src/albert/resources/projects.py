from __future__ import annotations

from enum import Enum

from pydantic import Field, PrivateAttr, field_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import AttachmentId, ProjectId
from albert.core.shared.models.base import BaseSessionResource
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.acls import ACL
from albert.resources.locations import Location
from albert.resources.smart_projects import SmartProject


class ProjectClass(str, Enum):
    """The ACL Class of a project"""

    SHARED = "shared"
    CONFIDENTIAL = "confidential"
    PRIVATE = "private"


class State(str, Enum):
    """The current state of a project"""

    NOT_STARTED = "Not Started"
    ACTIVE = "Active"
    CLOSED_SUCCESS = "Closed - Success"
    CLOSED_ARCHIVED = "Closed - Archived"


class TaskConfig(BaseAlbertModel):
    """The task configuration for a project"""

    datatemplateId: str | None = None
    workflowId: str | None = None
    defaultTaskName: str | None = None
    target: str | None = None
    hidden: bool | None = False


class GridDefault(str, Enum):
    """The default grid for a project"""

    PD = "PD"
    WKS = "WKS"


class Project(BaseSessionResource):
    """A project in Albert.

    Attributes
    ----------
    description : str
        The description of the project. Used as the name of the project as well.
    id : str | None
        The Albert ID of the project. Set when the project is retrieved from Albert.
    locations : list[Location] | None
        The locations associated with the project. Optional.
    project_class : ProjectClass
        The class of the project. Defaults to PRIVATE.
    metadata : dict[str, str | list[EntityLink] | EntityLink] | None
        The metadata of the project. Optional. Metadata allowed values can be found using the Custom Fields API.
    prefix : str | None
        The prefix of the project. Optional.
    acl : list[ACL] | None
        The ACL of the project. Optional.
    task_config : list[TaskConfig] | None
        The task configuration of the project. Optional.
    grid : GridDefault | None
        The default grid of the project. Optional.
    state : State | None
        The state/status of the project. Allowed states are customizeable using the entitystatus API. Optional.
    application_engineering_inventory_ids : list[str] | None
        Inventory Ids to be added as application engineering. Optional.
    smart : SmartProject | None
        Smart project metadata for the project. Optional.
    """

    description: str = Field(min_length=1, max_length=2000)
    locations: list[SerializeAsEntityLink[Location]] | None = Field(
        default=None, min_length=1, max_length=20, alias="Locations"
    )
    project_class: ProjectClass | None = Field(default=ProjectClass.PRIVATE, alias="class")
    prefix: str | None = Field(default=None)
    application_engineering_inventory_ids: list[str] | None = Field(
        default=None,
        alias="appEngg",
        description="Inventory Ids to be added as application engineering",
    )
    id: ProjectId | None = Field(None, alias="albertId")
    acl: list[ACL] | None = Field(default_factory=list, alias="ACL")
    old_api_params: dict | None = None
    task_config: list[TaskConfig] | None = Field(default_factory=list)
    grid: GridDefault | None = None
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    # Read-only fields
    status: str | None = Field(default=None, exclude=True, frozen=True)

    # Cannot be sent in a create POST, but can be referenced from a PATCH for update.
    state: State | None = Field(default=None, exclude=True)
    _smart: list[SmartProject] | None = PrivateAttr(default=None)

    @field_validator("status", mode="before")
    def validate_status(cls, value):
        """Somehow, some statuses are capitalized in the API response. This ensures they are always lowercase."""
        if isinstance(value, str):
            return value.lower()
        return value

    @property
    def smart(self) -> SmartProject | None:
        """Return the smart project resource for this project. If no smart project is found, returns None."""
        if self._smart is None:
            response = self.session.get(f"/api/v3/projects/{self.id}/getSmartProject")
            smart = response.json().get("smart", [])
            self._smart = [
                SmartProject(**item, session=self.session, project_id=self.id) for item in smart
            ]
        if not self._smart:
            return None
        return self._smart[0]


class ProjectSearchItem(BaseAlbertModel, HydrationMixin[Project]):
    id: ProjectId | None = Field(None, alias="albertId")
    description: str = Field(min_length=1, max_length=2000)
    status: str | None = Field(default=None, exclude=True, frozen=True)


class DocumentSearchItem(BaseAlbertModel):
    """A document (attachment) search result item from a project."""

    id: AttachmentId | None = Field(None, alias="albertId")
    name: str | None = None
    mime_type: str | None = Field(default=None, alias="mimeType")
    file_size: int | None = Field(default=None, alias="fileSize")
    project_id: str | None = Field(default=None, alias="projectId")
    key: str | None = None
    source: str | None = None
    created_by: str | None = Field(default=None, alias="createdBy")
    created_by_name: str | None = Field(default=None, alias="createdByName")
    created_at: str | None = Field(default=None, alias="createdAt")
