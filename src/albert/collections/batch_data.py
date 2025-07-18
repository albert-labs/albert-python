from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import TaskId
from albert.resources.batch_data import BatchData, BatchDataType, BatchValuePatchPayload


class BatchDataCollection(BaseCollection):
    """BatchDataCollection is a collection class for managing BatchData entities in the Albert platform."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the BatchDataCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{BatchDataCollection._api_version}/batchdata"

    def create_batch_data(self, *, task_id: TaskId):
        """
        Create a new batch data entry.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task for which the batch data is being created.

        Returns
        -------
        BatchData
            The created BatchData object.
        """
        url = f"{self.base_path}"
        response = self.session.post(url, json={"parentId": task_id})
        return BatchData(**response.json())

    @validate_call
    def get_by_id(
        self,
        *,
        id: TaskId,
        type: BatchDataType = BatchDataType.TASK_ID,
        limit: int = 100,
        start_key: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> BatchData:
        """
        Retrieve BatchData by ID.

        Parameters
        ----------
        id : TaskId
            Unique Id of the selected type.
        type : BatchDataType
            Type of Id for which BatchData will be fetched.
        limit : int, optional
            The maximum number of list entities to return.
        start_key : str, optional
            The primary key of the first item that this operation will evaluate.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING
        Returns
        ------
        BatchData
            The BatchData object.
        """
        params = {
            "id": id,
            "limit": limit,
            "type": type,
            "startKey": start_key,
            "orderBy": order_by,
        }
        response = self.session.get(self.base_path, params=params)
        return BatchData(**response.json())

    def update_used_batch_amounts(
        self, *, task_id: str, patches: list[BatchValuePatchPayload]
    ) -> None:
        """
        Update the used batch amounts for a given task ID.

        Parameters
        ----------
        task_id : str
            The ID of the task to update.
        patches : list[BatchValuePatchPayload]
            The patch payloads containing the data to update.

        Returns
        -------
        None
            This method does not return anything.
        """
        url = f"{self.base_path}/{task_id}/values"
        self.session.patch(
            url,
            json=[
                patch.model_dump(exclude_none=True, by_alias=True, mode="json")
                for patch in patches
            ],
        )
