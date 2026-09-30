from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import BTModelId, BTModelSessionId
from albert.resources.btmodel import BTModel, BTModelSession


class BTModelSessionCollection(BaseCollection):
    """Manage Breakthrough model sessions in the Albert platform.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. A **model session**
    ([`BTModelSession`][albert.resources.btmodel.BTModelSession]) is the parent record that
    groups a related set of trained models produced in a single modeling run. Each
    session is built from a dataset ([`BTDataset`][albert.resources.btdataset.BTDataset]),
    identified by ``dataset_id`` (format ``DST...``), and the individual models it
    contains are managed through
    [`BTModelCollection`][albert.collections.btmodel.BTModelCollection].

    Model sessions are identified by a model session ID (format ``MDS...``, e.g.
    ``"MDS12"``).

    This collection is accessed as ``client.btmodelsessions``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        session = client.btmodelsessions.get_by_id(id="MDS12")
        session.name
        # 'Tensile strength study'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for model session requests.

    Methods
    -------
    create(model_session) -> BTModelSession
        Create a new model session.
    get_by_id(id) -> BTModelSession
        Get a single model session by its ID.
    update(model_session) -> BTModelSession
        Update an existing model session.
    delete(id) -> None
        Delete a model session by its ID.
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "flag", "registry"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{BTModelSessionCollection._api_version}/btmodel"

    @validate_call
    def create(self, *, model_session: BTModelSession) -> BTModelSession:
        """Create a new model session.

        A session groups the models produced from a single dataset. Set
        ``dataset_id`` to the [`BTDataset`][albert.resources.btdataset.BTDataset] the
        session is built from, and ``category`` to indicate whether it is a
        user-built or Albert-built session.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.btmodel import BTModelSession, BTModelSessionCategory

            client = Albert()
            session = BTModelSession(
                name="Tensile strength study",
                category=BTModelSessionCategory.USER_MODEL,
                dataset_id="DST1",
            )
            created = client.btmodelsessions.create(model_session=session)
            created.id
            # 'MDS12'
            ```

        Parameters
        ----------
        model_session : BTModelSession
            The session to create. ``name``, ``category``, and ``dataset_id`` are
            required.

        Returns
        -------
        BTModelSession
            The newly created session, populated with its assigned ID.
        """
        response = self.session.post(
            self.base_path,
            json=model_session.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTModelSession(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTModelSessionId) -> BTModelSession:
        """Get a single model session by its ID.

        !!! example
            ```python
            session = client.btmodelsessions.get_by_id(id="MDS12")
            session.name
            # 'Tensile strength study'
            ```

        Parameters
        ----------
        id : BTModelSessionId
            The model session ID (format ``MDS...``, e.g. ``"MDS12"``).

        Returns
        -------
        BTModelSession
            The fully populated model session.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return BTModelSession(**response.json())

    @validate_call
    def update(self, *, model_session: BTModelSession) -> BTModelSession:
        """Update an existing model session.

        Fetch the session (e.g. with [`get_by_id`][albert.collections.btmodel.BTModelSessionCollection.get_by_id]), modify the updatable
        fields on the returned object, then pass it here. Only the fields listed
        in Notes are applied; changes to other fields are ignored.

        !!! example
            ```python
            session = client.btmodelsessions.get_by_id(id="MDS12")
            session.name = "Tensile strength study (rev 2)"
            updated = client.btmodelsessions.update(model_session=session)
            updated.name
            # 'Tensile strength study (rev 2)'
            ```

        Parameters
        ----------
        model_session : BTModelSession
            The session to update. Must have a valid ``id``.

        Returns
        -------
        BTModelSession
            The updated session.

        Notes
        -----
        The following fields can be updated: ``flag``, ``name``, ``registry``.
        """

        path = f"{self.base_path}/{model_session.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=model_session.id),
            updated=model_session,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=model_session.id)

    @validate_call
    def delete(self, *, id: BTModelSessionId) -> None:
        """Delete a model session by its ID.

        !!! example
            ```python
            client.btmodelsessions.delete(id="MDS12")
            ```

        Parameters
        ----------
        id : BTModelSessionId
            The model session ID to delete (format ``MDS...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")


class BTModelCollection(BaseCollection):
    """Manage individual Breakthrough models in the Albert platform.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. A **model**
    ([`BTModel`][albert.resources.btmodel.BTModel]) is a single trained model. A model
    can either belong to a parent model session
    ([`BTModelSession`][albert.resources.btmodel.BTModelSession]), in which case its
    ``parent_id`` is the session ID, or be **detached** (standalone, with no parent
    session). Most methods here take an optional ``parent_id``: pass the session ID
    to operate on a model within that session, or omit it to operate on a detached
    model.

    Models are identified by a model ID (format ``MDL...``, e.g. ``"MDL34"``).

    This collection is accessed as ``client.btmodels``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        model = client.btmodels.get_by_id(id="MDL34", parent_id="MDS12")
        model.state
        # <BTModelState.COMPLETE: 'Complete'>
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Methods
    -------
    create(model, parent_id=None) -> BTModel
        Create a new model, optionally within a parent session.
    get_by_id(id, parent_id=None) -> BTModel
        Get a single model by its ID.
    update(model, parent_id=None) -> BTModel
        Update an existing model.
    delete(id, parent_id=None) -> None
        Delete a model by its ID.
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
        """Create a new model.

        Pass ``parent_id`` to create the model inside an existing session
        ([`BTModelSession`][albert.resources.btmodel.BTModelSession]); omit it to create a
        detached, standalone model.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.btmodel import BTModel

            client = Albert()
            model = BTModel(name="Random forest v1")
            created = client.btmodels.create(model=model, parent_id="MDS12")
            created.id
            # 'MDL34'
            ```

        Parameters
        ----------
        model : BTModel
            The model to create. ``name`` is required.
        parent_id : BTModelSessionId, optional
            The parent session ID (format ``MDS...``). If omitted, the model is
            created as detached.

        Returns
        -------
        BTModel
            The newly created model, populated with its assigned ID.

        Notes
        -----
        Only ``name`` is required on a [`BTModel`][albert.resources.btmodel.BTModel].
        ``dataset_id`` and ``target`` are optional on the model, but in practice
        they are provided together with ``state``.
        """
        base_path = self._get_base_path(parent_id)
        response = self.session.post(
            base_path,
            json=model.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTModel(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTModelId, parent_id: BTModelSessionId | None = None) -> BTModel:
        """Get a single model by its ID.

        !!! example
            ```python
            model = client.btmodels.get_by_id(id="MDL34", parent_id="MDS12")
            model.name
            # 'Random forest v1'
            ```

        Parameters
        ----------
        id : BTModelId
            The model ID (format ``MDL...``, e.g. ``"MDL34"``).
        parent_id : BTModelSessionId, optional
            The parent session ID (format ``MDS...``). Omit for a detached model.

        Returns
        -------
        BTModel
            The fully populated model.
        """
        base_path = self._get_base_path(parent_id)
        response = self.session.get(f"{base_path}/{id}")
        return BTModel(**response.json())

    @validate_call
    def update(self, *, model: BTModel, parent_id: BTModelSessionId | None = None) -> BTModel:
        """Update an existing model.

        Fetch the model (e.g. with [`get_by_id`][albert.collections.btmodel.BTModelCollection.get_by_id]), modify the updatable fields
        on the returned object, then pass it here. Only the fields listed in Notes
        are applied; changes to other fields are ignored.

        !!! example
            ```python
            model = client.btmodels.get_by_id(id="MDL34", parent_id="MDS12")
            model.name = "Random forest v2"
            updated = client.btmodels.update(model=model, parent_id="MDS12")
            updated.name
            # 'Random forest v2'
            ```

        Parameters
        ----------
        model : BTModel
            The model to update. Must have a valid ``id``.
        parent_id : BTModelSessionId, optional
            The parent session ID (format ``MDS...``). Omit for a detached model.

        Returns
        -------
        BTModel
            The updated model.

        Notes
        -----
        The following fields can be updated: ``end_time``, ``metadata``,
        ``model_binary_key``, ``name``, ``start_time``, ``state``, ``target``,
        ``total_time``, ``type``.
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
        """Delete a model by its ID.

        !!! example
            ```python
            client.btmodels.delete(id="MDL34", parent_id="MDS12")
            ```

        Parameters
        ----------
        id : BTModelId
            The model ID to delete (format ``MDL...``).
        parent_id : BTModelSessionId, optional
            The parent session ID (format ``MDS...``). Omit for a detached model.

        Returns
        -------
        None
        """
        base_path = self._get_base_path(parent_id)
        self.session.delete(f"{base_path}/{id}")
