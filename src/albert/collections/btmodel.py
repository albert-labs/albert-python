from albert.collections.base import BaseCollection
from albert.resources.btmodel import BTModel, BTModelSession
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

    def _deserialize_with_session(self, data: dict) -> BTModelSession:
        mds = BTModelSession(**data)
        mds._session = self.session
        return mds

    def create(self, *, model_session: BTModelSession) -> BTModelSession:
        response = self.session.post(
            self.base_path,
            json=model_session.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return self._deserialize_with_session(response.json())

    def get_by_id(self, *, id: str) -> BTModelSession:
        response = self.session.get(f"{self.base_path}/{id}")
        return self._deserialize_with_session(response.json())

    def update(self, *, model_session: BTModelSession) -> BTModelSession:
        path = f"{self.base_path}/{model_session.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=model_session.id),
            updated=model_session,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=model_session.id)

    def delete(self, *, id: str) -> None:
        """Delete a BTModelSession by ID.

        Parameters
        ----------
        id : str
            The ID of the BTModelSession to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")


class BTModelCollection(BaseCollection):
    """
    BTModelCollection is a collection class for managing Breakthrough model entities.

    Breakthrough models are associated with a parent Breakthrough model session.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.
    parent_id: str
        The Albert ID for the parent BTModelSession.

    Attributes
    ----------
    base_path : str
        The base path for BTModel API requests.
    """

    _api_version = "v3"
    _updatable_attributes = {"state", "start_time", "end_time", "total_time", "model_binary_key"}

    def __init__(self, *, session: AlbertSession, parent_id: str):
        super().__init__(session=session)
        self.parent_id = parent_id
        self.base_path = f"/api/{BTModelCollection._api_version}/btmodel/{parent_id}/model"

    def create(self, *, model: BTModel) -> BTModel:
        response = self.session.post(
            self.base_path,
            json=model.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTModel(**response.json())

    def get_by_id(self, *, id: str) -> BTModel:
        response = self.session.get(f"{self.base_path}/{id}")
        return BTModel(**response.json())

    def update(self, *, model: BTModel) -> BTModel:
        path = f"{self.base_path}/{model.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=model.id),
            updated=model,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=model.id)

    def delete(self, *, id: str) -> None:
        """Delete a BTModel by ID.

        Parameters
        ----------
        id : str
            The ID of the BTModel to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")
