from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import LinkId
from albert.resources.links import Link, LinkCategory


class LinksCollection(BaseCollection):
    """Manage Links in the Albert platform.

    A Link represents a directional relationship between two entities in Albert:
    a parent and a child. Links capture cross-entity relationships such as a
    mention, a linked Task, a synthesis relationship, or a linked Inventory
    Item (see [`LinkCategory`][albert.resources.links.LinkCategory]). Links have no
    updatable fields; they are created, retrieved, and deleted.

    This collection is accessed as ``client.links``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for link requests.

    Methods
    -------
    create(links) -> list[Link]
        Create one or more links.
    get_all(...) -> Iterator[Link]
        Iterate over links, optionally filtered by entity, type, and category.
    get_by_id(id) -> Link
        Get a single link by its ID.
    delete(id) -> None
        Delete a link by its ID.

    Examples
    --------
    ```python
    from albert import Albert
    from albert.resources.links import LinkCategory
    client = Albert()
    links = client.links.get_all(id="INVA1", type="all", category=LinkCategory.MENTION)
    for link in links:
        print(link.parent.id, "->", link.child.id)
    ```
    """

    _api_version = "v3"
    _updatable_attributes = {}  # No updatable attributes for links

    def __init__(self, *, session: AlbertSession):
        """Initialize a LinksCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{LinksCollection._api_version}/links"

    def create(self, *, links: list[Link]) -> list[Link]:
        """Create one or more links.

        Parameters
        ----------
        links : list[Link]
            The links to create. Each requires a ``parent``, a ``child``, and a
            ``category``.

        Returns
        -------
        list[Link]
            The created links, each populated with its assigned Link ID.

        Examples
        --------
        ```python
        from albert.resources.links import Link, LinkCategory
        from albert.core.shared.models.base import EntityLink
        created = client.links.create(
            links=[
                Link(
                    parent=EntityLink(id="INVA1"),
                    child=EntityLink(id="INVA2"),
                    category=LinkCategory.LINKED_INVENTORY,
                )
            ]
        )
        created[0].id
        # 'LNK1'
        ```
        """
        response = self.session.post(
            self.base_path,
            json=[l.model_dump(by_alias=True, exclude_none=True, mode="json") for l in links],
        )
        return [Link(**l) for l in response.json()]

    def get_all(
        self,
        *,
        type: str | None = None,
        category: LinkCategory | None = None,
        id: str | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Link]:
        """Iterate over links, with optional filters.

        Parameters
        ----------
        type : str, optional
            Which side of the relationship to return relative to ``id``. Allowed
            values are ``"parent"``, ``"child"``, and ``"all"``. When ``"all"``,
            both parent and child records for the given ID are returned.
        category : LinkCategory, optional
            The link category to filter by (e.g. ``mention``, ``linkedTask``,
            ``synthesis``, ``linkedInventory``). See
            [`LinkCategory`][albert.resources.links.LinkCategory].
        id : str, optional
            The ID of the entity to fetch links for. Must include the full entity
            prefix (e.g. ``"INVA1"``).
        start_key : str, optional
            The pagination key to start from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Link]
            An iterator over the matching links.

        Examples
        --------
        ```python
        for link in client.links.get_all(id="INVA1", type="all"):
            print(link.category, link.parent.id, link.child.id)
        ```
        """
        params = {
            "type": type,
            "category": category,
            "id": id,
            "startKey": start_key,
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Link(**item) for item in items],
        )

    @validate_call
    def get_by_id(self, *, id: LinkId) -> Link:
        """Get a link by its ID.

        Parameters
        ----------
        id : LinkId
            The Link ID (format ``LNK...``).

        Returns
        -------
        Link
            The fully populated link.

        Examples
        --------
        ```python
        link = client.links.get_by_id(id="LNK1")
        link.category
        # <LinkCategory.MENTION: 'mention'>
        ```
        """
        path = f"{self.base_path}/{id}"
        response = self.session.get(path)
        return Link(**response.json())

    @validate_call
    def delete(self, *, id: LinkId) -> None:
        """Delete a link by its ID.

        Parameters
        ----------
        id : LinkId
            The Link ID to delete (format ``LNK...``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.links.delete(id="LNK1")
        ```
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)
