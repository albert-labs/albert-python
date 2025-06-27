from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.exceptions import AlbertHTTPError
from albert.resources.projects import Project, ProjectFilterParams, ProjectSearchItem


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

    def get_by_id(self, *, id: str) -> Project:
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

    def delete(self, *, id: str) -> None:
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

    def search(self, *, params: ProjectFilterParams | None = None) -> Iterator[ProjectSearchItem]:
        """Search for Project matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        params : ProjectFilterParams, optional
            Structured query parameters to filter, sort, and paginate projects.

        Returns
        -------
        Iterator[Project]
            An iterator of Project resources.
        """
        params = params or ProjectFilterParams()

        query_params = {
            "limit": params.limit,
            "order": params.order_by.value,
            "text": params.text,
            "sortBy": params.sort_by,
            "status": params.status,
            "marketSegment": params.market_segment,
            "application": params.application,
            "technology": params.technology,
            "createdBy": params.created_by,
            "location": params.location,
            "fromCreatedAt": params.from_created_at,
            "toCreatedAt": params.to_created_at,
            "facetField": params.facet_field,
            "facetText": params.facet_text,
            "containsField": params.contains_field,
            "containsText": params.contains_text,
            "linkedTo": params.linked_to,
            "myProjects": params.my_projects,
            "myRole": params.my_role,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=query_params,
            deserialize=lambda items: [
                ProjectSearchItem(**item)._bind_collection(self) for item in items
            ],
        )

    def get_all(self, *, params: ProjectFilterParams | None = None) -> Iterator[Project]:
        """Retrieve fully hydrated Project entities with optional filters.

        This method returns complete entity data using `get_by_id`.
        Use :meth:`search` for faster retrieval when you only need lightweight, partial (unhydrated) entities.

        Parameters
        ----------
        params : ProjectFilterParams, optional
            Structured query parameters to filter, sort, and paginate projects.

        Returns
        -------
        Iterator[Project]
            An iterator of fully hydrated Project entities.
        """
        params = params or ProjectFilterParams()

        for project in self.search(params=params):
            project_id = getattr(project, "albertId", None) or getattr(project, "id", None)
            if not project_id:
                continue

            id = project_id if project_id.startswith("PRO") else f"PRO{project_id}"

            try:
                yield self.get_by_id(id=id)
            except AlbertHTTPError as e:
                logger.warning(f"Error fetching project details {id}: {e}")
