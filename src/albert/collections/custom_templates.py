from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
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
        max_items: int | None = None,
        offset: int | None = 0,
    ) -> Iterator[CustomTemplateSearchItem]:
        """
        Search for CustomTemplate matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str, optional
            Text to filter search results by.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            Offset to begin pagination at. Default is 0.

        Returns
        -------
        Iterator[CustomTemplateSearchItem]
            An iterator of CustomTemplateSearchItem items.
        """
        params = {
            "text": text,
            "offset": offset,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [
                CustomTemplateSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
        )

    def get_all(
        self,
        *,
        text: str | None = None,
        max_items: int | None = None,
        offset: int | None = 0,
    ) -> Iterator[CustomTemplate]:
        """
        Retrieve fully hydrated CustomTemplate entities with optional filters.

        This method returns complete entity data using `get_by_id`.
        Use :meth:`search` for faster retrieval when you only need lightweight, partial (unhydrated) entities.

        Parameters
        ----------
        text : str, optional
            Text filter for template name or content.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            Offset for search pagination.

        Returns
        -------
        Iterator[CustomTemplate]
            An iterator of CustomTemplate entities.
        """
        for item in self.search(text=text, max_items=max_items, offset=offset):
            try:
                yield self.get_by_id(id=item.id)
            except AlbertHTTPError as e:
                logger.warning(f"Error hydrating custom template {item.id}: {e}")
