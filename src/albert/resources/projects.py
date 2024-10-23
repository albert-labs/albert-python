from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from albert.resources.acls import ACL
from albert.resources.base import BaseEntityLink, BaseResource, EntityLinkConvertible
from albert.resources.locations import Location
from albert.resources.serialization import SerializeAsEntityLink


class ProjectClass(str, Enum):
    """The ACL Class of a project"""

    SHARED = "shared"
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"
    PRIVATE = "private"


class State(str, Enum):
    """The current state of a project"""

    NOT_STARTED = "Not Started"
    ACTIVE = "Active"
    CLOSED_SUCCESS = "Closed - Success"
    CLOSED_ARCHIVED = "Closed - Archived"


class TaskConfig(BaseModel):
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


class Project(BaseResource, EntityLinkConvertible):
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
    metadata : dict[str, str | list[BaseEntityLink] | BaseEntityLink] | None
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
        The state of the project. Read-only.
    application_engineering_inventory_ids : list[str] | None
        Inventory Ids to be added as application engineering. Optional.

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
    id: str | None = Field(None, alias="albertId")
    acl: list[ACL] | None = Field(default_factory=list, alias="ACL")
    old_api_params: dict | None = None
    task_config: list[TaskConfig] | None = Field(default_factory=list)
    grid: GridDefault | None = None
    metadata: dict[str, str | list[BaseEntityLink] | BaseEntityLink] | None = Field(
        alias="Metadata", default=None
    )
    _state: State | None = PrivateAttr(default=None)

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "state" in data:
            self._state = data["state"]

    @property
    def state(self):
        return self._state
