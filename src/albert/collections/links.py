from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import LinkId
from albert.resources.links import Link, LinkCategory


class LinksCollection(BaseCollection):
    """LinksCollection is a collection class for managing Link entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {}  # No updatable attributes for links

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the LinksCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{LinksCollection._api_version}/links"

    def create(self, *, links: list[Link]) -> list[Link]:
        """
        Creates a new link entity.

        Parameters
        ----------
        links : list[Link]
            List of Link entities to create.

        Returns
        -------
        Link
            The created link entity.
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
        """
        Get all link entities with optional filters.

        Parameters
        ----------
        type : str, optional
            The type of the link entities to return. Allowed values are `parent`, `child`, and `all`.
            If type is "all", both parent and child records for the given ID will be returned.
        category : LinkCategory, optional
            The category of the link entities to return. Allowed values are `mention`, `linkedTask`, and `synthesis`.
        id : str, optional
            The ID of the entity to fetch links for.
        start_key : str, optional
            The pagination key to start from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Link]
            An iterator of Link entities.
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
        """
        Retrieves a link entity by its ID.

        Parameters
        ----------
        id : str
            The ID of the link entity to retrieve.

        Returns
        -------
        Link
            The retrieved link entity.
        """
        path = f"{self.base_path}/{id}"
        response = self.session.get(path)
        return Link(**response.json())

    @validate_call
    def delete(self, *, id: LinkId) -> None:
        """
        Deletes a link entity by its ID.

        Parameters
        ----------
        id : str
            The ID of the link entity to delete.
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)
