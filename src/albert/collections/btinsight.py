from albert.collections.base import BaseCollection, OrderBy
from albert.resources.btinsight import BTInsight, BTInsightCategory, BTInsightState
from albert.session import AlbertSession
from albert.utils.exceptions import InternalServerError
from albert.utils.logging import logger
from albert.utils.pagination import SearchPaginator


class BTInsightCollection(BaseCollection):
    """
    BTInsightCollection is a collection class for managing Breakthrough insight entities.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base path for BTInsight API requests.
    """

    _api_version = "v3"
    # name, state, Metadata, outputKey, startTime, endTime, totalTime, RawPayload, contentEdited, payloadType, Registry'
    _updatable_attributes = {
        "name",
        "state",
        "metadata",
        "output_key",
        "start_time",
        "end_time",
        "total_time",
        "raw_payload",
        "content_edited",
        "payload_type",
        "registry",
    }

    def __init__(self, *, session: AlbertSession):
        """
        Initialize the BTInsightCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{BTInsightCollection._api_version}/btinsight"

    def create(self, *, insight: BTInsight) -> BTInsight:
        """
        Create a new BTInsight.

        Parameters
        ----------
        insight : BTInsight
            The BTInsight record to create.

        Returns
        -------
        BTInsight
            The created BTInsight.
        """
        response = self.session.post(
            self.base_path,
            json=insight.model_dump(by_alias=True, exclude_none=True),
        )
        return BTInsight(**response.json())

    def get_by_id(self, *, id: str) -> BTInsight:
        """
        Get a BTInsight by ID.

        Parameters
        ----------
        id : str
            The Albert ID of the insight.

        Returns
        -------
        BTInsight
            The retrived BTInsight.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return BTInsight(**response.json())

    def list(
        self,
        *,
        limit: int = 100,
        offset: int | None = None,
        order_by: OrderBy | None = None,
        sort_by: str | None = None,
        text: str | None = None,
        name: str | list[str] | None = None,
        state: BTInsightState | list[BTInsightState] | None = None,
        category: BTInsightCategory | list[BTInsightCategory] | None = None,
    ) -> SearchPaginator[BTInsight | None]:
        """List items in the BTInsight collection.

        Parameters
        ----------
        limit : int, optional
            Number of items to return per page, default 100
        offset : int | None, optional
            Item offset to begin search at, default None
        order_by : OrderBy | None, optional
            Asc/desc ordering, default None
        sort_by : str | None
            Sort field, default None
        text : str | None
            Text field in search query, default None
        name : str | list[str] | None
            BTInsight name search filter, default None
        state : BTInsightState | list[BTInsightState] | None
            BTInsight state search filter, default None
        category : BTInsightCategory | list[BTInsightCategory] | None
            BTInsight category search filter, default None

        Returns
        -------
        SearchPaginator[BTInsight | None]
            An iterator over the BTInsight search query.
        """

        def deserialize(data: dict) -> BTInsight | None:
            id = data["albertId"]
            try:
                return self.get_by_id(id=id)
            except InternalServerError as e:
                logger.warning(f"Error fetching insight '{id}': {e}")
                return None

        params = {
            "limit": limit,
            "offset": offset,
            "order": OrderBy(order_by).value if order_by else None,
            "sortBy": sort_by,
            "text": text,
            "name": name,
        }
        if state:
            state = state if isinstance(state, list) else [state]
            params["state"] = [BTInsightState(x).value for x in state]
        if category:
            category = category if isinstance(category, list) else [category]
            params["category"] = [BTInsightCategory(x).value for x in category]

        return SearchPaginator(
            path=f"{self.base_path}/search",
            session=self.session,
            deserialize=deserialize,
            params=params,
        )

    def update(self, *, insight: BTInsight) -> BTInsight:
        """Update a BTInsight.

        Parameters
        ----------
        insight : BTInsight
            The BTInsight to update.

        Returns
        -------
        BTInsight
            The updated BTInsight.
        """
        path = f"{self.base_path}/{insight.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=insight.id),
            updated=insight,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=insight.id)

    def delete(self, *, id: str) -> bool:
        """Delete a BTInsight by ID.

        Parameters
        ----------
        id : str
            The ID of the BTInsight to delete.

        Returns
        -------
        bool
            If the BTInsight was deleted.
        """
        self.session.delete(f"{self.base_path}/{id}")
        return True
