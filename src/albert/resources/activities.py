from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class ActivityOperationId(str, Enum):
    POST_SDS = "post.sds"
    POST_LABEL = "post.label"


class ActivityAction(str, Enum):
    READ = "read"
    WRITE = "write"


class ActivityType(str, Enum):
    ENTITY_ID = "entityId"
    USER_ID = "userId"
    PARENT_ID = "parentId"
    UUID = "uuid"
    DATE = "date"
    DATE_RANGE = "dateRange"


class ActivitySearchItemUser(BaseAlbertModel):
    name: str | None = Field(default=None)
    id: str | None = Field(default=None)
    role: str | None = Field(default=None)
    user_class: str | None = Field(default=None, alias="class")


class ActivitySearchItem(BaseAlbertModel):
    action: str | None = Field(default=None)
    name: str | None = Field(default=None)
    pk: str | None = Field(default=None, alias="PK")
    object_class: str | None = Field(default=None, alias="class")
    logged_at: str | None = Field(default=None, alias="loggedAt")
    operation_id: str | None = Field(default=None, alias="operationId")
    object_id: str | None = Field(default=None, alias="objectId")
    object_type: str | None = Field(default=None, alias="objectType")
    activity_id: str | None = Field(default=None, alias="activityId")
    user: ActivitySearchItemUser | None = Field(default=None)


class Activity(BaseResource):
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
