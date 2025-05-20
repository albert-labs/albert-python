from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.links import Link, LinkCategory
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


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

    def list(
        self,
        *,
        limit: int = 100,
        type: str | None = None,
        category: LinkCategory | None = None,
        id: str | None = None,
    ) -> Iterator[Link]:
        """
        Generates a list of link entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of link entities to return.
        type : str, optional
            The type of the link entities to return. Allowed values are `parent`, `child`, and `all`. If type is "all" then it will fetch both parent/child record for mentioned id.
        category : LinkCategory, optional
            The category of the link entities to return. Allowed values are `mention`, `linkedTask`, and `synthesis`.
        id : str
            The ID of the link entity to return. (Use with `type` parameter)

        Returns
        ------
        Iterator[Link]
            An iterator of Links.
        """
        params = {"limit": limit, "type": type, "category": category, "id": id}
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params=params,
            session=self.session,
            deserialize=lambda items: [Link(**item) for item in items],
        )

    def get_by_id(self, *, id: str) -> Link:
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

    def delete(self, *, id: str) -> None:
        """
        Deletes a link entity by its ID.

        Parameters
        ----------
        id : str
            The ID of the link entity to delete.
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)
