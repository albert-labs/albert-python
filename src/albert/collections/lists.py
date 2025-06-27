from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.lists import ListItem, ListItemCategory
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class ListsCollection(BaseCollection):
    """ListsCollection is a collection class for managing ListItem entities in the Albert platform.

    Example
    -------

    ```python
    stages = [
        "1. Discovery",
        "2. Concept Validation",
        "3. Proof of Concept",
        "4. Prototype Development",
        "5. Preliminary Evaluation",
        "6. Feasibility Study",
        "7. Optimization",
        "8. Scale-Up",
        "9. Regulatory Assessment",
    ]
    # Initialize the Albert client
    client = Albert()

    # Get the custom field this list is associated with
    stage_gate_field = client.custom_fields.get_by_id(id="CF123")

    # Create the list items
    for s in stages:
        item = ListItem(
            name=s,
            category=stage_gate_field.category,
            list_type=stage_gate_field.name,
        )

        client.lists.create(list_item=item)
    ```
    """

    _updatable_attributes = {"name"}
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
        names : list[str], optional
            A list of names of the list entity to retrieve.
        category : ListItemCategory, optional
            The category of the list entity to retrieve.
        list_type : str, optional
            The type of list entity to retrieve.
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
            mode=PaginationMode.OFFSET,
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

    def delete(self, *, id: str) -> None:
        """
        Delete a lists entry item by its ID.

        Parameters
        ----------
        id : str
            The ID of the lists item.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def get_matching_item(self, *, name: str, list_type: str) -> ListItem | None:
        """Get a list item by name and list type.

        Parameters
        ----------
        name : str
            The name of it item to retrieve.
        list_type : str
            The type of list (can be the name of the custom field)

        Returns
        -------
        ListItem | None
            A list item with the provided name and list type, or None if not found.
        """
        for list_item in self.list(names=[name], list_type=list_type):
            if list_item.name.lower() == name.lower():
                return list_item
        return None

    def update(self, *, list_item=ListItem) -> ListItem:
        """Update a list item.

        Parameters
        ----------
        list_item : ListItem
            The list item to update.

        Returns
        -------
        ListItem
            The updated list item.
        """
        existing = self.get_by_id(id=list_item.id)
        patches = self._generate_patch_payload(
            existing=existing, updated=list_item, generate_metadata_diff=False
        )
        if len(patches.data) == 0:
            return existing
        self.session.patch(
            url=f"{self.base_path}/{list_item.id}",
            json=patches.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return self.get_by_id(id=list_item.id)
