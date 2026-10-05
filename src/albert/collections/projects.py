from collections.abc import Iterable, Iterator
from contextlib import suppress
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.personalization import PersonalizationCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator, MappedPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import (
    InventoryId,
    ProjectId,
    SearchProjectId,
    WorksheetId,
)
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.core.utils import ensure_list
from albert.exceptions import AlbertHTTPError, BadRequestError, NotFoundError
from albert.resources.acls import ACL
from albert.resources.projects import (
    DocumentSearchItem,
    Project,
    ProjectSearchItem,
    ReferenceFormula,
    ReferenceFormulaType,
)
from albert.utils.projects import (
    in_project_reference_formula_payload,
    linked_reference_formula_payload,
    reference_formula_path,
    reference_formula_payload,
)
from albert.resources.personalization import Personalization, PersonalizationCategory
from albert.resources.projects import DocumentSearchItem, Project, ProjectSearchItem


class ProjectCollection(BaseCollection):
    """Manage Projects in the Albert platform.

    A Project is the top-level container for a piece of R&D work. It groups the
    formulations designed for that work, the Project's Worksheet (1:1 with the
    project), the Tasks run against it, and the inventory it references. Projects
    are the entry point most workflows start from: you create a project, then
    build formulas and run tasks inside it.

    Every project is identified by a Project ID (format ``PRO...``, e.g.
    ``"PRO123"``). A project always has a ``description`` (which doubles as its
    display name) and a [`ProjectClass`][albert.resources.projects.ProjectClass]
    controlling its access level (private, shared, or confidential).

    This collection is accessed as ``client.projects``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.projects import Project
        client = Albert()
        project = client.projects.create(
            project=Project(description="Weatherproof Coatings 2026")
        )
        print(project.id)
        # 'PRO123'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for project requests.

    Methods
    -------
    create(project) -> Project
        Create a new project.
    get_by_id(id) -> Project
        Get a single project by its ID.
    update(project) -> Project
        Update an existing project.
    delete(id) -> None
        Delete a project by its ID.
    reactivate(id) -> Project
        Reactivate a soft-deleted project by its ID.
    search(...) -> Iterator[ProjectSearchItem]
        Fast, lightweight search returning partial projects (best for lookups).
    get_all(...) -> Iterator[Project]
        Same filters as search, but returns fully populated projects (slower).
    document_search(...) -> Iterator[DocumentSearchItem]
        Search documents (attachments) linked to a project.
    set_reference_formula(...) -> ReferenceFormula
        This promotes a project's formula to a designated reference type that can be easily referenced within a project. Reference formulas can be of any type defined in [`ReferenceFormulaType`][albert.resources.projects.ReferenceFormulaType]. The [`OTHER`][albert.resources.projects.ReferenceFormulaType.OTHER] reference type allows for custom naming of the type.
    link_reference_formula(...) -> ReferenceFormula
        Link a reference formula from another project.
    get_all_reference_formulas(...) -> Iterator[ReferenceFormula]
        Get all reference formula designations, with optional filters.
    update_reference_formula_type(...) -> ReferenceFormula
        Update the type designation of an existing reference formula.
    delete_reference_formula(...) -> None
        Delete a reference formula designation from a project.
    star(id) -> Project
        Star (pin, favorite) a project for the current user.
    unstar(id) -> None
        Remove a project from the current user's starred (pinned, favorited) projects.
    get_starred(...) -> Iterator[Project]
        Get the current user's starred (pinned, favorited) projects.
    """

    _api_version = "v3"
    _updatable_attributes = {"description", "grid", "metadata", "state"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a ProjectCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ProjectCollection._api_version}/projects"

    def create(self, *, project: Project) -> Project:
        """Create a new project.

        Use this to register a new R&D container. Only ``description`` is
        required; it doubles as the project's display name. Optionally set
        ``locations``, ``project_class`` (defaults to private), ``metadata``, and
        other fields on the [`Project`][albert.resources.projects.Project] first.

        !!! example
            ```python
            from albert.resources.projects import Project
            project = client.projects.create(
                project=Project(description="Weatherproof Coatings 2026")
            )
            project.id
            # 'PRO123'
            ```

        Parameters
        ----------
        project : Project
            The project to create.

        Returns
        -------
        Project
            The newly created project, populated with its assigned Project ID.
        """
        response = self.session.post(
            self.base_path, json=project.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        return Project(**response.json(), session=self.session)

    @validate_call
    def get_by_id(self, *, id: ProjectId) -> Project:
        """Get a single project by its ID.

        To find projects without knowing their IDs, use [`search`][albert.collections.projects.ProjectCollection.search] or
        [`get_all`][albert.collections.projects.ProjectCollection.get_all].

        !!! example
            ```python
            project = client.projects.get_by_id(id="PRO123")
            project.description
            # 'Weatherproof Coatings 2026'
            ```

        Parameters
        ----------
        id : ProjectId
            The Project ID (format ``PRO...``, e.g. ``"PRO123"``).

        Returns
        -------
        Project
            The fully populated project.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)

        return Project(**response.json(), session=self.session)

    def update(self, *, project: Project) -> Project:
        """Update an existing project.

        Retrieve the project (e.g. with
        [`get_by_id`][albert.collections.projects.ProjectCollection.get_by_id]), modify the updatable fields, then pass it
        here. Only the fields listed in Notes are applied.

        !!! example
            ```python
            project = client.projects.get_by_id(id="PRO123")
            project.description = "Weatherproof Coatings 2026 (rev B)"
            updated = client.projects.update(project=project)
            ```

        Parameters
        ----------
        project : Project
            The project carrying the desired changes. Its ``id`` identifies which
            project to update.

        Returns
        -------
        Project
            The updated project.

        Notes
        -----
        The following fields can be updated: ``description``, ``grid``,
        ``metadata``, ``state``, ``acl``.
        """
        existing_project = self.get_by_id(id=project.id)
        patch_data = self._generate_patch_payload(existing=existing_project, updated=project)
        url = f"{self.base_path}/{project.id}"
        patch_payload = patch_data.model_dump(mode="json", by_alias=True)

        acl_operations: list[dict[str, Any]] = []
        if "acl" in project.model_fields_set:
            acl_operations = self._generate_acl_patch_operations(
                existing=existing_project.acl,
                updated=project.acl,
            )

        if patch_payload["data"]:
            self.session.patch(url, json=patch_payload)

        if acl_operations:
            self.session.patch(f"{url}/acl", json={"data": acl_operations})

        if not patch_payload["data"] and not acl_operations:
            return existing_project

        return self.get_by_id(id=project.id)

    def _generate_acl_patch_operations(
        self,
        *,
        existing: list[ACL] | None,
        updated: list[ACL] | None,
    ) -> list[dict[str, Any]]:
        """Build PATCH operations for project ACL changes."""
        existing_entries = existing or []
        updated_entries = updated or []
        existing_ids = [entry.id for entry in existing_entries]
        updated_ids = [entry.id for entry in updated_entries]
        to_add = set(updated_ids) - set(existing_ids)
        to_delete = set(existing_ids) - set(updated_ids)
        to_update = set(existing_ids).intersection(updated_ids)

        operations: list[dict[str, Any]] = []

        if to_add:
            operations.append(
                {
                    "attribute": "ACL",
                    "operation": "add",
                    "newValue": [
                        entry.model_dump(by_alias=True, exclude_none=True)
                        for entry in updated_entries
                        if entry.id in to_add
                    ],
                }
            )

        if to_delete:
            operations.append(
                {
                    "attribute": "ACL",
                    "operation": "delete",
                    "oldValue": [{"id": entry_id} for entry_id in to_delete],
                }
            )

        for entry_id in to_update:
            existing_fgc = next(entry.fgc for entry in existing_entries if entry.id == entry_id)
            updated_fgc = next(entry.fgc for entry in updated_entries if entry.id == entry_id)
            if existing_fgc != updated_fgc:
                operations.append(
                    {
                        "attribute": "fgc",
                        "id": entry_id,
                        "operation": "update",
                        "oldValue": existing_fgc.value if existing_fgc is not None else None,
                        "newValue": updated_fgc.value if updated_fgc is not None else None,
                    }
                )

        return operations

    @validate_call
    def delete(self, *, id: ProjectId) -> None:
        """Delete a project by its ID.

        !!! example
            ```python
            client.projects.delete(id="PRO123")
            ```

        Parameters
        ----------
        id : ProjectId
            The Project ID (format ``PRO...``, e.g. ``"PRO123"``).

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def reactivate(self, *, id: ProjectId) -> Project:
        """Reactivate a soft-deleted project by its ID.

        Restores a project previously deleted with
        [`delete`][albert.collections.projects.ProjectCollection.delete]. The project's
        tasks and worksheets are restored with it.

        !!! example
            ```python
            project = client.projects.reactivate(id="PRO123")
            project.status
            # 'active'
            ```

        Parameters
        ----------
        id : ProjectId
            The Project ID (format ``PRO...``, e.g. ``"PRO123"``).

        Returns
        -------
        Project
            The reactivated project.
        """
        url = f"{self.base_path}/{id}/reactivate"
        self.session.patch(url)
        return self.get_by_id(id=id)

    @validate_call
    def star(self, *, id: ProjectId) -> Project:
        """Star (pin, favorite) a project for the current user.

        Starring a project adds it to the current user's starred projects list.
        If the project is already starred, this method leaves it starred.

        !!! example
            ```python
            project = client.projects.star(id="PRO123")
            project.description
            # 'Weatherproof Coatings 2026'
            ```

        Parameters
        ----------
        id : ProjectId
            The Project ID (format ``PRO...``, e.g. ``"PRO123"``).

        Returns
        -------
        Project
            The fully populated starred Project.
        """
        project = self.get_by_id(id=id)
        record = Personalization(
            category=PersonalizationCategory.STARRED_PROJECTS,
            saved_id=project.id,
            saved_name=project.description,
        )
        try:
            PersonalizationCollection(session=self.session).create(personalization=record)
        except BadRequestError as e:
            if not self._is_already_starred_error(e):
                raise
        return project

    @validate_call
    def unstar(self, *, id: ProjectId) -> None:
        """Remove a project from the current user's starred (pinned, favorited) projects.

        If the project is not starred, this method does nothing.

        !!! example
            ```python
            client.projects.unstar(id="PRO123")
            ```

        Parameters
        ----------
        id : ProjectId
            The Project ID (format ``PRO...``, e.g. ``"PRO123"``).

        Returns
        -------
        None
        """
        personalizations = PersonalizationCollection(session=self.session)
        records = personalizations.get_all(category=PersonalizationCategory.STARRED_PROJECTS)
        for record_id in self._starred_record_ids(records=records, project_id=id):
            with suppress(NotFoundError):
                personalizations.delete(id=record_id)

    @validate_call
    def get_starred(self, *, max_items: int | None = None) -> Iterator[Project]:
        """Get the current user's starred (pinned, favorited) projects.

        Yields fully populated [`Project`][albert.resources.projects.Project] entities
        belonging to the current user's starred list.

        !!! example
            ```python
            for project in client.projects.get_starred():
                print(project.id, project.description)
            # PRO123 Weatherproof Coatings 2026
            ```

        Parameters
        ----------
        max_items : int, optional
            Maximum number of projects to return in total. If None, returns all
            starred projects.

        Returns
        -------
        Iterator[Project]
            An iterator of fully populated Project entities.
        """

        def _hydrate(record: Personalization) -> Project | None:
            if not record.saved_id:
                return None
            try:
                return self.get_by_id(id=record.saved_id)
            except AlbertHTTPError as e:
                logger.warning(f"Error fetching starred project {record.saved_id}: {e}")
                return None

        records = PersonalizationCollection(session=self.session).get_all(
            category=PersonalizationCategory.STARRED_PROJECTS, max_items=max_items
        )
        return MappedPaginator(records, _hydrate)

    @staticmethod
    def _starred_record_ids(*, records: Iterable[Personalization], project_id: str) -> list[str]:
        """Return the personalization record IDs that star ``project_id``."""
        target = project_id.upper()
        return [
            record.id
            for record in records
            if record.id and (record.saved_id or "").upper() == target
        ]

    @staticmethod
    def _is_already_starred_error(error: BadRequestError) -> bool:
        """Return True if ``error`` reports that the project is already starred."""
        try:
            payload = error.response.json()
        except ValueError:
            return False
        errors = payload.get("errors") if isinstance(payload, dict) else None
        return any(
            isinstance(item, dict) and "savedId already exist" in str(item.get("msg", ""))
            for item in errors or []
        )

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        status: list[str] | None = None,
        market_segment: list[str] | None = None,
        application: list[str] | None = None,
        technology: list[str] | None = None,
        created_by: list[str] | None = None,
        location: list[str] | None = None,
        program: list[str] | None = None,
        technical_lead: list[str] | None = None,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        updated_by: str | list[str] | None = None,
        from_updated_at: str | None = None,
        to_updated_at: str | None = None,
        facet_field: str | None = None,
        facet_text: str | None = None,
        contains_field: list[str] | None = None,
        contains_text: list[str] | None = None,
        linked_to: str | None = None,
        my_project: bool | None = None,
        my_role: list[str] | None = None,
        metadata_filters: dict[str, Any] | None = None,
        additional_field: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
        formula_access: list[str] | None = None,
        linked_to_grid: str | None = None,
        source_field: list[str] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[ProjectSearchItem]:
        """Search for projects matching the given filters.

        This is the fast way to find projects: it returns lightweight, partial
        (unhydrated) [`ProjectSearchItem`][albert.resources.projects.ProjectSearchItem] results
        and is best for lookups, counts, and pulling IDs. To retrieve fully
        detailed [`Project`][albert.resources.projects.Project] entities, use
        [`get_all`][albert.collections.projects.ProjectCollection.get_all] instead (slower, one full fetch per result).

        All filters are optional; with no arguments this iterates over all
        projects you can access.

        !!! example
            ```python
            # Keep the paginator reference; do not wrap in list() if you need
            # completeness signals after iteration.
            hits = client.projects.search(text="coatings", max_items=25)
            for hit in hits:
                print(hit.id, hit.description)
            if hits.has_more:
                print(f"Stopped early; ~{hits.total} total matches")
            ```

        Parameters
        ----------
        text : str, optional
            Full-text search query.
        status : list[str], optional
            Filter by project statuses.
        market_segment : list[str], optional
            Filter by market segment.
        application : list[str], optional
            Filter by application.
        technology : list[str], optional
            Filter by technology tags.
        created_by : list[str], optional
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``).
        location : list[str], optional
            Filter by location(s).
        program : list[str], optional
            Filter by project program (custom field).
        technical_lead : list[str], optional
            Filter by technical lead (custom field).
        from_created_at : str, optional
            Only include projects created on or after this date, formatted as
            ``YYYY-MM-DD``.
        to_created_at : str, optional
            Only include projects created on or before this date, formatted as
            ``YYYY-MM-DD``.
        updated_by : str or list[str], optional
            Filter by user(s) who last updated the project. Accepts UserId(s)
            only (e.g. ``"USR4227"``), not display names.
        from_updated_at : str, optional
            Only include projects updated on or after this date (ISO 8601).
        to_updated_at : str, optional
            Only include projects updated on or before this date (ISO 8601).
        facet_field : str, optional
            Facet field to filter on.
        facet_text : str, optional
            Facet text to search for.
        contains_field : list[str], optional
            Fields to search inside.
        contains_text : list[str], optional
            Values to search for within the `contains_field`.
        linked_to : str, optional
            Entity ID the project is linked to.
        my_project : bool, optional
            If True, return only projects owned by current user.
        my_role : list[str], optional
            User roles to filter by.
        metadata_filters : dict[str, Any], optional
            Filter by custom field (metadata) values.
            !!! warning
                Do not use this for application, technology, program, technical lead, or
                market segment. Use their corresponding query parameters instead.
        additional_field : list[str], optional
            Request additional columns from the search index.
        custom_fields : dict[str, Any], optional
            Filter by custom field values.
        formula_access : list[str], optional
            Filter by formula access level.
        linked_to_grid : str, optional
            Text for linked-to dropdown search in grid/report flows.
        source_field : list[str], optional
            Restrict which fields are returned in the response.
        order_by : OrderBy, optional
            Sort order. Default is DESCENDING.
        sort_by : str, optional
            Field to sort by.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[ProjectSearchItem]
            An iterator of matching partial (unhydrated) project results.
        """
        # Always POST — same path as the Albert UI (searchProjectsWithPost). GET search
        # sometimes ignores ``limit`` (defaults to 25) and returns empty for offset>0.
        payload: dict[str, Any] = {
            "order": order_by,
            "offset": offset,
            "text": text,
            "sortBy": sort_by,
            "status": status,
            "marketSegment": market_segment,
            "application": application,
            "technology": technology,
            "createdBy": created_by,
            "location": location,
            "program": program,
            "technicalLead": technical_lead,
            "fromCreatedAt": from_created_at,
            "toCreatedAt": to_created_at,
            "updatedBy": ensure_list(updated_by),
            "fromUpdatedAt": from_updated_at,
            "toUpdatedAt": to_updated_at,
            "facetField": facet_field,
            "facetText": facet_text,
            "containsField": contains_field,
            "containsText": contains_text,
            "linkedTo": linked_to,
            "myProject": my_project,
            "myRole": my_role,
            "additionalField": additional_field,
            "formulaAccess": formula_access,
            "linkedToGrid": linked_to_grid,
            "sourceField": source_field,
        }
        if metadata_filters is not None:
            payload["metadataFilters"] = {"metadata": metadata_filters}
        if custom_fields is not None:
            payload["customFields"] = {"metadata": custom_fields}

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            max_items=max_items,
            deserialize=lambda items: [
                ProjectSearchItem(**item)._bind_collection(self) for item in items
            ],
            method="POST",
            json=payload,
        )

    @validate_call
    def document_search(
        self,
        *,
        linked_to: SearchProjectId,
        text: str | None = None,
        source_field: list[str] | None = None,
        additional_field: list[str] | None = None,
        search_field: list[str] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[DocumentSearchItem]:
        """Search for documents (attachments) linked to a project.

        Each result is a lightweight
        [`DocumentSearchItem`][albert.resources.projects.DocumentSearchItem] describing an
        attachment (name, MIME type, size, uploader) rather than the file itself.

        !!! example
            ```python
            for doc in client.projects.document_search(linked_to="PRO123"):
                print(doc.name, doc.mime_type)
            ```

        Parameters
        ----------
        linked_to : SearchProjectId
            The project to filter documents by (format ``PRO...``, e.g.
            ``"PRO123"``).
        text : str, optional
            Full-text search query for document names.
        source_field : list[str], optional
            Restrict which fields are returned in the response.
        additional_field : list[str], optional
            Request additional columns from the search index.
        search_field : list[str], optional
            Restrict which fields the ``text`` query searches.
        order_by : OrderBy, optional
            Sort order. Default is DESCENDING.
        sort_by : str, optional
            Field to sort by (for example ``createdAt``).
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all.

        Returns
        -------
        Iterator[DocumentSearchItem]
            Matching document search results.
        """
        query_params = {
            "linkedTo": linked_to,
            "text": text,
            "sourceField": source_field,
            "additionalField": additional_field,
            "searchField": search_field,
            "order": order_by,
            "sortBy": sort_by,
            "offset": offset,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/documentsearch",
            session=self.session,
            params=query_params,
            max_items=max_items,
            deserialize=lambda items: [DocumentSearchItem(**item) for item in items],
        )

    @validate_call
    def get_all(
        self,
        *,
        text: str | None = None,
        status: list[str] | None = None,
        market_segment: list[str] | None = None,
        application: list[str] | None = None,
        technology: list[str] | None = None,
        created_by: list[str] | None = None,
        location: list[str] | None = None,
        program: list[str] | None = None,
        technical_lead: list[str] | None = None,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        updated_by: str | list[str] | None = None,
        from_updated_at: str | None = None,
        to_updated_at: str | None = None,
        facet_field: str | None = None,
        facet_text: str | None = None,
        contains_field: list[str] | None = None,
        contains_text: list[str] | None = None,
        linked_to: str | None = None,
        my_project: bool | None = None,
        my_role: list[str] | None = None,
        metadata_filters: dict[str, Any] | None = None,
        additional_field: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
        formula_access: list[str] | None = None,
        linked_to_grid: str | None = None,
        source_field: list[str] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[Project]:
        """Get fully populated projects matching optional filters.

        Accepts the same filters as [`search`][albert.collections.projects.ProjectCollection.search], but yields complete
        [`Project`][albert.resources.projects.Project] entities by fetching each
        match individually via [`get_by_id`][albert.collections.projects.ProjectCollection.get_by_id]. This is convenient but slower;
        prefer [`search`][albert.collections.projects.ProjectCollection.search] when you only need IDs or a few summary fields.

        !!! example
            ```python
            projects = client.projects.get_all(text="coatings", max_items=10)
            for project in projects:
                print(project.id, project.description)
            # has_more / total are preserved through hydration.
            if projects.has_more:
                print(f"Sample only; ~{projects.total} total matches")
            ```

        Parameters
        ----------
        text : str, optional
            Full-text search query.
        status : list[str], optional
            Filter by project statuses.
        market_segment : list[str], optional
            Filter by market segment.
        application : list[str], optional
            Filter by application.
        technology : list[str], optional
            Filter by technology tags.
        created_by : list[str], optional
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``).
        location : list[str], optional
            Filter by location(s).
        program : list[str], optional
            Filter by project program (custom field).
        technical_lead : list[str], optional
            Filter by technical lead (custom field).
        from_created_at : str, optional
            Only include projects created on or after this date, formatted as
            ``YYYY-MM-DD``.
        to_created_at : str, optional
            Only include projects created on or before this date, formatted as
            ``YYYY-MM-DD``.
        updated_by : str or list[str], optional
            Filter by user(s) who last updated the project. Accepts UserId(s)
            only (e.g. ``"USR4227"``), not display names.
        from_updated_at : str, optional
            Only include projects updated on or after this date (ISO 8601).
        to_updated_at : str, optional
            Only include projects updated on or before this date (ISO 8601).
        facet_field : str, optional
            Facet field to filter on.
        facet_text : str, optional
            Facet text to search for.
        contains_field : list[str], optional
            Fields to search inside.
        contains_text : list[str], optional
            Values to search for within the `contains_field`.
        linked_to : str, optional
            Entity ID the project is linked to.
        my_project : bool, optional
            If True, return only projects owned by current user.
        my_role : list[str], optional
            User roles to filter by.
        metadata_filters : dict[str, Any], optional
            Filter by custom field (metadata) values.
        additional_field : list[str], optional
            Request additional columns from the search index.
        custom_fields : dict[str, Any], optional
            Filter by custom field values.
        formula_access : list[str], optional
            Filter by formula access level.
        linked_to_grid : str, optional
            Text for linked-to dropdown search in grid/report flows.
        source_field : list[str], optional
            Restrict which fields are returned in the response.
        order_by : OrderBy, optional
            Sort order. Default is DESCENDING.
        sort_by : str, optional
            Field to sort by.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Project]
            An iterator of fully populated Project entities. Preserves ``has_more`` /
            ``total`` from the underlying search paginator.
        """

        def _hydrate(project: ProjectSearchItem) -> Project | None:
            project_id = getattr(project, "albertId", None) or getattr(project, "id", None)
            if not project_id:
                return None
            id = project_id if str(project_id).startswith("PRO") else f"PRO{project_id}"
            try:
                return self.get_by_id(id=id)
            except AlbertHTTPError as e:
                logger.warning(f"Error fetching project details {id}: {e}")
                return None

        return MappedPaginator(
            self.search(
                text=text,
                status=status,
                market_segment=market_segment,
                application=application,
                technology=technology,
                created_by=created_by,
                location=location,
                program=program,
                technical_lead=technical_lead,
                from_created_at=from_created_at,
                to_created_at=to_created_at,
                updated_by=updated_by,
                from_updated_at=from_updated_at,
                to_updated_at=to_updated_at,
                facet_field=facet_field,
                facet_text=facet_text,
                contains_field=contains_field,
                contains_text=contains_text,
                linked_to=linked_to,
                my_project=my_project,
                my_role=my_role,
                metadata_filters=metadata_filters,
                additional_field=additional_field,
                custom_fields=custom_fields,
                formula_access=formula_access,
                linked_to_grid=linked_to_grid,
                source_field=source_field,
                order_by=order_by,
                sort_by=sort_by,
                offset=offset,
                max_items=max_items,
            ),
            _hydrate,
        )

    _reference_formula_path = staticmethod(reference_formula_path)
    _in_project_reference_formula_payload = staticmethod(in_project_reference_formula_payload)
    _linked_reference_formula_payload = staticmethod(linked_reference_formula_payload)
    _reference_formula_payload = staticmethod(reference_formula_payload)

    @validate_call
    def set_reference_formula(
        self,
        *,
        project_id: ProjectId,
        sheet_id: WorksheetId,
        inventory_id: InventoryId,
        reference_formula_type: ReferenceFormulaType | str,
    ) -> ReferenceFormula:
        """Set a formula in this project as a reference formula.

        Corresponds to the "Set as Reference Formula" action in the worksheet column
        menu. Flags an existing formula column in the project worksheet as a named
        comparison point (e.g. Original commercial formula, Leading experimental
        candidate, Final outcome, or Control) during reformulation projects.

        At the point of designation, the formula column's ingredients and process
        design sections are locked by default in the worksheet to prevent accidental
        edits while the reference designation is active. Experimental results can still
        be recorded normally. To edit composition, unlock the formula column first.

        Once the project's dataset is synced via
        [`update_dataset`][albert.resources.smart_projects.SmartProject.update_dataset],
        the designated formula appears as a reference column in Target Overview and a
        reference bar in Compare Formula Data.

        This operation is not idempotent: designating a formula that is already
        designated in the specified sheet returns an error. To update an existing
        designation's role, call
        [`update_reference_formula_type`][albert.collections.projects.ProjectCollection.update_reference_formula_type].
        To remove the designation, call
        [`delete_reference_formula`][albert.collections.projects.ProjectCollection.delete_reference_formula].

        !!! example
            ```python
            from albert import Albert
            from albert.resources.projects import ReferenceFormulaType

            client = Albert()
            rf = client.projects.set_reference_formula(
                project_id="PRO123",
                sheet_id="WKS456",
                inventory_id="INV123-001",
                reference_formula_type=ReferenceFormulaType.ORIGINAL,
            )
            rf.reference_formula_type
            # 'Original'
            ```

        Parameters
        ----------
        project_id : ProjectId
            The project ID (format ``PRO...``).
        sheet_id : WorksheetId
            The sheet ID where the formula is designated (format ``WKS...``).
        inventory_id : InventoryId
            The inventory ID of the formula (format ``INV...``).
        reference_formula_type : ReferenceFormulaType | str
            The reference formula designation, such as ``ReferenceFormulaType.ORIGINAL``
            or a custom label.

        Returns
        -------
        ReferenceFormula
            The newly created reference formula designation.
        """
        payload = in_project_reference_formula_payload(
            project_id=project_id,
            sheet_id=sheet_id,
            inventory_id=inventory_id,
            reference_formula_type=reference_formula_type,
        )
        response = self.session.post(
            f"{self.base_path}/{project_id}/referenceFormulas",
            json=payload,
        )
        return ReferenceFormula(**response.json())

    @validate_call
    def link_reference_formula(
        self,
        *,
        project_id: ProjectId,
        parent_project_id: ProjectId,
        inventory_id: InventoryId,
        reference_formula_type: ReferenceFormulaType | str,
    ) -> ReferenceFormula:
        """Link a reference formula from another project.

        Corresponds to the "Link Reference Formula" action on the project homepage and
        Target Overview picker. Designates an external formula from another project
        (such as a commercial product to reformulate, a competitive benchmark, or an
        external control) as a reference formula on this project without duplicating
        records or losing historical performance data.

        The caller must have view/read access to the source project (``parent_project_id``)
        at the time of designation. The ``parent_project_id`` must differ from the host
        ``project_id``, and a formula can be linked at most once per project.

        When a reference formula from another project is linked, Albert incorporates the
        source project's full dataset into the smart dataset scope upon sync
        ([`update_dataset`][albert.resources.smart_projects.SmartProject.update_dataset])
        to support inverse design machine learning (Breakthrough). However, only the
        specifically designated reference formula columns are surfaced in Target
        Overview and Compare Formula Data.

        Historical performance results from the source project populate against this
        project's targets automatically whenever test conditions match. If the formula
        has not been measured against a target, Target Overview renders it as
        unmeasured rather than broken or missing data.

        In the web UI, a linked reference formula's type cannot be changed in place (it
        must be unlinked and relinked), although
        [`update_reference_formula_type`][albert.collections.projects.ProjectCollection.update_reference_formula_type]
        supports in-place programmatic updates.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.projects import ReferenceFormulaType

            client = Albert()
            rf = client.projects.link_reference_formula(
                project_id="PRO123",
                parent_project_id="PRO456",
                inventory_id="INV456-001",
                reference_formula_type=ReferenceFormulaType.CONTROL,
            )
            rf.is_external_formula
            # True
            ```

        Parameters
        ----------
        project_id : ProjectId
            The host project ID (format ``PRO...``).
        parent_project_id : ProjectId
            The source project ID where the formula originates (format ``PRO...``).
            Must differ from ``project_id``.
        inventory_id : InventoryId
            The inventory ID of the external formula (format ``INV...``).
        reference_formula_type : ReferenceFormulaType | str
            The reference formula designation, such as ``ReferenceFormulaType.CONTROL``
            or a custom label.

        Returns
        -------
        ReferenceFormula
            The newly linked reference formula designation.
        """
        payload = linked_reference_formula_payload(
            parent_project_id=parent_project_id,
            inventory_id=inventory_id,
            reference_formula_type=reference_formula_type,
        )
        response = self.session.post(
            f"{self.base_path}/{project_id}/referenceFormulas",
            json=payload,
        )
        return ReferenceFormula(**response.json())

    @validate_call
    def get_all_reference_formulas(
        self,
        *,
        project_id: ProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        linked_only: bool = False,
        max_items: int | None = None,
    ) -> Iterator[ReferenceFormula]:
        """Get all reference formula designations, with optional filters.

        Results are returned as a lazily paginated iterator.

        When ``project_id`` is omitted, lists reference formula designations
        tenant-wide across all accessible projects.

        When ``project_id`` is provided:
        * By default, returns all reference formulas on that project (both in-project
          worksheet designations and cross-project linked formulas).
        * If ``sheet_id`` is provided, filters to formulas designated in that specific
          worksheet sheet.
        * If ``linked_only=True``, returns only cross-project linked reference formulas
          (corresponding to the linked reference formulas list on the project homepage).

        ``sheet_id`` and ``linked_only`` are mutually exclusive and require ``project_id``.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            for rf in client.projects.get_all_reference_formulas(
                project_id="PRO123",
                linked_only=True,
            ):
                print(rf.inventory_id, rf.reference_formula_type)
            ```

        Parameters
        ----------
        project_id : ProjectId, optional
            The project ID to filter by. If omitted, lists reference formulas tenant-wide.
        sheet_id : WorksheetId, optional
            Filter designations to a specific sheet. Requires ``project_id``. Mutually
            exclusive with ``linked_only``.
        linked_only : bool, optional
            When ``True``, returns only cross-project linked reference formulas.
            Requires ``project_id``. Mutually exclusive with ``sheet_id``. Defaults to
            ``False``.
        max_items : int, optional
            Maximum number of reference formulas to yield. Defaults to ``None`` (unlimited).

        Returns
        -------
        Iterator[ReferenceFormula]
            An iterator of matching reference formula designations.
        """
        if project_id is None:
            if sheet_id is not None or linked_only:
                raise ValueError("sheet_id and linked_only require project_id")
        elif sheet_id is not None and linked_only:
            raise ValueError("sheet_id and linked_only are mutually exclusive")

        params: dict[str, str] | None = None
        if project_id is None:
            path = f"{self.base_path}/referenceFormulas"
        else:
            path = f"{self.base_path}/{project_id}/referenceFormulas"
            query_params: dict[str, str] = {}
            if sheet_id is not None:
                query_params["worksheetId"] = sheet_id
            elif linked_only:
                query_params["worksheetId"] = "external"
            if query_params:
                params = query_params

        # The reference formula endpoints are backed by DynamoDB (not OpenSearch)
        # and return a single-page response containing {total: int, Items: [...]}.
        # - The tenant-wide route rejects unknown query parameters (sending limit or offset
        #   causes a 400 Bad Request).
        # - The project-scoped route declares startKey in OpenAPI and does not accept offset.
        # KEY mode avoids sending limit/offset parameters, correctly iterates all items
        # in the single response page, and is forward-compatible if the backend implements
        # startKey/lastKey pagination in the future.
        return AlbertPaginator(
            path=path,
            mode=PaginationMode.KEY,
            session=self.session,
            deserialize=lambda items: [ReferenceFormula(**item) for item in items],
            params=params,
            max_items=max_items,
        )

    @validate_call
    def update_reference_formula_type(
        self,
        *,
        project_id: ProjectId,
        inventory_id: InventoryId,
        reference_formula_type: ReferenceFormulaType | str,
        sheet_id: WorksheetId | None = None,
        expected_type: ReferenceFormulaType | str | None = None,
    ) -> ReferenceFormula:
        """Update the type designation of an existing reference formula.

        Changes the designated role of a reference formula (for example, promoting a
        promising candidate from Leading to Final, or changing a designation).

        Pass ``sheet_id`` to update an in-project worksheet designation. If ``sheet_id``
        is omitted, updates the cross-project linked designation. Note that while the
        web UI requires unlinking and relinking cross-project formulas to change their
        type, this SDK method supports in-place type updates for both shapes.

        When ``expected_type`` is specified, the update only succeeds if the current
        type on the server matches; otherwise, a 409 conflict error is raised.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.projects import ReferenceFormulaType

            client = Albert()
            rf = client.projects.update_reference_formula_type(
                project_id="PRO123",
                sheet_id="WKS456",
                inventory_id="INV123-001",
                reference_formula_type=ReferenceFormulaType.LEADING,
                expected_type=ReferenceFormulaType.ORIGINAL,
            )
            rf.reference_formula_type
            # 'Leading'
            ```

        Parameters
        ----------
        project_id : ProjectId
            The project ID (format ``PRO...``).
        inventory_id : InventoryId
            The inventory ID of the formula (format ``INV...``).
        reference_formula_type : ReferenceFormulaType | str
            The new reference formula designation.
        sheet_id : WorksheetId, optional
            The sheet ID where the formula is designated. If omitted, updates the
            cross-project linked reference formula.
        expected_type : ReferenceFormulaType | str, optional
            The expected current type. If provided, guards against concurrent updates.

        Returns
        -------
        ReferenceFormula
            The updated reference formula designation.

        Notes
        -----
        The only patchable attribute on reference formulas is
        ``referenceFormulaType``.
        """
        path = reference_formula_path(
            project_id=project_id,
            sheet_id=sheet_id,
            inventory_id=inventory_id,
            base_path=self.base_path,
        )
        new_val = (
            reference_formula_type.value
            if hasattr(reference_formula_type, "value")
            else str(reference_formula_type)
        )
        patch_kwargs: dict[str, Any] = {
            "operation": PatchOperation.UPDATE.value,
            "attribute": "referenceFormulaType",
            "newValue": new_val,
        }
        if expected_type is not None:
            old_val = (
                expected_type.value if hasattr(expected_type, "value") else str(expected_type)
            )
            patch_kwargs["oldValue"] = old_val

        datum = PatchDatum(**patch_kwargs)
        payload = PatchPayload(data=[datum])
        self.session.patch(
            path,
            json=payload.model_dump(by_alias=True, mode="json"),
        )
        try:
            matching = next(
                (
                    rf
                    for rf in self.get_all_reference_formulas(
                        project_id=project_id,
                        sheet_id=sheet_id,
                        linked_only=sheet_id is None,
                    )
                    if rf.inventory_id == inventory_id
                ),
                None,
            )
            if matching is not None:
                return matching
        except AlbertHTTPError:
            pass

        return ReferenceFormula(
            project_id=project_id,
            inventory_id=inventory_id,
            reference_formula_type=new_val,
            is_external_formula=sheet_id is None,
            parent_project_id=project_id if sheet_id is not None else None,
            sheet_id=sheet_id,
        )

    @validate_call
    def delete_reference_formula(
        self,
        *,
        project_id: ProjectId,
        inventory_id: InventoryId,
        sheet_id: WorksheetId | None = None,
    ) -> None:
        """Delete a reference formula designation from a project.

        Removes the reference formula designation from the project.

        For in-project formulas (when ``sheet_id`` is provided), removing the designation
        unlocks the formula column in the worksheet and reverts it to a regular formula
        column. For cross-project formulas (when ``sheet_id`` is omitted), unlinks the
        formula from Target Overview and the project homepage.

        Removing a designation does NOT delete the underlying formula inventory item or
        its recorded experimental results. Furthermore, unlinking a reference formula
        does not remove the source project's historical data from the smart dataset scope.

        !!! example
            ```python
            from albert import Albert

            client = Albert()
            client.projects.delete_reference_formula(
                project_id="PRO123",
                sheet_id="WKS456",
                inventory_id="INV123-001",
            )
            ```

        Parameters
        ----------
        project_id : ProjectId
            The project ID (format ``PRO...``).
        inventory_id : InventoryId
            The inventory ID of the formula (format ``INV...``).
        sheet_id : WorksheetId, optional
            The sheet ID where the formula is designated. If omitted, deletes the
            cross-project linked reference formula.

        Returns
        -------
        None
        """
        path = reference_formula_path(
            project_id=project_id,
            sheet_id=sheet_id,
            inventory_id=inventory_id,
            base_path=self.base_path,
        )
        self.session.delete(path)
