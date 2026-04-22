from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import SmartDatasetId, TargetId
from albert.resources.smart_datasets import SmartDataset, SmartDatasetScope
from albert.resources.targets import AggregateBy, TargetLineData


class SmartDatasetCollection(BaseCollection):
    """A collection for managing smart datasets in the Albert platform (🧪Beta).

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for smart dataset API requests.

    Methods
    -------
    create(scope, build=True) -> SmartDataset
        Creates a new smart dataset entity.
    get_all() -> list[SmartDataset]
        Lists all smart datasets for the tenant.
    get_by_id(id) -> SmartDataset
        Retrieves a smart dataset by its ID.
    update(id, **kwargs) -> SmartDataset
        Updates a smart dataset by its ID.
    delete(id) -> None
        Deletes a smart dataset by its ID.
    get_target_data(smart_dataset_id, target_id, ...) -> TargetLineData
        Retrieves target line data for a specific target within a smart dataset.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the SmartDatasetCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{SmartDatasetCollection._api_version}/smartdatasets"

    def create(
        self,
        *,
        scope: SmartDatasetScope,
        build: bool = True,
    ) -> SmartDataset:
        """
        Creates a new smart dataset entity.

        Parameters
        ----------
        scope : SmartDatasetScope
            The scope of the smart dataset.
        build : bool, optional
            Whether to populate the smart dataset with data from Albert.

        Returns
        -------
        SmartDataset
            The created smart dataset entity.
        """
        response = self.session.post(
            self.base_path,
            json={"scope": scope.model_dump(by_alias=True, exclude_none=False, mode="json")},
            params={"build": build},
        )
        return SmartDataset(**response.json())

    def get_all(self) -> list[SmartDataset]:
        """
        Lists all smart datasets for the tenant.

        Returns
        -------
        list[SmartDataset]
            A list of SmartDataset entities.
        """
        response = self.session.get(self.base_path)
        data = response.json()
        return [SmartDataset(**item) for item in data.get("Items", [])]

    def get_by_id(self, *, id: SmartDatasetId) -> SmartDataset:
        """
        Retrieves a smart dataset by its ID.

        Parameters
        ----------
        id : SmartDatasetId
            The ID of the smart dataset to retrieve.

        Returns
        -------
        SmartDataset
            The SmartDataset entity.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return SmartDataset(**response.json())

    def update(self, *, smart_dataset: SmartDataset) -> SmartDataset:
        """
        Updates a smart dataset by its ID.

        Parameters
        ----------
        smart_dataset : SmartDataset
            The smart dataset to update. Must have an id set.

        Returns
        -------
        SmartDataset
            The updated SmartDataset entity.
        """
        url = f"{self.base_path}/{smart_dataset.id}"
        payload = smart_dataset.model_dump(
            by_alias=True,
            exclude_none=True,
            mode="json",
            include={"build_state", "storage_key", "scope", "schema_"},
        )
        response = self.session.patch(url, json=payload)
        return SmartDataset(**response.json())

    def delete(self, *, id: SmartDatasetId) -> None:
        """
        Deletes a smart dataset by its ID.

        Parameters
        ----------
        id : SmartDatasetId
            The ID of the smart dataset to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def get_target_data(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        target_id: TargetId,
        aggregate_by: AggregateBy | None = None,
        inventory_id: str | None = None,
        lot_id: str | None = None,
        workflow_id: str | None = None,
    ) -> TargetLineData:
        """
        Retrieves target line data for a specific target within a smart dataset.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The ID of the smart dataset.
        target_id : TargetId
            The ID of the target.
        aggregate_by : AggregateBy, optional
            The aggregation dimension. Defaults to ``"measurement"`` server-side.
        inventory_id : str, optional
            Scopes data to a specific inventory item.
        lot_id : str, optional
            Scopes data to a specific lot.
        workflow_id : str, optional
            Scopes data to a specific workflow run.

        Returns
        -------
        TargetLineData
            The target line data for the given target.
        """
        url = f"{self.base_path}/{smart_dataset_id}/targets/{target_id}/data"
        params: dict = {}
        if aggregate_by is not None:
            params["aggregate_by"] = aggregate_by.value
        if inventory_id is not None:
            params["inventory_id"] = inventory_id
        if lot_id is not None:
            params["lot_id"] = lot_id
        if workflow_id is not None:
            params["workflow_id"] = workflow_id
        response = self.session.get(url, params=params or None)
        body = response.json()["result"]["body"]
        return TargetLineData(**body)
