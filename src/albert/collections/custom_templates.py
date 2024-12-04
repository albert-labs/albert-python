from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertHTTPError
from albert.resources.custom_templates import CustomTemplate
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


class CustomTemplatesCollection(BaseCollection):
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

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        text: str | None = None,
    ) -> Iterator[CustomTemplate]:
        def deserialize(items: list[dict]) -> Iterator[CustomTemplate]:
            for item in items:
                id = item["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except AlbertHTTPError as e:
                    logger.warning(f"Error fetching custom template {id}: {e}")

        params = {"limit": limit, "offset": offset, "text": text}

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            deserialize=deserialize,
        )
