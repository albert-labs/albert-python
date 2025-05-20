import json
import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.exceptions import AlbertException
from albert.resources.tags import Tag
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


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
    list(limit=50, order_by=OrderBy.DESCENDING, name=None, exact_match=True)
        Lists tag entities with optional filters.
    tag_exists(tag, exact_match=True) -> bool
        Checks if a tag exists by its name.
    create(tag) -> Tag
        Creates a new tag entity.
    get_by_id(tag_id) -> Tag
        Retrieves a tag by its ID.
    get_by_ids(tag_ids) -> list[Tag]
        Retrieve a list of tags by their IDs.
    get_by_tag(tag, exact_match=True) -> Tag
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

    def tag_exists(self, *, tag: str, exact_match: bool = True) -> bool:
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

        return self.get_by_tag(tag=tag, exact_match=exact_match) is not None

    def create(self, *, tag: str | Tag) -> Tag:
        """
        Creates a new tag entity if the given tag does not exist.

        Parameters
        ----------
        tag : Union[str, Tag]
            The tag name or Tag object to create.

        Returns
        -------
        Tag
            The created Tag object or the existing Tag object of it already exists.
        """
        if isinstance(tag, str):
            tag = Tag(tag=tag)
        hit = self.get_by_tag(tag=tag.tag, exact_match=True)
        if hit is not None:
            logging.warning(f"Tag {hit.tag} already exists with id {hit.id}")
            return hit
        payload = {"name": tag.tag}
        response = self.session.post(self.base_path, json=payload)
        tag = Tag(**response.json())
        return tag

    def get_by_id(self, *, id: str) -> Tag:
        """
        Get a tag by its ID.

        Parameters
        ----------
        id : str
            The ID of the tag to get.

        Returns
        -------
        Tag
            The Tag object.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Tag(**response.json())

    def get_by_ids(self, *, ids: list[str]) -> list[Tag]:
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            Tag(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()
        ]

    def get_by_tag(self, *, tag: str, exact_match: bool = True) -> Tag | None:
        """
        Retrieves a tag by its name of None if not found.

        Parameters
        ----------
        tag : str
            The name of the tag to retrieve.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        Tag
            The Tag object if found, None otherwise.
        """
        found = self.list(name=tag, exact_match=exact_match)
        return next(found, None)

    def delete(self, *, id: str) -> None:
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
        found_tag = self.get_by_tag(tag=old_name, exact_match=True)
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

    def list(
        self,
        *,
        limit: int = 50,
        order_by: OrderBy = OrderBy.DESCENDING,
        name: str | list[str] | None = None,
        exact_match: bool = True,
        start_key: str | None = None,
    ) -> Iterator[Tag]:
        """
        Lists Tag entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of tags to return, by default 50.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        name : Union[str, None], optional
            The name of the tag to filter by, by default None.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.
        start_key : Optional[str], optional
            The starting point for the next set of results, by default None.

        Returns
        -------
        Iterator[Tag]
            An iterator of Tag objects.
        """
        params = {"limit": limit, "orderBy": order_by.value, "startKey": start_key}
        if name:
            params["name"] = [name] if isinstance(name, str) else name
            params["exactMatch"] = json.dumps(exact_match)
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [Tag(**item) for item in items],
        )
