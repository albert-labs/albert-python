from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import BaseResource


class ActivityOperationId(str, Enum):
    """Operation identifiers for activity log entries."""

    POST_SDS = "post.sds"
    POST_LABEL = "post.label"


class ActivityAction(str, Enum):
    """Action type recorded in an activity log entry."""

    READ = "read"
    WRITE = "write"


class ActivityType(str, Enum):
    """Filter type used when querying activity logs."""

    ENTITY_ID = "entityId"
    USER_ID = "userId"
    PARENT_ID = "parentId"
    UUID = "uuid"
    DATE = "date"
    DATE_RANGE = "dateRange"


class Activity(BaseResource):
    """An activity log entry recorded by the Albert platform.

    Attributes
    ----------
    id : str | None
        The Albert ID of the activity entry.
    activity_id : str | None
        The unique activity identifier.
    action : str | None
        The action taken (e.g. ``"read"`` or ``"write"``).
    operation_id : str | None
        The operation identifier associated with the activity.
    data : dict | None
        Payload data associated with the activity.
    env : str | None
        The environment in which the activity occurred.
    name : str | None
        The name of the entity involved in the activity.
    module : str | None
        The module that generated the activity.
    sub_module : str | None
        The sub-module that generated the activity.
    uri : str | None
        The URI of the resource involved in the activity.
    uuid : str | None
        A UUID for the activity record.
    expires_at : float | None
        Unix timestamp when this activity record expires.
    region : str | None
        The region where the activity occurred.
    """

    id: str | None = Field(default=None, alias="albertId")
    activity_id: str | None = Field(default=None, alias="activityId")
    action: str | None = Field(default=None)
    operation_id: str | None = Field(default=None, alias="operationId")
    data: dict | None = Field(default=None)
    env: str | None = Field(default=None)
    name: str | None = Field(default=None)
    module: str | None = Field(default=None)
    sub_module: str | None = Field(default=None, alias="subModule")
    uri: str | None = Field(default=None)
    uuid: str | None = Field(default=None)
    expires_at: float | None = Field(default=None, alias="expiresAt")
    region: str | None = Field(default=None)
