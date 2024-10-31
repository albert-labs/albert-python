import logging
from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.tags import Tag
from albert.session import AlbertSession
from albert.utils.exceptions import AlbertException


class TagCollection(BaseCollection):
    """
    TagCollection is a collection class for managing tag entities.

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

    def _list_generator(
        self,
        *,
        limit: int = 50,
        order_by: OrderBy = OrderBy.DESCENDING,
        name: str | list[str] = None,
        exact_match: bool = True,
        start_key: str | None = None,
    ) -> Generator[Tag, None, None]:
        """
        Lists tag entities with optional filters.

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
        Generator
            A generator of Tag objects.
        """
        params = {"limit": limit, "orderBy": order_by.value}
        if name:
            params["name"] = name if isinstance(name, list) else [name]
            params["exactMatch"] = str(exact_match).lower()
        if start_key:  # pragma: no cover
            params["startKey"] = start_key

        while True:
            response = self.session.get(self.base_path, params=params)
            tags_data = response.json().get("Items", [])
            if not tags_data or tags_data == []:
                break
            for t in tags_data:
                this_tag = Tag(**t)
                yield this_tag
            start_key = response.json().get("lastKey")
            if not start_key:
                break
            params["startKey"] = start_key

    def list(
        self,
        *,
        order_by: OrderBy = OrderBy.DESCENDING,
        name: str | list[str] = None,
        exact_match: bool = True,
    ) -> Iterator[Tag]:
        """
        Lists tag entities with optional filters.

        Parameters
        ----------
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        name : Union[str, None], optional
            The name of the tag to filter by, by default None.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        Generator
            A generator of Tag objects.
        """
        return self._list_generator(order_by=order_by, name=name, exact_match=exact_match)

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

    def get_by_id(self, *, tag_id: str) -> Tag | None:
        """
        Retrieves a tag by its ID of None if not found.

        Parameters
        ----------
        tag_id : str
            The ID of the tag to retrieve.

        Returns
        -------
        Tag
            The Tag object if found, None otherwise.
        """
        url = f"{self.base_path}/{tag_id}"
        response = self.session.get(url)
        tag = Tag(**response.json())
        return tag

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

    def delete(self, *, tag_id: str) -> None:
        """
        Deletes a tag by its ID.

        Parameters
        ----------
        tag_id : str
            The ID of the tag to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{tag_id}"
        self.session.delete(url)

    def rename(self, *, old_name: str, new_name: str) -> Tag | None:
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
        Optional[Tag]
            The renamed Tag object if successful, None otherwise.
        """
        found_tag = self.get_by_tag(tag=old_name, exact_match=True)

        if not found_tag:
            msg = f'Tag "{old_name}" not found.'
            logging.error(msg)
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
        updated_tag = self.get_by_id(tag_id=tag_id)
        return updated_tag
