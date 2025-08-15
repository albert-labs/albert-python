from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import ProjectId
from albert.exceptions import AlbertHTTPError
from albert.resources.projects import Project, ProjectSearchItem


class ProjectCollection(BaseCollection):
    """ProjectCollection is a collection class for managing Project entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"description", "grid", "metadata", "state"}

    def __init__(self, *, session: AlbertSession):
        """
        Initialize a ProjectCollection object.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ProjectCollection._api_version}/projects"

    def create(self, *, project: Project) -> Project:
        """
        Create a new project.

        Parameters
        ----------
        project : Project
            The project to create.

        Returns
        -------
        Optional[Project]
            The created project object if successful, None otherwise.
        """
        response = self.session.post(
            self.base_path, json=project.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        return Project(**response.json())

    @validate_call
    def get_by_id(self, *, id: ProjectId) -> Project:
        """
        Retrieve a project by its ID.

        Parameters
        ----------
        id : str
            The ID of the project to retrieve.

        Returns
        -------
        Project
            The project object if found
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)

        return Project(**response.json())

    def update(self, *, project: Project) -> Project:
        """Update a project.

        Parameters
        ----------
        project : Project
            The updated project object.

        Returns
        -------
        Project
            The updated project object as returned by the server.
        """
        existing_project = self.get_by_id(id=project.id)
        patch_data = self._generate_patch_payload(existing=existing_project, updated=project)
        url = f"{self.base_path}/{project.id}"

        self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=project.id)

    @validate_call
    def delete(self, *, id: ProjectId) -> None:
        """
        Delete a project by its ID.

        Parameters
        ----------
        id : str
            The ID of the project to delete.

        Returns
        -------
        None
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
    ) -> Iterator[ProjectSearchItem]:
        """
        Search for Project matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str, optional
            Full-text search query.
        status : list of str, optional
            Filter by project statuses.
        market_segment : list of str, optional
            Filter by market segment.
        application : list of str, optional
            Filter by application.
        technology : list of str, optional
            Filter by technology tags.
        created_by : list of str, optional
            Filter by user names who created the project.
        location : list of str, optional
            Filter by location(s).
        from_created_at : str, optional
            Earliest creation date in 'YYYY-MM-DD' format.
        to_created_at : str, optional
            Latest creation date in 'YYYY-MM-DD' format.
        facet_field : str, optional
            Facet field to filter on.
        facet_text : str, optional
            Facet text to search for.
        contains_field : list of str, optional
            Fields to search inside.
        contains_text : list of str, optional
            Values to search for within the `contains_field`.
        linked_to : str, optional
            Entity ID the project is linked to.
        my_project : bool, optional
            If True, return only projects owned by current user.
        my_role : list of str, optional
            User roles to filter by.
        order_by : OrderBy, optional
            Sort order. Default is DESCENDING.
        sort_by : str, optional
            Field to sort by.
        offset : int, optional
            Pagination offset.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[ProjectSearchItem]
            An iterator of matching partial (unhydrated) Project results.
        """
        query_params = {
            "order": order_by.value,
            "offset": offset,
            "text": text,
            "sortBy": sort_by,
            "status": status,
            "marketSegment": market_segment,
            "application": application,
            "technology": technology,
            "createdBy": created_by,
            "location": location,
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
        """
        Retrieve fully hydrated Project entities with optional filters.

        This method returns complete entity data using `get_by_id`.
        Use :meth:`search` for faster retrieval when you only need lightweight, partial (unhydrated) entities.

        Returns
        -------
        Iterator[Project]
            An iterator of fully hydrated Project entities.
        """
        for project in self.search(
            text=text,
            status=status,
            market_segment=market_segment,
            application=application,
            technology=technology,
            created_by=created_by,
            location=location,
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
