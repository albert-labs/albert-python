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
    """ActivityCollection manages Activity entities in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for activity API requests.

    Methods
    -------
    get_all(type, ...) -> Iterator[Activity]
        Lists activity entities with optional filters.
    search(...) -> Iterator[ActivitySearchItem]
        Searches activity records using full-text and filter criteria.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the ActivityCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
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
        """Lists Activity entities with optional filters

        Parameters
        ----------
        type : ActivityType
            The type of Id for which activities will be fetched.
        start_key : str | None, optional
            The primary key of the first item that this operation will evaluate.
        id : str | None, optional
            Unique id value for the selected type. This field is not supported for ActivityType.DATE_RANGE type, by default None
        start_date : date | None, optional
            The start date of the activities to list, by default None
        end_date : date | None, optional
            The end date of the activities to list, by default None
        action : ActivityAction | None, optional
            List activities with read/write operations, by default ActivityAction.WRITE
        order_by : OrderBy | None, optional
            The order by which to sort the results, by default OrderBy.DESCENDING
        operation_id : ActivityOperationId | None, optional
            OperationId of id for which activities will be fetched. Applicable only for recency support of sds/bl, by default ActivityOperationId.POST_SDS
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Activity]
            An iterator of Activity objects.
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
        """Searches activity records using full-text and filter criteria.

        Parameters
        ----------
        text : str, optional
            Free-text search across activity fields.
        sort_by : str, optional
            Field to sort results by. Valid value: ``loggedAt``.
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
            Filter by one or more object IDs.
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
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[ActivitySearchItem]
            An iterator of ActivitySearchItem objects matching the search criteria.
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
