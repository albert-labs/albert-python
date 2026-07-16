from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.resources.lists import ListItem, ListItemCategory


class ListsCollection(BaseCollection):
    """Manage List Items in the Albert platform.

    A List Item is a single allowed value in a configurable list of options, such
    as the choices offered by a dropdown custom field or a fixed set of category
    values. Each item has a name, a category
    ([`ListItemCategory`][albert.resources.lists.ListItemCategory], e.g. ``userDefined`` or
    ``inventory``), and a ``list_type`` that ties it to the specific list it
    belongs to.

    List Items most often populate the lists defined by ``list``-type Custom
    Fields: a [`CustomField`][albert.resources.custom_fields.CustomField] with
    [`LIST`][albert.resources.custom_fields.FieldType.LIST] creates a new list
    whose ``list_type`` is typically the field's name, and each selectable option
    is a List Item with that same ``list_type``. To offer choices on such a field,
    add List Items here with a matching ``list_type`` (see
    [`CustomFieldCollection`][albert.collections.custom_fields.CustomFieldCollection]). Some
    ``list_type`` values are instead built-in platform lists (e.g. ``projectState``,
    ``casCategory``, ``inventoryFunction``).

    This collection is accessed as ``client.lists``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for list requests.

    Methods
    -------
    create(list_item) -> ListItem
        Create a new list item.
    get_by_id(id) -> ListItem
        Get a single list item by its ID.
    get_all(...) -> Iterator[ListItem]
        Iterate over list items with optional filters.
    get_matching_item(name, list_type) -> ListItem | None
        Find a list item by name within a given list type.
    update(list_item) -> ListItem
        Update an existing list item.
    delete(id) -> None
        Delete a list item by its ID.

    Examples
    --------
    ```python
    from albert import Albert
    from albert.resources.lists import ListItem
    client = Albert()

    # Populate the options for a dropdown custom field with stage-gate values
    stages = [
        "1. Discovery",
        "2. Concept Validation",
        "3. Proof of Concept",
        "4. Prototype Development",
    ]

    # Get the custom field this list is associated with
    stage_gate_field = client.custom_fields.get_by_id(id="CTF123")

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
        """Initialize a ListsCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ListsCollection._api_version}/lists"

    def get_all(
        self,
        *,
        names: list[str] | None = None,
        category: ListItemCategory | None = None,
        list_type: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[ListItem]:
        """Iterate over list items, with optional filters.

        Results are fetched page by page as you iterate, so this scales to large
        result sets without loading everything at once.

        Parameters
        ----------
        names : list[str], optional
            One or more item names to filter by.
        category : ListItemCategory, optional
            Restrict results to a single category (e.g. ``userDefined``, ``inventory``).
        list_type : str, optional
            Restrict results to a single list type (often a custom field name).
        order_by : OrderBy, optional
            Sort direction for results. Defaults to ``OrderBy.DESCENDING``.
        start_key : str, optional
            Pagination key to resume iteration from a previous position.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matching items.

        Returns
        -------
        Iterator[ListItem]
            An iterator over the matching list items.

        Examples
        --------
        ```python
        items = client.lists.get_all(list_type="Stage Gate", max_items=50)
        for item in items:
            print(item.name)
        ```
        """
        params = {
            "startKey": start_key,
            "name": names,
            "category": category,
            "listType": list_type,
            "orderBy": order_by,
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [ListItem(**item) for item in items],
        )

    def get_by_id(self, *, id: str) -> ListItem:
        """Get a single list item by its ID.

        Parameters
        ----------
        id : str
            The ID of the list item to retrieve.

        Returns
        -------
        ListItem
            The fully populated list item.

        Examples
        --------
        ```python
        item = client.lists.get_by_id(id="...")
        ```
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return ListItem(**response.json())

    def create(self, *, list_item: ListItem) -> ListItem:
        """Create a new list item.

        Parameters
        ----------
        list_item : ListItem
            The list item to create.

        Returns
        -------
        ListItem
            The newly created list item, including its assigned ID.

        Examples
        --------
        ```python
        from albert.resources.lists import ListItem, ListItemCategory
        item = client.lists.create(
            list_item=ListItem(name="In Progress", category=ListItemCategory.USER_DEFINED)
        )
        ```
        """
        response = self.session.post(
            self.base_path,
            json=list_item.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return ListItem(**response.json())

    def delete(self, *, id: str) -> None:
        """Delete a list item by its ID.

        Parameters
        ----------
        id : str
            The ID of the list item to delete.

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.lists.delete(id="...")
        ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def get_matching_item(self, *, name: str, list_type: str) -> ListItem | None:
        """Find a list item by name within a given list type.

        Performs a ranked search and returns the first item whose name matches
        ``name`` (case-insensitive) within the given list type.

        Parameters
        ----------
        name : str
            The name of the item to retrieve.
        list_type : str
            The list type to search within (often the name of a custom field).

        Returns
        -------
        ListItem or None
            The matching list item, or None if no item with that name and list
            type exists.

        Examples
        --------
        ```python
        item = client.lists.get_matching_item(name="In Progress", list_type="Stage Gate")
        ```
        """
        for list_item in self.get_all(names=[name], list_type=list_type, max_items=20):
            # since it's a ranked search, we only need to check the first few results
            if list_item.name.lower() == name.lower():
                return list_item
        return None

    def update(self, *, list_item=ListItem) -> ListItem:
        """Update an existing list item.

        Fetch a list item (e.g. via [`get_by_id`][albert.collections.lists.ListsCollection.get_by_id]), modify its name, then pass
        it here. The item is matched by its ``id``. If nothing changed, the
        existing item is returned unmodified.

        Parameters
        ----------
        list_item : ListItem
            The list item carrying the desired changes. Must have its ``id`` set.

        Returns
        -------
        ListItem
            The updated list item, re-fetched from Albert.

        Notes
        -----
        The following fields can be updated: ``name``.

        Examples
        --------
        ```python
        item = client.lists.get_by_id(id="...")
        item.name = "Completed"
        updated = client.lists.update(list_item=item)
        ```
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
