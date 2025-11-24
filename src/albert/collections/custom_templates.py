from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.tags import TagCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import CustomTemplateId
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

    @validate_call
    def create(
        self,
        *,
        custom_templates: CustomTemplate | list[CustomTemplate],
    ) -> list[CustomTemplate]:
        """
        Creates one or more custom templates.

        Parameters
        ----------
        custom_templates : CustomTemplate | list[CustomTemplate]
            The template entities to create.

        Returns
        -------
        list[CustomTemplate] | dict[str, Any]
            The created templates. Returns the raw API response when partial success data is provided.
        """
        templates = custom_templates if isinstance(custom_templates, list) else [custom_templates]
        if len(templates) == 0:
            raise ValueError("At least one CustomTemplate must be provided.")

        payload = [
            template.model_dump(
                mode="json",
                by_alias=True,
                exclude_none=True,
                exclude_unset=True,
            )
            for template in templates
        ]
        response = self.session.post(url=self.base_path, json=payload)
        response_data = response.json()
        created_payloads = (
            (response_data or {}).get("CreatedItems")
            if response.status_code == 206
            else response_data
        ) or []

        tag_collection = TagCollection(session=self.session)

        def resolve_tag(tag_id: str | None) -> dict[str, str] | None:
            if not tag_id:
                return None
            tag = tag_collection.get_by_id(id=tag_id)
            return {"albertId": tag.id or tag_id, "name": tag.tag}

        def populate_tag_names(section: dict | None) -> None:
            if not isinstance(section, dict):
                return
            tags = section.get("Tags")
            if not tags:
                return
            resolved_tags = []
            for tag in tags:
                if isinstance(tag, dict):
                    tag_id = tag.get("id") or tag.get("albertId")
                elif isinstance(tag, str):
                    tag_id = tag
                else:
                    tag_id = None

                resolved_tag = resolve_tag(tag_id)
                if resolved_tag:
                    resolved_tags.append(resolved_tag)
            section["Tags"] = resolved_tags

        for payload in created_payloads:
            if not isinstance(payload, dict):
                continue
            populate_tag_names(payload.get("Data"))

        if response.status_code == 206:
            failed_items = response_data.get("FailedItems") or []
            if failed_items:
                error_messages = []
                for failed in failed_items:
                    errors = failed.get("errors") or []
                    if errors:
                        error_messages.extend(err.get("msg", "Unknown error") for err in errors)
                joined = " | ".join(error_messages) if error_messages else "Unknown error"
                logger.warning(
                    "Custom template creation partially succeeded. Errors: %s",
                    joined,
                )

        return [CustomTemplate(**item) for item in created_payloads]

    def get_by_id(self, *, id: CustomTemplateId) -> CustomTemplate:
        """Get a Custom Template by ID

        Parameters
        ----------
        id : str
            id of the custom template

        Returns
        -------
        CustomTemplate
            The CutomTemplate with the provided ID
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

