from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.exceptions import AlbertHTTPError
from albert.resources.custom_templates import CustomTemplate, CustomTemplateSearchItem


class CustomTemplatesCollection(BaseCollection):
    """CustomTemplatesCollection is a collection class for managing CustomTemplate entities in the Albert platform."""

    # _updatable_attributes = {"symbol", "synonyms", "category"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CustomTemplatesCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CustomTemplatesCollection._api_version}/customtemplates"

    def get_by_id(self, *, id) -> CustomTemplate:
        """Get a Custom Template by ID

        Parameters
        ----------
        id : str
            id of the custom template

        Returns
        -------
        CustomTemplate
            The CutomTemplate with the provided ID (or None if not found)
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return CustomTemplate(**response.json())

    def search(
        self,
        *,
        text: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Iterator[CustomTemplateSearchItem]:
        """Search for CustomTemplate matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str | None, optional
            The text to search for, by default None


        Yields
        ------
        Iterator[CustomTemplateSearchItem]
            An iterator of CustomTemplateSearchItem items matching the search criteria.
        """

        params = {"limit": limit, "offset": offset, "text": text}

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            deserialize=lambda items: [
                CustomTemplateSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
        )

    def get_all(
        self,
        *,
        text: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Iterator[CustomTemplate]:
        """Retrieve fully hydrated CustomTemplate entities with optional filters.

        This method returns complete entity data using `get_by_id`.
        Use :meth:`search` for faster retrieval when you only need lightweight, partial (unhydrated) entities.
        """

        for item in self.search(text=text, limit=limit, offset=offset):
            try:
                yield self.get_by_id(id=item.id)
            except AlbertHTTPError as e:
                logger.warning(f"Error hydrating custom template {id}: {e}")
