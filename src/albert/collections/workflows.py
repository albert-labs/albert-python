from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.resources.workflows import Workflow


class WorkflowCollection(BaseCollection):
    """WorkflowCollection is a collection class for managing Workflow entities in the Albert platform."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the WorkflowCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{WorkflowCollection._api_version}/workflows"

    def create(self, *, workflows: list[Workflow]) -> list[Workflow]:
        """Create or return matching workflows for the provided list of workflows.
        This endpoint automatically tries to find an existing workflow with the same parameter setpoints, and will either return the existing workflow or create a new one.

        Parameters
        ----------
        workflows : list[Workflow]
            A list of Workflow entities to find or create.

        Returns
        -------
        list[Workflow]
            A list of created or found Workflow entities.
        """
        if isinstance(workflows, Workflow):
            # in case the user forgets this should be a list
            workflows = [workflows]
        response = self.session.post(
            url=f"{self.base_path}/bulk",
            json=[x.model_dump(mode="json", by_alias=True, exclude_none=True) for x in workflows],
        )
        return [Workflow(**x) for x in response.json()]

    def get_by_id(self, *, id: str) -> Workflow:
        """Retrieve a Workflow by its ID.

        Parameters
        ----------
        id : str
            The ID of the Workflow to retrieve.

        Returns
        -------
        Workflow
            The Workflow object.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Workflow(**response.json())

    def get_by_ids(self, *, ids: list[str]) -> list[Workflow]:
        """Returns a list of Workflow entities by their IDs.

        Parameters
        ----------
        ids : list[str]
            The list of Workflow IDs to retrieve.

        Returns
        -------
        list[Workflow]
            The list of Workflow entities matching the provided IDs.
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            Workflow(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def get_all(
        self,
        max_items: int | None = None,
    ) -> Iterator[Workflow]:
        """
        Get all workflows. Unlikely to be used in production.

        Parameters
        ----------
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Yields
        ------
        Iterator[Workflow]
            An iterator of Workflow entities.
        """

        def deserialize(items: list[dict]) -> list[Workflow]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params={},
            session=self.session,
            deserialize=deserialize,
            max_items=max_items,
        )
