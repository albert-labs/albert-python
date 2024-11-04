from albert.collections.base import BaseCollection
from albert.resources.workflows import Workflow
from albert.session import AlbertSession
from albert.utils.exceptions import ForbiddenError, InternalServerError, NotFoundError
from albert.utils.logging import logger
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

    def list(self):
        def deserialize(data: dict) -> Workflow | None:
            id = data["albertId"]
            try:
                return self.get_by_id(id=id)
            except (ForbiddenError, InternalServerError, NotFoundError) as e:
                logger.warning(f"Error fetching Workflow '{id}': {e}")
                return None

        params = {}
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            params=params,
            session=self.session,
            deserialize=deserialize,
        )

    def get_by_id(self, *, id):
        response = self.session.get(f"{self.base_path}/{id}")
        return Workflow(**response.json())

    def create(self, *, workflow: Workflow):
        response = self.session.post(
            self.base_path, json=workflow.model_dump(mode="json", by_alias=True, exclude_none=True)
        )
        return Workflow(**response.json())
