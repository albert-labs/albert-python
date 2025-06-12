from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertHTTPError
from albert.resources.custom_templates import CustomTemplate, CustomTemplateSearchItem
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


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
        """Searches for custom templates matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) search results for performance.
        To retrieve fully detailed objects, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str | None, optional
            The text to search for, by default None


        Yields
        ------
        Iterator[CustomTemplate]
            An iterator of CustomTemplate items matching the search criteria.
        """

        params = {"limit": limit, "offset": offset, "text": text}

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            deserialize=lambda items: [CustomTemplateSearchItem.model_validate(x) for x in items],
        )

    def get_all(
        self,
        *,
        text: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Iterator[CustomTemplate]:
        """Retrieve fully hydrated CustomTemplate objects with optional filters.

        This method uses `get_by_id` to hydrate the results for convenience.
        Use :meth:`search` for better performance.
        """

        for item in self.search(text=text, limit=limit, offset=offset):
            try:
                yield self.get_by_id(id=item.id)
            except AlbertHTTPError as e:
                logger.warning(f"Error hydrating custom template {id}: {e}")
