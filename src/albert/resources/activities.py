from enum import Enum
from typing import Any

from pydantic import AliasChoices, Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class ActivityOperationId(str, Enum):
    """A specific logged operation used to scope activity recency queries.

    Attributes
    ----------
    POST_SDS : str
        The most recent Safety Data Sheet (SDS) publish operation.
    POST_LABEL : str
        The most recent label publish operation.
    """

    POST_SDS = "post.sds"
    POST_LABEL = "post.label"


class ActivityAction(str, Enum):
    """The kind of operation recorded by an activity.

    Attributes
    ----------
    READ : str
        A read operation (an entity was viewed or fetched).
    WRITE : str
        A write operation (an entity was created or modified).
    """

    READ = "read"
    WRITE = "write"


class ActivityType(str, Enum):
    """The scope a [`get_all`][albert.collections.activities.ActivityCollection.get_all]
    query is anchored to.

    Attributes
    ----------
    ENTITY_ID : str
        Activities for a single entity, identified by its Albert ID.
    USER_ID : str
        Activities performed by a single user.
    PARENT_ID : str
        Activities for entities belonging to a given parent entity.
    UUID : str
        Activities for a single activity UUID.
    DATE : str
        Activities on a single date.
    DATE_RANGE : str
        Activities across a date range (``id`` is not supported for this type).
    """

    ENTITY_ID = "entityId"
    USER_ID = "userId"
    PARENT_ID = "parentId"
    UUID = "uuid"
    DATE = "date"
    DATE_RANGE = "dateRange"


class ActivitySearchItemUser(BaseAlbertModel):
    """The user associated with an [`ActivitySearchItem`][albert.resources.activities.ActivitySearchItem]."""

    name: str | None = Field(default=None)
    """The user's display name."""

    id: str | None = Field(default=None)
    """The user's Albert ID."""

    role: str | None = Field(default=None)
    """The user's role at the time of the activity."""

    user_class: str | None = Field(default=None, alias="class")
    """The user's class value."""


class ActivityActorAct(BaseAlbertModel):
    """Actor delegation identity information for service-to-service calls."""

    sub: str | None = Field(default=None)
    """Subject identifier of the calling service."""

    name: str | None = Field(default=None)
    """Display name of the calling service or delegation scope."""


class ActivityActorDetails(BaseAlbertModel):
    """Execution and delegation details of an [`ActivityActor`][albert.resources.activities.ActivityActor]."""

    mode: str | None = Field(default=None)
    """Authentication or delegation mode (e.g. ``"obo"`` for on-behalf-of)."""

    client_id: str | None = Field(
        default=None,
        alias="client_id",
        validation_alias=AliasChoices("client_id", "clientId"),
    )
    """OAuth client ID of the service performing the activity."""

    act: ActivityActorAct | None = Field(default=None)
    """Delegation details identifying the upstream service."""


class ActivityActor(BaseAlbertModel):
    """Service-to-service actor (sibling to user) on activity events."""

    details: ActivityActorDetails | None = Field(default=None)
    """Delegation and execution details for the service actor."""

    metadata: dict[str, Any] | None = Field(default=None)
    """Arbitrary key-value metadata associated with the actor call (e.g. trace ID)."""


class ActivitySearchItem(BaseAlbertModel):
    """A lightweight activity record returned by
    [`search`][albert.collections.activities.ActivityCollection.search]."""

    action: str | None = Field(default=None)
    """The operation recorded (e.g. ``"read"`` or ``"write"``)."""

    name: str | None = Field(default=None)
    """Display name of the entity the activity acted on."""

    pk: str | None = Field(default=None, alias="PK")
    """The internal partition key for the record."""

    object_class: str | None = Field(default=None, alias="class")
    """The class of the entity the activity acted on."""

    logged_at: str | None = Field(default=None, alias="loggedAt")
    """Timestamp when the activity was logged."""

    operation_id: str | None = Field(default=None, alias="operationId")
    """The logged operation identifier."""

    object_id: str | None = Field(default=None, alias="objectId")
    """The Albert ID of the entity the activity acted on."""

    object_type: str | None = Field(default=None, alias="objectType")
    """The type of the entity the activity acted on."""

    activity_id: str | None = Field(default=None, alias="activityId")
    """The unique ID of the activity record."""

    user: ActivitySearchItemUser | None = Field(default=None)
    """The user who performed the activity."""

    actor: ActivityActor | None = Field(default=None)
    """The service actor that performed the activity, if logged via service-to-service."""


class Activity(BaseResource):
    """A single event in the Albert activity feed (audit trail).

    Returned by [`get_all`][albert.collections.activities.ActivityCollection.get_all].
    Each record captures an action performed on an entity, together with metadata
    about where in the platform it occurred. Activities are produced by the
    platform and are read-only."""

    id: str | None = Field(default=None, alias="albertId")
    """The Albert ID of the activity record."""

    activity_id: str | None = Field(default=None, alias="activityId")
    """The unique activity identifier."""

    action: str | None = Field(default=None)
    """The operation recorded (e.g. ``"read"`` or ``"write"``)."""

    operation_id: str | None = Field(default=None, alias="operationId")
    """The logged operation identifier."""

    data: dict | None = Field(default=None)
    """Free-form payload describing the change, when available."""

    env: str | None = Field(default=None)
    """The environment in which the activity was logged."""

    name: str | None = Field(default=None)
    """Display name of the entity the activity acted on."""

    module: str | None = Field(default=None)
    """The platform module the activity belongs to."""

    sub_module: str | None = Field(default=None, alias="subModule")
    """The platform sub-module the activity belongs to."""

    uri: str | None = Field(default=None)
    """The resource URI associated with the activity."""

    uuid: str | None = Field(default=None)
    """The activity UUID."""

    expires_at: float | None = Field(default=None, alias="expiresAt")
    """Expiry timestamp for the record, when applicable."""

    region: str | None = Field(default=None)
    """The region in which the activity was logged."""

    actor: ActivityActor | None = Field(default=None)
    """The service actor that performed the activity, if logged via service-to-service."""
