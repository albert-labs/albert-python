from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.lists import ListItem, ListItemCategory
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class ListsCollection(BaseCollection):
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the TagCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ListsCollection._api_version}/lists"

    def list(
        self,
        *,
        limit: int = 100,
        names: list[str] | None = None,
        category: ListItemCategory | None = None,
        list_type: str | None = None,
        start_key: str | None = None,
    ) -> Iterator[ListItem]:
        """
        Generates a list of list entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of list entities to return.
        order_by : OrderBy, optional
            The order in which to return list entities.
        name : str, optional
            The name of the list entity to retrieve.
        exact_match : bool, optional
            Whether to perform an exact match on the list name.

        Returns
        ------
        Iterator[ListItem]
            An iterator of ListItems.
        """
        params = {
            "limit": limit,
            "startKey": start_key,
            "name": [names] if isinstance(names, str) else names,
            "category": category.value if isinstance(category, ListItemCategory) else category,
            "listType": list_type,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [ListItem(**item) for item in items],
        )

    def get_by_id(self, *, id: str) -> ListItem:
        """
        Retrieves a list entity by its ID.

        Parameters
        ----------
        id : str
            The ID of the list entity to retrieve.

        Returns
        -------
        List
            A list entity.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return ListItem(**response.json())

    def create(self, *, list_item: ListItem) -> ListItem:
        """
        Creates a list entity.

        Parameters
        ----------
        list_item : ListItem
            The list entity to create.

        Returns
        -------
        List
            The created list entity.
        """
        response = self.session.post(
            self.base_path,
            json=list_item.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ListItem(**response.json())

    def get_matching_item(self, *, name: str, list_type: str) -> ListItem | None:
        for list_item in self.list(names=[name], list_type=list_type):
            if list_item.name.lower() == name.lower():
                return list_item
        return None
