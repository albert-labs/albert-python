import logging
from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import TagId
from albert.exceptions import AlbertException
from albert.resources.tags import Tag


class TagCollection(BaseCollection):
    """
    TagCollection is a collection class for managing Tag entities in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for tag API requests.

    Methods
    -------
    get_all(limit=50, order_by=OrderBy.DESCENDING, name=None, exact_match=True)
        Lists tag entities with optional filters.
    exists(tag, exact_match=True) -> bool
        Checks if a tag exists by its name.
    create(tag) -> Tag
        Creates a new tag entity.
    get_by_id(tag_id) -> Tag
        Retrieves a tag by its ID.
    get_by_ids(tag_ids) -> list[Tag]
        Retrieve a list of tags by their IDs.
    get_by_name(name, exact_match=True) -> Tag
        Retrieves a tag by its name.
    delete(tag_id) -> bool
        Deletes a tag by its ID.
    rename(old_name, new_name) -> Optional[Tag]
        Renames an existing tag entity.
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
        """
        Checks if a tag exists by its name.

        Parameters
        ----------
        tag : str
            The name of the tag to check.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        bool
            True if the tag exists, False otherwise.
        """

        return self.get_by_name(name=tag, exact_match=exact_match) is not None

    def create(self, *, tag: str | Tag) -> Tag:
        """
        Creates a new tag entity.

        Parameters
        ----------
        tag : Union[str, Tag]
            The tag name or Tag entity to create.

        Returns
        -------
        Tag
            The created Tag entity.
        """
        if isinstance(tag, str):
            tag = Tag(tag=tag)

        payload = {"name": tag.tag}
        response = self.session.post(self.base_path, json=payload)
        tag = Tag(**response.json())
        return tag

    def get_or_create(self, *, tag: str | Tag) -> Tag:
        """
        Retrieves a Tag by its name or creates it if it does not exist.

        Parameters
        ----------
        tag : Union[str, Tag]
            The tag name or Tag entity to retrieve or create.

        Returns
        -------
        Tag
            The existing or newly created Tag entity.
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
        """
        Get a tag by its ID.

        Parameters
        ----------
        id : str
            The ID of the tag to get.

        Returns
        -------
        Tag
            The Tag entity.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Tag(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[TagId]) -> list[Tag]:
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            Tag(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()
        ]

    def get_by_name(self, *, name: str, exact_match: bool = True) -> Tag | None:
        """
        Retrieves a tag by its name or None if not found.

        Parameters
        ----------
        name : str
            The name of the tag to retrieve.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        Tag
            The Tag entity if found, None otherwise.
        """
        found = self.get_all(name=name, exact_match=exact_match, max_items=1)
        return next(found, None)

    @validate_call
    def delete(self, *, id: TagId) -> None:
        """
        Deletes a tag by its ID.

        Parameters
        ----------
        id : str
            The ID of the tag to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def rename(self, *, old_name: str, new_name: str) -> Tag:
        """
        Renames an existing tag entity.

        Parameters
        ----------
        old_name : str
            The current name of the tag.
        new_name : str
            The new name of the tag.

        Returns
        -------
        Tag
            The renamed Tag.
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
        """
        Get all Tag entities with optional filters.

        Parameters
        ----------
        order_by : OrderBy, optional
            The order by which to sort the results. Default is DESCENDING.
        name : str or list[str], optional
            Filter tags by one or more names.
        exact_match : bool, optional
            Whether to match the name(s) exactly. Default is True.
        start_key : str, optional
            The pagination key to start from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Tag]
            An iterator of Tag entities matching the filters.
        """
        params = {
            "orderBy": order_by.value,
            "startKey": start_key,
        }

        if name:
            params["name"] = [name] if isinstance(name, str) else name
            params["exactMatch"] = exact_match

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Tag(**item) for item in items],
        )
