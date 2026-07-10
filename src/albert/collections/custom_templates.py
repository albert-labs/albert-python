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
    """Manage Custom Templates in the Albert platform.

    A Custom Template is a reusable, pre-configured template that seeds a new
    entity with a standard setup. Depending on its
    :class:`~albert.resources.custom_templates.TemplateCategory`, a template can
    prefill a Property task, Batch task, Sheet, Notebook, or a general task with
    default fields such as project, location, assignee, inventories, workflow,
    priority, and metadata. Applying a template saves users from rebuilding the
    same configuration each time.

    Custom Template IDs use the ``CTP`` prefix. This is configuration/schema-level
    data.

    This collection is accessed as ``client.custom_templates``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for custom template requests.

    Methods
    -------
    create(custom_template) -> list[CustomTemplate]
        Register one or more custom templates (up to 10 at once).
    get_by_id(id) -> CustomTemplate
        Retrieve a single fully populated template by its Custom Template ID.
    search(...) -> Iterator[CustomTemplateSearchItem]
        Fast, lightweight search returning partial templates.
    get_all(...) -> Iterator[CustomTemplate]
        Iterate over fully populated templates matching optional filters.
    delete(id) -> None
        Delete a template by its Custom Template ID.
    update_acl(custom_template_id, acl_class=None, acls=None) -> CustomTemplate
        Replace a template's ACL class and/or access entries.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        template = client.custom_templates.get_by_id(id="CTP1")
        template.name
        # 'Standard Property Task'
        ```
    """

    # _updatable_attributes = {"symbol", "synonyms", "category"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a CustomTemplatesCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CustomTemplatesCollection._api_version}/customtemplates"

    @validate_call
    def create(
        self,
        *,
        custom_template: CustomTemplate | list[CustomTemplate],
    ) -> list[CustomTemplate]:
        """Register one or more custom templates.

        Up to 10 templates can be created in a single call. Each created template
        is re-fetched so the returned entities are fully populated.

        Parameters
        ----------
        custom_template : CustomTemplate or list[CustomTemplate]
            The template(s) to create. At least one and at most 10 are required.

        Returns
        -------
        list[CustomTemplate]
            The newly created templates, each populated with its assigned Custom
            Template ID.

        Raises
        ------
        ValueError
            If no templates are provided, or if more than 10 are provided.

        Examples
        --------
        !!! example
            ```python
            from albert import Albert
            from albert.resources.custom_templates import CustomTemplate
            client = Albert()
            template = CustomTemplate(name="Standard Property Task")
            created = client.custom_templates.create(custom_template=template)
            created[0].id
            # 'CTP1'
            ```
        """
        templates = ensure_list(custom_template) or []
        if len(templates) == 0:
            raise ValueError("At least one CustomTemplate must be provided.")
        if len(templates) > 10:
            raise ValueError("A maximum of 10 CustomTemplates can be created at once.")

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

        hydrated_templates = []
        for payload in created_payloads:
            template = CustomTemplate(**payload)
            hydrated = self.get_by_id(id=template.id)
            hydrated_templates.append(hydrated)

        return hydrated_templates

    def get_by_id(self, *, id: CustomTemplateId) -> CustomTemplate:
        """Retrieve a single, fully populated custom template by its ID.

        Parameters
        ----------
        id : CustomTemplateId
            The Custom Template ID (format ``CTP...``).

        Returns
        -------
        CustomTemplate
            The fully populated template.

        Examples
        --------
        !!! example
            ```python
            template = client.custom_templates.get_by_id(id="CTP1")
            template.name
            # 'Standard Property Task'
            ```
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
        status: Status | None = None,
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
        """Search for custom templates matching the given criteria.

        Returns lightweight, partially populated results and is the fastest way to
        look templates up. When you need complete templates, use :meth:`get_all`,
        or pass a resulting ID to :meth:`get_by_id`. Results are returned as a
        lazily paginated iterator.

        Parameters
        ----------
        text : str, optional
            Free-text search term.
        sort_by : str, optional
            Field to sort on.
        order_by : OrderBy, optional
            Sort direction for ``sort_by``.
        status : Status, optional
            Filter results by template status.
        created_by : str, optional
            Filter by creator ID.
        category : TemplateCategory or list[TemplateCategory], optional
            Filter by template category (or categories).
        created_by_name : str or list[str], optional
            Filter by creator display name(s).
        collaborator : str or list[str], optional
            Filter by collaborator ID(s).
        facet_text : str, optional
            Text to match within a facet.
        facet_field : str, optional
            The facet field to search inside.
        contains_field : str or list[str], optional
            Field(s) to apply a "contains" search to.
        contains_text : str or list[str], optional
            Text value(s) for the "contains" search.
        my_role : str or list[str], optional
            Restrict results to templates where the calling user holds the given
            role(s).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[CustomTemplateSearchItem]
            A lazily paginated iterator of partially populated search results.

        Examples
        --------
        !!! example
            ```python
            hits = client.custom_templates.search(text="stability", max_items=10)
            first = next(iter(hits))
            first.name
            # 'Stability Property Task'
            ```
        """

        params = {
            "text": text,
            "offset": offset,
            "sortBy": sort_by,
            "order": order_by,
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
        """Iterate over fully populated custom templates matching the filters.

        Returns complete ``CustomTemplate`` entities rather than lightweight
        search results, so prefer :meth:`search` when you only need names, IDs, or
        counts. Results are returned as a lazily paginated iterator.

        Parameters
        ----------
        name : str or list[str], optional
            Filter by template name(s).
        created_by : str, optional
            Filter by creator ID.
        category : TemplateCategory, optional
            Filter by template category.
        start_key : str, optional
            Provide the ``lastKey`` from a previous request to resume pagination.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[CustomTemplate]
            A lazily paginated iterator of fully populated templates.

        Examples
        --------
        !!! example
            ```python
            for template in client.custom_templates.get_all(max_items=25):
                print(template.id, template.name)
            ```
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
        """Delete a custom template by its ID.

        Parameters
        ----------
        id : CustomTemplateId
            The Custom Template ID to delete (format ``CTP...``).

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            client.custom_templates.delete(id="CTP1")
            ```
        """

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
        """Replace a template's ACL class and/or access entries.

        Updates who can access a template. Provide ``acl_class`` to change the
        ACL class, ``acls`` to replace the list of access entries, or both. When
        ``acls`` is given, the template's current entries are diffed against it so
        that entries are added, updated, or removed as needed.

        Parameters
        ----------
        custom_template_id : CustomTemplateId
            The Custom Template ID to update (format ``CTP...``).
        acl_class : str, optional
            The ACL class to set on the template.
        acls : list[ACL], optional
            The full set of ACL entries the template should end up with.

        Returns
        -------
        CustomTemplate
            The updated template.

        Raises
        ------
        ValueError
            If neither ``acl_class`` nor ``acls`` is provided.

        Examples
        --------
        !!! example
            ```python
            template = client.custom_templates.update_acl(
                custom_template_id="CTP1",
                acl_class="private",
            )
            ```
        """

        if acl_class is None and acls is None:
            raise ValueError("Provide an ACL class and/or ACL entries to update.")

        data = []
        current_template: CustomTemplate | None = None

        if acl_class is not None:
            acl_class_value = getattr(acl_class, "value", acl_class)
            data.append(
                {
                    "operation": PatchOperation.UPDATE.value,
                    "attribute": "class",
                    "newValue": acl_class_value,
                }
            )

        if acls is not None:
            current_template = self.get_by_id(id=custom_template_id)
            current_acl = (
                current_template.acl.fgclist
                if current_template.acl and current_template.acl.fgclist
                else []
            )
            current_entries = {
                entry.id: getattr(entry.fgc, "value", entry.fgc) for entry in current_acl
            }

            desired_entries = {entry.id: getattr(entry.fgc, "value", entry.fgc) for entry in acls}

            to_add = []
            to_delete = []
            to_update = []

            for entry_id, new_fgc in desired_entries.items():
                if entry_id not in current_entries:
                    payload = {"id": entry_id}
                    if new_fgc is not None:
                        payload["fgc"] = new_fgc
                    to_add.append(payload)
                else:
                    old_fgc = current_entries[entry_id]
                    if new_fgc is not None and old_fgc != new_fgc:
                        to_update.append(
                            {
                                "operation": PatchOperation.UPDATE.value,
                                "attribute": "fgc",
                                "id": entry_id,
                                "oldValue": old_fgc,
                                "newValue": new_fgc,
                            }
                        )

            for entry_id in current_entries:
                if entry_id not in desired_entries:
                    to_delete.append({"id": entry_id})

            if to_add:
                data.append(
                    {
                        "operation": PatchOperation.ADD.value,
                        "attribute": "ACL",
                        "newValue": to_add,
                    }
                )
            if to_delete:
                data.append(
                    {
                        "operation": PatchOperation.DELETE.value,
                        "attribute": "ACL",
                        "oldValue": to_delete,
                    }
                )
            data.extend(to_update)

        if not data:
            return current_template or self.get_by_id(id=custom_template_id)

        url = f"{self.base_path}/{custom_template_id}/acl"
        self.session.patch(url, json={"data": data})
        return self.get_by_id(id=custom_template_id)
