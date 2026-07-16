from collections.abc import Iterator
from datetime import date

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.resources.activities import (
    Activity,
    ActivityAction,
    ActivityOperationId,
    ActivitySearchItem,
    ActivityType,
)


class ActivityCollection(BaseCollection):
    """Read the Albert activity feed (audit trail) for entities and users.

    An Activity is a single logged event in Albert's audit trail, recording an
    action (such as a read or a write) performed on an entity by a user. The feed
    is used to answer questions like "what changed on this item and when" or
    "what has this user done recently". Activities are produced by the platform
    and are read-only through the SDK; there is no create, update, or delete.

    Use [`get_all`][albert.collections.activities.ActivityCollection.get_all] to page through the raw feed scoped to a single entity,
    user, or date, and [`search`][albert.collections.activities.ActivityCollection.search] to run a full-text/filtered query across
    activity records.

    This collection is accessed as ``client.activities``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for activity requests.

    Methods
    -------
    get_all(type, ...) -> Iterator[Activity]
        Page through the activity feed scoped by entity, user, or date.
    search(...) -> Iterator[ActivitySearchItem]
        Search activity records using full-text and filter criteria.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.activities import ActivityType

        client = Albert()
        # Recent activity for a single entity, newest first
        for activity in client.activities.get_all(
            type=ActivityType.ENTITY_ID,
            id="INVA1",
            max_items=25,
        ):
            print(activity.name, activity.action)
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize an ActivityCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ActivityCollection._api_version}/activities"

    def get_all(
        self,
        *,
        type: ActivityType,
        id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        operation_id: ActivityOperationId | None = None,
        action: ActivityAction | None = ActivityAction.WRITE,
        order_by: OrderBy | None = OrderBy.DESCENDING,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Activity]:
        """Page through the activity feed scoped by entity, user, or date.

        Returns the raw activity records for a single scope, chosen with ``type``:
        the events for one entity, one user, one parent entity, one UUID, or a
        date/date range. Results are a lazily paginated iterator, so iterating
        fetches additional pages on demand. To run a broader full-text or
        multi-filter query instead, use [`search`][albert.collections.activities.ActivityCollection.search].

        Parameters
        ----------
        type : ActivityType
            Which kind of scope ``id`` (and the date filters) refer to, for example
            a single entity, a user, or a date range. See [`ActivityType`][albert.resources.activities.ActivityType].
        id : str, optional
            The identifier of the scope selected by ``type`` (e.g. an entity or
            user ID). Not supported when ``type`` is ``ActivityType.DATE_RANGE``.
        start_date : date, optional
            Only include activities on or after this date.
        end_date : date, optional
            Only include activities on or before this date.
        operation_id : ActivityOperationId, optional
            Restrict to a specific logged operation. Applies only to recency
            support for SDS/label events. See
            [`ActivityOperationId`][albert.resources.activities.ActivityOperationId].
        action : ActivityAction, optional
            Whether to list read or write activities. Defaults to
            ``ActivityAction.WRITE``.
        order_by : OrderBy, optional
            Sort direction. Defaults to ``OrderBy.DESCENDING`` (newest first).
        start_key : str, optional
            Pagination key of the first record to evaluate; used to resume paging.
        max_items : int, optional
            Maximum number of records to return in total. If None, iterates over
            all available records.

        Returns
        -------
        Iterator[Activity]
            A lazily paginated iterator of activity records.

        !!! example
            ```python
            from albert.resources.activities import ActivityType

            for activity in client.activities.get_all(
                type=ActivityType.ENTITY_ID,
                id="INVA1",
                max_items=10,
            ):
                print(activity.name, activity.action)
            ```
        """
        params = {
            "type": type,
            "startKey": start_key,
            "id": id,
            "startDate": start_date,
            "endDate": end_date,
            "action": action,
            "orderBy": order_by,
            "operationId": operation_id,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Activity(**item) for item in items],
        )

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        sort_by: str | None = None,
        order_by: OrderBy | None = None,
        operation_id: list[str] | None = None,
        user: list[str] | None = None,
        user_class: list[str] | None = None,
        user_role: list[str] | None = None,
        object_id: list[str] | None = None,
        object_type: list[str] | None = None,
        object_class: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        uuid: list[str] | None = None,
        activity_id: list[str] | None = None,
        max_items: int | None = None,
    ) -> Iterator[ActivitySearchItem]:
        """Search activity records using full-text and filter criteria.

        Returns lightweight [`ActivitySearchItem`][albert.resources.activities.ActivitySearchItem]
        results and is the flexible way to query the audit trail across entities
        and users at once (e.g. everything a set of users did to a given object
        type in a date window). To page the raw feed for a single entity or user
        instead, use [`get_all`][albert.collections.activities.ActivityCollection.get_all]. Results are a lazily paginated iterator.

        Parameters
        ----------
        text : str, optional
            Free-text query matched across activity fields.
        sort_by : str, optional
            Field to sort results by. Supported value: ``"loggedAt"``.
        order_by : OrderBy, optional
            Sort direction, ascending or descending.
        operation_id : list[str], optional
            Filter by one or more operation IDs.
        user : list[str], optional
            Filter by one or more user IDs.
        user_class : list[str], optional
            Filter by one or more user class values.
        user_role : list[str], optional
            Filter by one or more user roles.
        object_id : list[str], optional
            Filter by one or more object (entity) IDs.
        object_type : list[str], optional
            Filter by one or more object types.
        object_class : list[str], optional
            Filter by one or more object class values.
        start_date : date, optional
            Start of the date range to filter results.
        end_date : date, optional
            End of the date range to filter results.
        uuid : list[str], optional
            Filter by one or more activity UUIDs.
        activity_id : list[str], optional
            Filter by one or more activity IDs.
        max_items : int, optional
            Maximum number of records to return in total. If None, iterates over
            all matches.

        Returns
        -------
        Iterator[ActivitySearchItem]
            A lazily paginated iterator of matching search results.

        !!! example
            ```python
            hits = client.activities.search(text="titanium dioxide", max_items=10)
            for hit in hits:
                print(hit.logged_at, hit.name)
            ```
        """
        params = {
            "text": text,
            "sortBy": sort_by,
            "orderBy": order_by,
            "operationId": operation_id,
            "user": user,
            "userClass": user_class,
            "userRole": user_role,
            "objectId": object_id,
            "objectType": object_type,
            "objectClass": object_class,
            "startDate": start_date,
            "endDate": end_date,
            "uuid": uuid,
            "activityId": activity_id,
        }
        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [ActivitySearchItem(**item) for item in items],
        )
