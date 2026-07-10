from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import ProjectId, SearchProjectId
from albert.exceptions import AlbertHTTPError
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
    display name) and a :class:`~albert.resources.projects.ProjectClass`
    controlling its access level (private, shared, or confidential).

    This collection is accessed as ``client.projects``.

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
        Retrieve a single project by its Project ID.
    update(project) -> Project
        Apply changes to an existing project.
    delete(id) -> None
        Delete a project by its Project ID.
    search(...) -> Iterator[ProjectSearchItem]
        Fast, lightweight search returning partial projects (best for lookups).
    get_all(...) -> Iterator[Project]
        Same filters as search, but returns fully hydrated projects (slower).
    document_search(...) -> Iterator[DocumentSearchItem]
        Search documents (attachments) linked to a project.

    Examples
    --------
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
        other fields on the :class:`~albert.resources.projects.Project` first.

        Parameters
        ----------
        project : Project
            The project to create.

        Returns
        -------
        Project
            The newly created project, populated with its assigned Project ID.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.projects import Project
            project = client.projects.create(
                project=Project(description="Weatherproof Coatings 2026")
            )
            project.id
            # 'PRO123'
            ```
        """
        response = self.session.post(
            self.base_path, json=project.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        return Project(**response.json(), session=self.session)

    @validate_call
    def get_by_id(self, *, id: ProjectId) -> Project:
        """Retrieve a single project by its ID.

        To find projects without knowing their IDs, use :meth:`search` or
        :meth:`get_all`.

        Parameters
        ----------
        id : ProjectId
            The Project ID (format ``PRO...``, e.g. ``"PRO123"``).

        Returns
        -------
        Project
            The fully hydrated project.

        Examples
        --------
        !!! example
            ```python
            project = client.projects.get_by_id(id="PRO123")
            project.description
            # 'Weatherproof Coatings 2026'
            ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)

        return Project(**response.json(), session=self.session)

    def update(self, *, project: Project) -> Project:
        """Update a project.

        Fetches the current server-side project, diffs it against the object you
        pass in, and applies the difference. Retrieve the project (e.g. with
        :meth:`get_by_id`), modify the updatable fields, then pass it here.

        Parameters
        ----------
        project : Project
            The project carrying the desired changes. Its ``id`` identifies which
            project to update.

        Returns
        -------
        Project
            The updated project as returned by the server.

        Notes
        -----
        The following fields can be updated: ``description``, ``grid``,
        ``metadata``, ``state``.

        Examples
        --------
        !!! example
            ```python
            project = client.projects.get_by_id(id="PRO123")
            project.description = "Weatherproof Coatings 2026 (rev B)"
            updated = client.projects.update(project=project)
            ```
        """
        existing_project = self.get_by_id(id=project.id)
        patch_data = self._generate_patch_payload(existing=existing_project, updated=project)
        url = f"{self.base_path}/{project.id}"

        self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=project.id)

    @validate_call
    def delete(self, *, id: ProjectId) -> None:
        """Delete a project by its ID.

        Parameters
        ----------
        id : ProjectId
            The Project ID (format ``PRO...``, e.g. ``"PRO123"``).

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            client.projects.delete(id="PRO123")
            ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

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
        facet_field: str | None = None,
        facet_text: str | None = None,
        contains_field: list[str] | None = None,
        contains_text: list[str] | None = None,
        linked_to: str | None = None,
        my_project: bool | None = None,
        my_role: list[str] | None = None,
        metadata_filters: dict[str, Any] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[ProjectSearchItem]:
        """Search for projects matching the provided criteria.

        This is the fast way to find projects: it returns lightweight, partial
        (unhydrated) :class:`~albert.resources.projects.ProjectSearchItem` results
        and is best for lookups, counts, and pulling IDs. To retrieve fully
        detailed :class:`~albert.resources.projects.Project` entities, use
        :meth:`get_all` instead (slower, one full fetch per result).

        All filters are optional; with no arguments this iterates over all
        projects you can access.

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
            Filter by user names who created the project.
        location : list[str], optional
            Filter by location(s).
        program : list[str], optional
            Filter by project program (custom field).
        technical_lead : list[str], optional
            Filter by technical lead (custom field).
        from_created_at : str, optional
            Earliest creation date in 'YYYY-MM-DD' format.
        to_created_at : str, optional
            Latest creation date in 'YYYY-MM-DD' format.
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
            Filters for custom field values, sent in the `metadataFilters` request body field.
            !!! warning
                Do not use this for application, technology, program, technical lead, or
                market segment. Use their corresponding query parameters instead.
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

        Examples
        --------
        !!! example
            ```python
            for hit in client.projects.search(text="coatings", max_items=25):
                print(hit.id, hit.description)
            ```
        """
        query_params = {
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
            "facetField": facet_field,
            "facetText": facet_text,
            "containsField": contains_field,
            "containsText": contains_text,
            "linkedTo": linked_to,
            "myProject": my_project,
            "myRole": my_role,
        }

        if metadata_filters is not None:
            payload: dict[str, Any] = {
                **query_params,
                "metadataFilters": {"metadata": metadata_filters},
            }
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

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=query_params,
            max_items=max_items,
            deserialize=lambda items: [
                ProjectSearchItem(**item)._bind_collection(self) for item in items
            ],
        )

    @validate_call
    def document_search(
        self,
        *,
        linked_to: SearchProjectId,
        text: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[DocumentSearchItem]:
        """Search for documents (attachments) linked to a project.

        Each result is a lightweight
        :class:`~albert.resources.projects.DocumentSearchItem` describing an
        attachment (name, MIME type, size, uploader) rather than the file itself.

        Parameters
        ----------
        linked_to : SearchProjectId
            The project to filter documents by (format ``PRO...``, e.g.
            ``"PRO123"``).
        text : str, optional
            Full-text search query for document names.
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

        Examples
        --------
        !!! example
            ```python
            for doc in client.projects.document_search(linked_to="PRO123"):
                print(doc.name, doc.mime_type)
            ```
        """
        query_params = {
            "linkedTo": linked_to,
            "text": text,
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
        facet_field: str | None = None,
        facet_text: str | None = None,
        contains_field: list[str] | None = None,
        contains_text: list[str] | None = None,
        linked_to: str | None = None,
        my_project: bool | None = None,
        my_role: list[str] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[Project]:
        """Retrieve fully hydrated projects matching optional filters.

        Accepts the same filters as :meth:`search`, but yields complete
        :class:`~albert.resources.projects.Project` entities by fetching each
        match individually via :meth:`get_by_id`. This is convenient but slower;
        prefer :meth:`search` when you only need IDs or a few summary fields.

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
            Filter by user names who created the project.
        location : list[str], optional
            Filter by location(s).
        program : list[str], optional
            Filter by project program (custom field).
        technical_lead : list[str], optional
            Filter by technical lead (custom field).
        from_created_at : str, optional
            Earliest creation date in 'YYYY-MM-DD' format.
        to_created_at : str, optional
            Latest creation date in 'YYYY-MM-DD' format.
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
        order_by : OrderBy, optional
            Sort order. Default is DESCENDING.
        sort_by : str, optional
            Field to sort by.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Project]
            An iterator of fully hydrated Project entities.

        Examples
        --------
        !!! example
            ```python
            for project in client.projects.get_all(text="coatings", max_items=10):
                print(project.id, project.description)
            ```
        """
        for project in self.search(
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
            facet_field=facet_field,
            facet_text=facet_text,
            contains_field=contains_field,
            contains_text=contains_text,
            linked_to=linked_to,
            my_project=my_project,
            my_role=my_role,
            order_by=order_by,
            sort_by=sort_by,
            offset=offset,
            max_items=max_items,
        ):
            project_id = getattr(project, "albertId", None) or getattr(project, "id", None)
            if not project_id:
                continue

            id = project_id if project_id.startswith("PRO") else f"PRO{project_id}"

            try:
                yield self.get_by_id(id=id)
            except AlbertHTTPError as e:
                logger.warning(f"Error fetching project details {id}: {e}")
