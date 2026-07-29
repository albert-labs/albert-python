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
from albert.resources.smart_projects import _PROJECTS_BASE_PATH, SmartProject


class ProjectClass(str, Enum):
    """The access-control class of a project, governing who can see it.

    - ``PRIVATE``: visible only to the project's ACL members (the default).
    - ``SHARED``: visible more broadly across the organization.
    - ``CONFIDENTIAL``: restricted, most tightly controlled access.
    """

    SHARED = "shared"
    CONFIDENTIAL = "confidential"
    PRIVATE = "private"


class State(str, Enum):
    """The lifecycle state of a project.

    The set of allowed states is customizable per tenant via the entity-status
    API; these are the platform defaults.
    """

    NOT_STARTED = "Not Started"
    ACTIVE = "Active"
    CLOSED_SUCCESS = "Closed - Success"
    CLOSED_ARCHIVED = "Closed - Archived"


class TaskConfig(BaseAlbertModel):
    """Default task settings applied when tasks are created within a project."""

    datatemplateId: str | None = None
    """ID of the data template tasks default to."""

    workflowId: str | None = None
    """ID of the workflow tasks default to."""

    defaultTaskName: str | None = None
    """Default name applied to new tasks."""

    target: str | None = None
    """Default target for the configured tasks."""

    hidden: bool | None = False
    """Whether this configuration is hidden in the UI."""


class GridDefault(str, Enum):
    """The default grid view shown for a project.

    - ``PD``: the Property Data grid.
    - ``WKS``: the Worksheet grid.
    """

    PD = "PD"
    WKS = "WKS"


class Project(BaseSessionResource):
    """A project in Albert: the top-level container for a piece of R&D work.

    A project groups the formulations designed for the work, its Worksheet (1:1
    with the project), the Tasks run against it, and the inventory it references.
    Create and manage projects through the
    [`ProjectCollection`][albert.collections.projects.ProjectCollection] (``client.projects``).

    Only ``description`` is required to build one; it doubles as the project's
    display name. The ``id`` and ``state`` are assigned by Albert and are read
    only from the client's perspective.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.projects import Project, ProjectClass
        client = Albert()
        project = client.projects.create(
            project=Project(
                description="Weatherproof Coatings 2026",
                project_class=ProjectClass.SHARED,
            )
        )
        project.id
        # 'PRO123'
        ```"""

    description: str = Field(min_length=1, max_length=2000)
    """Human-readable project name/description (1-2000 characters). Also serves as the project's display name."""

    locations: list[SerializeAsEntityLink[Location]] | None = Field(
        default=None, min_length=1, max_length=20, alias="Locations"
    )
    """The locations the project is associated with. Optional."""

    project_class: ProjectClass | None = Field(default=ProjectClass.PRIVATE, alias="class")
    """Access-control class (private, shared, or confidential). Defaults to private."""

    prefix: str | None = Field(default=None)
    """Optional prefix used when naming entities within the project."""

    application_engineering_inventory_ids: list[str] | None = Field(
        default=None,
        alias="appEngg",
        description="Inventory Ids to be added as application engineering",
    )
    id: ProjectId | None = Field(None, alias="albertId")
    """The Albert Project ID (format ``PRO...``). Assigned by Albert and present once the project has been created or retrieved."""

    acl: list[ACL] | None = Field(default_factory=list, alias="ACL")
    """Access-control entries controlling who can access the project. Optional."""

    old_api_params: dict | None = None
    """Read-only. Do not use."""

    task_config: list[TaskConfig] | None = Field(default_factory=list)
    """Default task settings applied to tasks created within the project."""

    grid: GridDefault | None = None
    """The default grid view (Property Data or Worksheet) shown for the project."""

    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    """Custom field values. Allowed keys and values are defined via the Custom Fields API. Optional."""
    # Read-only fields
    status: str | None = Field(default=None, exclude=True, frozen=True)
    """Read-only status string returned by Albert."""

    # Cannot be sent in a create POST, but can be referenced from a PATCH for update.
    state: State | None = Field(default=None, exclude=True)
    """The project's lifecycle state. Read only on create; can be changed via [`update`][albert.collections.projects.ProjectCollection.update]."""

    _smart: list[SmartProject] | None = PrivateAttr(default=None)

    @field_validator("status", mode="before")
    def validate_status(cls, value):
        """Somehow, some statuses are capitalized in the API response. This ensures they are always lowercase."""
        if isinstance(value, str):
            return value.lower()
        return value

    @property
    def smart(self) -> SmartProject | None:
        """Return the project-bound Smart Projects interface for this project.

        Use this property for Smart Projects workflows: adding targets and
        building smart datasets scoped to the project. For standalone target or
        smart dataset creation, use
        [`TargetCollection`][albert.collections.targets.TargetCollection] or
        [`SmartDatasetCollection`][albert.collections.smart_datasets.SmartDatasetCollection]
        instead.

        Returns
        -------
        SmartProject or None
            The [`SmartProject`][albert.resources.smart_projects.SmartProject]
            for this project, or ``None`` if no smart project record exists yet.
        """
        if self._smart is None:
            response = self.session.get(f"{_PROJECTS_BASE_PATH}/{self.id}/getSmartProject")
            smart = response.json().get("smart", [])
            self._smart = [
                SmartProject(**item, session=self.session, project_id=self.id) for item in smart
            ]
        if not self._smart:
            return None
        return self._smart[0]


class ProjectSearchItem(BaseAlbertModel, HydrationMixin[Project]):
    """A lightweight (partial) project returned by project search.

    Returned by [`search`][albert.collections.projects.ProjectCollection.search],
    this carries only summary fields for fast listing. Use its hydration support
    (or fetch by ``id`` via
    [`get_by_id`][albert.collections.projects.ProjectCollection.get_by_id]) to obtain
    the full [`Project`][albert.resources.projects.Project]."""

    id: ProjectId | None = Field(None, alias="albertId")
    """The Albert Project ID (format ``PRO...``)."""

    description: str = Field(min_length=1, max_length=2000)
    """The project's name/description."""

    status: str | None = Field(default=None, exclude=True, frozen=True)
    """Read-only status string returned by Albert."""


class DocumentSearchItem(BaseAlbertModel):
    """A document (attachment) search result linked to a project.

    Returned by
    [`document_search`][albert.collections.projects.ProjectCollection.document_search]. Each
    item describes an attachment's metadata rather than its file contents."""

    id: AttachmentId | None = Field(None, alias="albertId")
    """The Albert Attachment ID (format ``ATT...``)."""

    name: str | None = None
    """The document's file name."""

    mime_type: str | None = Field(default=None, alias="mimeType")
    """The document's MIME type (e.g. ``application/pdf``)."""

    file_size: int | None = Field(default=None, alias="fileSize")
    """The document's size in bytes."""

    project_id: str | None = Field(default=None, alias="projectId")
    """ID of the project the document is linked to."""

    key: str | None = None
    """Storage key for the document."""

    source: str | None = None
    """Source system or origin of the document."""

    created_by: str | None = Field(default=None, alias="createdBy")
    """ID of the user who uploaded the document."""

    created_by_name: str | None = Field(default=None, alias="createdByName")
    """Name of the user who uploaded the document."""

    created_at: str | None = Field(default=None, alias="createdAt")
    """Timestamp when the document was created."""
