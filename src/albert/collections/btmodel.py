from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.resources.btmodel import BTModel, BTModelSession
from albert.resources.identifiers import BTModelId, BTModelSessionId
from albert.session import AlbertSession


class BTModelSessionCollection(BaseCollection):
    """
    BTModelSessionCollection is a collection class for managing Breakthrough model session entities.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base path for BTModelSession API requests.
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "flag", "registry"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{BTModelSessionCollection._api_version}/btmodel"

    @validate_call
    def create(self, *, model_session: BTModelSession) -> BTModelSession:
        response = self.session.post(
            self.base_path,
            json=model_session.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTModelSession(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTModelSessionId) -> BTModelSession:
        response = self.session.get(f"{self.base_path}/{id}")
        return BTModelSession(**response.json())

    @validate_call
    def update(self, *, model_session: BTModelSession) -> BTModelSession:
        path = f"{self.base_path}/{model_session.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=model_session.id),
            updated=model_session,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=model_session.id)

    @validate_call
    def delete(self, *, id: BTModelSessionId) -> None:
        """Delete a BTModelSession by ID.

        Parameters
        ----------
        id : BTModelSessionId
            The ID of the BTModelSession to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")


class BTModelCollection(BaseCollection):
    """
    BTModelCollection is a collection class for managing Breakthrough model entities.

    Breakthrough models can be associated with a parent Breakthrough model session,
    or a detached without a parent.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.
    """

    _api_version = "v3"
    _updatable_attributes = {
        "state",
        "start_time",
        "end_time",
        "total_time",
        "model_binary_key",
        "metadata",
        "target",
        "type",
        "name",
    }

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)

    def _get_base_path(self, parent_id: str | None) -> str:
        api_base = f"/api/{BTModelCollection._api_version}/btmodel"
        if parent_id is not None:
            return f"{api_base}/{parent_id}/model"
        else:
            return f"{api_base}/models/detached"

    @validate_call
    def create(self, *, model: BTModel, parent_id: BTModelSessionId | None = None) -> BTModel:
        """
        Create a new BTModel instance.

        Parameters
        ----------
        model : BTModel
            The BTModel instance to create.
        parent_id : BTModelSessionId | None
            The optional ID of the parent BTModelSession.

        Returns
        -------
        BTModel
            The created BTModel instance.
        """
        base_path = self._get_base_path(parent_id)
        response = self.session.post(
            base_path,
            json=model.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTModel(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTModelId, parent_id: BTModelSessionId | None = None) -> BTModel:
        """
        Retrieve a BTModel by its ID.

        Parameters
        ----------
        id : BTModelId
            The ID of the BTModel to retrieve.
        parent_id : BTModelSessionId | None
            The optional ID of the parent BTModelSession.

        Returns
        -------
        BTModel
            The retrieved BTModel instance.
        """
        base_path = self._get_base_path(parent_id)
        response = self.session.get(f"{base_path}/{id}")
        return BTModel(**response.json())

    @validate_call
    def update(self, *, model: BTModel, parent_id: BTModelSessionId | None = None) -> BTModel:
        """
        Update an existing BTModel.

        Parameters
        ----------
        model : BTModel
            The BTModel instance with updated data.
        parent_id : BTModelSessionId | None
            The optional ID of the parent BTModelSession.

        Returns
        -------
        BTModel
            The updated BTModel instance.
        """
        base_path = self._get_base_path(parent_id)
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=model.id, parent_id=parent_id),
            updated=model,
            generate_metadata_diff=False,
        )
        self.session.patch(
            f"{base_path}/{model.id}",
            json=payload.model_dump(mode="json", by_alias=True),
        )
        return self.get_by_id(id=model.id, parent_id=parent_id)

    @validate_call
    def delete(self, *, id: BTModelId, parent_id: BTModelSessionId | None = None) -> None:
        """Delete a BTModel by ID.

        Parameters
        ----------
        id : BTModelId
            The ID of the BTModel to delete.
        parent_id : BTModelSessionId | None
            The optional ID of the parent BTModelSession.

        Returns
        -------
        None
        """
        base_path = self._get_base_path(parent_id)
        self.session.delete(f"{base_path}/{id}")
