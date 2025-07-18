from collections.abc import Iterator
from datetime import date

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.activities import Activity, ActivityAction, ActivityOperationId, ActivityType
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class ActivityCollection(BaseCollection):
    """ActivityCollection is a collection class for managing viewing activities across Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name"}

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
        limit: int = 50,
        start_key: str | None = None,
        id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        operation_id: ActivityOperationId | None = None,
        action: ActivityAction | None = ActivityAction.WRITE,
        order_by: OrderBy | None = OrderBy.DESCENDING,
    ) -> Iterator[Activity]:
        """Lists Activity entities with optional filters

        Parameters
        ----------
        type : ActivityType
           The type of Id for which activities will be fetched.
        limit : int | None, optional
            The maximum number of activities to return, by default 50.
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

        Returns
        -------
        Iterator[Activity]
            An iterator of Activity objects.
        """
        params = {
            "type": type,
            "limit": limit,
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
            deserialize=lambda items: [Activity(**item) for item in items],
        )
