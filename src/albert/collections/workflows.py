from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.workflows import Workflow
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class WorkflowCollection(BaseCollection):
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

    def create(self, *, workflows: list[Workflow]) -> Workflow:
        if isinstance(workflows, Workflow):
            # in case the user forgets this should be a list
            workflows = [workflows]
        response = self.session.post(
            url=f"{self.base_path}/bulk",
            json=[x.model_dump(mode="json", by_alias=True, exclude_none=True) for x in workflows],
        )
        return [Workflow(**x) for x in response.json()]

    def get_by_id(self, *, id: str) -> Workflow:
        response = self.session.get(f"{self.base_path}/{id}")
        return Workflow(**response.json())

    def get_by_ids(self, *, ids: list[str]) -> Workflow:
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 100] for i in range(0, len(ids), 100)]
        return [
            Workflow(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def list(self, limit: int = 50) -> Iterator[Workflow]:
        def deserialize(items: list[dict]) -> list[Workflow]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        params = {"limit": limit}
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params=params,
            session=self.session,
            deserialize=deserialize,
        )
