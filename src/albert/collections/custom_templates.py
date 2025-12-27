from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.tags import TagCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode, Status
from albert.core.shared.identifiers import CustomTemplateId
from albert.core.shared.models.patch import PatchOperation
from albert.core.utils import ensure_list
from albert.resources.acls import ACL
from albert.resources.custom_templates import (
    CustomTemplate,
    CustomTemplateSearchItem,
    TemplateCategory,
)


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
        list[CustomTemplate]
            The created CustomTemplate entities.
        """
        templates = ensure_list(custom_templates) or []
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
        offset: int | None = 0,
        sort_by: str | None = None,
        order_by: OrderBy | None = None,
        status: Status | str | None = None,
        created_by: str | None = None,
        category: TemplateCategory | list[TemplateCategory] | None = None,
        created_by_name: str | list[str] | None = None,
        collaborator: str | list[str] | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: str | list[str] | None = None,
        contains_text: str | list[str] | None = None,
        my_role: str | list[str] | None = None,
        max_items: int | None = None,
    ) -> Iterator[CustomTemplateSearchItem]:
        """
        Search for CustomTemplate matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str, optional
            Free text search term.
        offset : int, optional
            Starting offset for pagination.
        sort_by : str, optional
            Field to sort on.
        order_by : OrderBy, optional
            Sort direction for `sort_by`.
        status : Status | str, optional
            Filter results by template status.
        created_by : str, optional
            Filter by creator id.
        category : TemplateCategory | list[TemplateCategory], optional
            Filter by template categories.
        created_by_name : str | list[str], optional
            Filter by creator display name(s).
        collaborator : str | list[str], optional
            Filter by collaborator ids.
        facet_text : str, optional
            Filter text within a facet.
        facet_field : str, optional
            Facet field to search inside.
        contains_field : str | list[str], optional
            Fields to apply contains search to.
        contains_text : str | list[str], optional
            Text values for contains search.
        my_role : str | list[str], optional
            Restrict templates to roles held by the calling user.
        max_items : int, optional
            Maximum number of items to yield client-side.

        Returns
        -------
        Iterator[CustomTemplateSearchItem]
            An iterator of CustomTemplateSearchItem items.
        """

        params = {
            "text": text,
            "offset": offset,
            "sortBy": sort_by,
            "order": order_by.value if order_by else None,
            "status": status,
            "createdBy": created_by,
            "category": ensure_list(category),
            "createdByName": ensure_list(created_by_name),
            "collaborator": ensure_list(collaborator),
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": ensure_list(contains_field),
            "containsText": ensure_list(contains_text),
            "myRole": ensure_list(my_role),
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
        name: str | list[str] | None = None,
        created_by: str | None = None,
        category: TemplateCategory | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[CustomTemplate]:
        """Iterate over CustomTemplate entities with optional filters.

        Parameters
        ----------
        name : str | list[str], optional
            Filter by template name(s).
        created_by : str, optional
            Filter by creator id.
        category : TemplateCategory, optional
            Filter by category.
        start_key : str, optional
            Provide the `lastKey` from a previous request to resume pagination.
        max_items : int, optional
            Maximum number of items to return.

        Returns
        -------
        Iterator[CustomTemplate]
            An iterator of CustomTemplates.
        """
        params = {
            "startKey": start_key,
            "createdBy": created_by,
            "category": category,
        }
        params["name"] = ensure_list(name)

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [CustomTemplate(**item) for item in items],
        )

    @validate_call
    def delete(self, *, id: CustomTemplateId) -> None:
        """Delete a custom template by id."""

        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def update_acl(
        self,
        *,
        custom_template_id: CustomTemplateId,
        acl_class: str | None = None,
        acls: list[ACL] | None = None,
    ) -> CustomTemplate:
        """Replace the template's ACL class and/or entries with the provided values and return the updated template."""

        if acl_class is None and not acls:
            raise ValueError("Provide an ACL class and/or ACL entries to update.")

        data = []

        if acl_class is not None:
            data.append(
                {
                    "operation": PatchOperation.UPDATE.value,
                    "attribute": "class",
                    "newValue": acl_class,
                }
            )

        if acls:
            entries = []
            for entry in acls:
                payload: dict[str, str] = {"id": entry.id}
                if entry.fgc is not None:
                    payload["fgc"] = getattr(entry.fgc, "value", entry.fgc)
                entries.append(payload)

            data.append(
                {
                    "operation": PatchOperation.UPDATE.value,
                    "attribute": "ACL",
                    "newValue": entries,
                }
            )

        url = f"{self.base_path}/{custom_template_id}/acl"
        self.session.patch(url, json={"data": data})
        return self.get_by_id(id=custom_template_id)
