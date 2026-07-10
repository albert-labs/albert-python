import logging
from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import TagId
from albert.core.utils import ensure_list
from albert.exceptions import AlbertException
from albert.resources.tags import Tag


class TagCollection(BaseCollection):
    """Manage Tags in the Albert platform.

    A Tag is a freeform text label used to categorize and connect entities across
    the platform, such as inventory items, companies, and tasks. Tags are shared:
    the same tag can be applied to many entities, which makes them useful for
    grouping and filtering related records.

    Because tags are identified by their text, the common pattern is to find an
    existing tag or create it on demand via :meth:`get_or_create`. Tags are
    referenced by their Tag ID (format ``TAG...``, e.g. ``"TAG1"``).

    This collection is accessed as ``client.tags``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for tag requests.

    Methods
    -------
    create(tag) -> Tag
        Create a new tag.
    get_or_create(tag) -> Tag
        Return the existing tag matching the name, or create it.
    get_by_id(id) -> Tag
        Retrieve a single tag by its Tag ID.
    get_by_ids(ids) -> list[Tag]
        Retrieve many tags by ID in batches.
    get_by_name(name, exact_match=True) -> Tag | None
        Retrieve a tag by name, or None if not found.
    get_all(...) -> Iterator[Tag]
        Iterate over tags with optional filters.
    rename(old_name, new_name) -> Tag
        Rename an existing tag.
    delete(id) -> None
        Delete a tag by its Tag ID.
    exists(tag, exact_match=True) -> bool
        Check whether a tag with the given name exists.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        tag = client.tags.get_or_create(tag="high-priority")
        print(tag.id, tag.tag)
        ```
    """

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
        self.base_path = f"/api/{TagCollection._api_version}/tags"

    def exists(self, *, tag: str, exact_match: bool = True) -> bool:
        """Check whether a tag with the given name exists.

        Parameters
        ----------
        tag : str
            The tag name to check.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        bool
            True if a matching tag exists, False otherwise.

        Examples
        --------
        !!! example
            ```python
            if client.tags.exists(tag="high-priority"):
                print("tag already defined")
            ```
        """

        return self.get_by_name(name=tag, exact_match=exact_match) is not None

    def create(self, *, tag: str | Tag) -> Tag:
        """Create a new tag.

        Parameters
        ----------
        tag : str or Tag
            The tag to create, given either as a plain name or a :class:`~albert.resources.tags.Tag`.

        Returns
        -------
        Tag
            The newly created tag, including its assigned Tag ID.

        Examples
        --------
        !!! example
            ```python
            tag = client.tags.create(tag="experimental")
            ```
        """
        if isinstance(tag, str):
            tag = Tag(tag=tag)

        payload = {"name": tag.tag}
        response = self.session.post(self.base_path, json=payload)
        tag = Tag(**response.json())
        return tag

    def get_or_create(self, *, tag: str | Tag) -> Tag:
        """Return the existing tag matching the given name, or create it.

        Looks for an existing tag with the same name (exact match). If one is
        found it is returned unchanged; otherwise a new tag is created. This is
        the recommended way to reference a tag, since tags are shared by name.

        Parameters
        ----------
        tag : str or Tag
            The tag to find or create, given either as a plain name or a
            :class:`~albert.resources.tags.Tag`.

        Returns
        -------
        Tag
            The existing or newly created tag.

        Examples
        --------
        !!! example
            ```python
            tag = client.tags.get_or_create(tag="high-priority")
            ```
        """
        if isinstance(tag, str):
            tag = Tag(tag=tag)
        found = self.get_by_name(name=tag.tag, exact_match=True)
        if found:
            logging.warning(f"Tag {found.tag} already exists with id {found.id}")
            return found
        return self.create(tag=tag)

    @validate_call
    def get_by_id(self, *, id: TagId) -> Tag:
        """Retrieve a single tag by its Tag ID.

        Parameters
        ----------
        id : TagId
            The Tag ID to retrieve (format ``TAG...``).

        Returns
        -------
        Tag
            The matching tag.

        Examples
        --------
        !!! example
            ```python
            tag = client.tags.get_by_id(id="TAG1")
            ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Tag(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[TagId]) -> list[Tag]:
        """Retrieve many tags by their IDs.

        IDs are fetched in batches, so arbitrarily long lists are supported.

        Parameters
        ----------
        ids : list[TagId]
            The Tag IDs to retrieve.

        Returns
        -------
        list[Tag]
            The matching tags. Tags not found are omitted.

        Examples
        --------
        !!! example
            ```python
            tags = client.tags.get_by_ids(ids=["TAG1", "TAG2"])
            ```
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            Tag(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()
        ]

    def get_by_name(self, *, name: str, exact_match: bool = True) -> Tag | None:
        """Retrieve a tag by its name.

        Parameters
        ----------
        name : str
            The tag name to retrieve.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        Tag or None
            The matching tag, or None if no tag with that name exists.

        Examples
        --------
        !!! example
            ```python
            tag = client.tags.get_by_name(name="high-priority")
            ```
        """
        found = self.get_all(name=name, exact_match=exact_match, max_items=1)
        return next(found, None)

    @validate_call
    def delete(self, *, id: TagId) -> None:
        """Delete a tag by its Tag ID.

        Parameters
        ----------
        id : TagId
            The Tag ID to delete.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            client.tags.delete(id="TAG1")
            ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def rename(self, *, old_name: str, new_name: str) -> Tag:
        """Rename an existing tag.

        The tag is looked up by its current name and updated in place, so every
        entity carrying the tag reflects the new name.

        Parameters
        ----------
        old_name : str
            The current name of the tag.
        new_name : str
            The new name to give the tag.

        Returns
        -------
        Tag
            The renamed tag.

        Raises
        ------
        AlbertException
            If no tag with ``old_name`` is found.

        Examples
        --------
        !!! example
            ```python
            tag = client.tags.rename(old_name="high-priority", new_name="urgent")
            ```
        """
        found_tag = self.get_by_name(name=old_name, exact_match=True)
        if not found_tag:
            msg = f'Tag "{old_name}" not found.'
            logger.error(msg)
            raise AlbertException(msg)
        tag_id = found_tag.id
        payload = [
            {
                "data": [
                    {
                        "operation": "update",
                        "attribute": "name",
                        "oldValue": old_name,
                        "newValue": new_name,
                    }
                ],
                "id": tag_id,
            }
        ]
        self.session.patch(self.base_path, json=payload)
        return self.get_by_id(id=tag_id)

    def get_all(
        self,
        *,
        order_by: OrderBy = OrderBy.DESCENDING,
        name: str | list[str] | None = None,
        exact_match: bool = True,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Tag]:
        """Iterate over tags, with optional filters.

        Results are fetched page by page as you iterate, so this scales to large
        result sets without loading everything at once.

        Parameters
        ----------
        order_by : OrderBy, optional
            Sort direction for results. Defaults to ``OrderBy.DESCENDING``.
        name : str or list[str], optional
            Filter tags by one or more names.
        exact_match : bool, optional
            Whether to match the name(s) exactly. Defaults to True.
        start_key : str, optional
            Pagination key to resume iteration from a previous position.
        max_items : int, optional
            Maximum number of tags to return in total. If None, iterates over all
            matching tags.

        Returns
        -------
        Iterator[Tag]
            An iterator over the matching tags.

        Examples
        --------
        !!! example
            ```python
            for tag in client.tags.get_all(max_items=100):
                print(tag.tag)
            ```
        """
        params = {
            "orderBy": order_by,
            "startKey": start_key,
        }

        if name:
            params["name"] = ensure_list(name)
            params["exactMatch"] = exact_match

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Tag(**item) for item in items],
        )
