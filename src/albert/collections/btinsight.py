from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import BTInsightId
from albert.resources.btinsight import BTInsight, BTInsightCategory, BTInsightState


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

    @validate_call
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
            json=insight.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTInsight(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTInsightId) -> BTInsight:
        """
        Get a BTInsight by ID.

        Parameters
        ----------
        id : BTInsightId
            The Albert ID of the insight.

        Returns
        -------
        BTInsight
            The retrived BTInsight.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return BTInsight(**response.json())

    @validate_call
    def search(
        self,
        *,
        order_by: OrderBy | None = None,
        sort_by: str | None = None,
        text: str | None = None,
        name: str | list[str] | None = None,
        state: BTInsightState | list[BTInsightState] | None = None,
        category: BTInsightCategory | list[BTInsightCategory] | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[BTInsight]:
        """Search for items in the BTInsight collection.

        Parameters
        ----------
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
        offset : int | None, optional
            Item offset to begin search at, default None
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[BTInsight]
            An iterator of elements returned by the BTInsight search query.
        """
        params = {
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

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [BTInsight(**item) for item in items],
        )

    @validate_call
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
            generate_metadata_diff=False,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=insight.id)

    @validate_call
    def delete(self, *, id: BTInsightId) -> None:
        """Delete a BTInsight by ID.

        Parameters
        ----------
        id : str
            The ID of the BTInsight to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")
