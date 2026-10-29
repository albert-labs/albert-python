from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.design_spaces import _LastKeyCursorPaginator
from albert.core.pagination import PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import (
    DesignModelConfigId,
    DesignRunId,
    DesignSpaceId,
    ProjectId,
    SmartDatasetId,
    TargetId,
)
from albert.resources.btinsight import BTInsight
from albert.resources.chats import ChatSessionRef
from albert.resources.design import (
    DesignMethod,
    DesignObjective,
    DesignRunValidationResponse,
    DOEDesignRunRequest,
    DOERunSettings,
    OptimizationDesignRunRequest,
    OptimizationRunSettings,
)
from albert.resources.design_runs import DesignRun, DesignRunState


class DesignRunCollection(BaseCollection):
    """Trigger inverse-design runs for Smart Datasets (🧪Beta).

    This collection is accessed as ``client.design_runs``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for design-run requests.

    Methods
    -------
    create_optimization(smart_dataset_id, name=None, objectives=None, settings=None, chat_session=None) -> BTInsight
        Triggers a model-guided optimization run for a smart dataset.
    create_doe(smart_dataset_id, name=None, settings=None, chat_session=None, anchor_targets=None) -> BTInsight
        Triggers a space-filling design run for a smart dataset.
    validate_optimization(smart_dataset_id, objectives=None, settings=None) -> DesignRunValidationResponse
        Validates an optimization run configuration without starting a job.
    validate_doe(smart_dataset_id, settings=None, anchor_targets=None) -> DesignRunValidationResponse
        Validates a space-filling run configuration without starting a job.
    """

    _api_version = "v3"
    _validate_suffix = "validate"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignRunCollection._api_version}/designruns"

    @validate_call
    def create_optimization(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        name: str | None = None,
        objectives: dict[TargetId, DesignObjective] | None = None,
        settings: OptimizationRunSettings | None = None,
        chat_session: ChatSessionRef | None = None,
    ) -> BTInsight:
        """Trigger a model-guided optimization run for a smart dataset.

        Trains a surrogate on historical data and searches for candidates predicted
        to meet targets. Each candidate carries predicted values, uncertainty, and
        a score. Use this when the user wants candidates optimized toward specific
        performance targets.

        The historical experiments a run accounts for are fixed by the **Smart
        Dataset**, not by anything on this call. To compare against a different
        history, use a different Smart Dataset.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset whose experiment history anchors the run.
        name : str, optional
            Display name for the resulting insight. When ``None``, a name is
            generated from the smart dataset id.
        objectives : dict[TargetId, DesignObjective], optional
            Per-target objectives, each carrying an optional ``weight`` that sets how
            much it counts relative to the others on this run. See
            [`DesignObjective`][albert.resources.design.DesignObjective]. Each key must
            be present within the dataset. When ``None``, all targets in the dataset are
            optimized using their own target values, each at the default weight. A plain
            [`Criterion`][albert.resources.targets.Criterion] is accepted and takes the
            default weight.
        settings : OptimizationRunSettings, optional
            Run sizing for candidate generation and selection. See
            [`OptimizationRunSettings`][albert.resources.design.OptimizationRunSettings].
        chat_session : ChatSessionRef, optional
            Chat session to notify when the run completes. See
            [`ChatSessionRef`][albert.resources.chats.ChatSessionRef]. Omit for no
            callback; the run is still tracked through the returned ``BTInsight``.
            Serialized to the wire as ``session``.

        Returns
        -------
        BTInsight
            A handle to the run. Poll its ``state`` via
            ``client.btinsights.get_by_id(id=insight.id)`` for completion and view
            candidates in the insight viewer.

        Raises
        ------
        AlbertClientError
            The run configuration was rejected, for example the dataset is not
            ``READY``, an objective is out of scope, or a setting is invalid.
        AlbertHTTPError
            Other failures.
        """
        body = OptimizationDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            name=name,
            objectives=objectives,
            settings=settings,
            session=chat_session,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(self.base_path, json=body)
        return BTInsight(**response.json())

    @validate_call
    def create_doe(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        name: str | None = None,
        anchor_targets: list[str] | None = None,
        settings: DOERunSettings | None = None,
        chat_session: ChatSessionRef | None = None,
    ) -> BTInsight:
        """Trigger a space-filling DOE design run.

        Proposes a batch that **covers the design space**, spread relative to the
        experiments the user already has. Produces **no scores and no predictions**.
        Trains no model. There is no ``objectives`` parameter on this method. Use it
        when there is little or no data to model, or when the user wants a screening
        or starting batch.

        The set of historical experiments it accounts for is fixed by the **Smart
        Dataset**, not by anything on this call. To compare against a different
        history, use a different Smart Dataset. ``anchor_targets`` optionally narrows
        the comparison further to experiments that already have a measurement for
        every named target id. That changes which existing rows the batch is spread
        against, not what the batch is optimized for: there is no direction, target
        value, or scoring involved.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset whose experiment history anchors the run.
        name : str, optional
            Display name for the resulting insight. When ``None``, a name is
            generated from the smart dataset id.
        anchor_targets : list[str], optional
            Performance target ids; only experiments measured on every listed target
            count as historical anchors for diversity.
        settings : DOERunSettings, optional
            Run sizing for space-filling sampling. See
            [`DOERunSettings`][albert.resources.design.DOERunSettings].
        chat_session : ChatSessionRef, optional
            Chat session to notify when the run completes. See
            [`ChatSessionRef`][albert.resources.chats.ChatSessionRef]. Omit for no
            callback; the run is still tracked through the returned ``BTInsight``.
            Serialized to the wire as ``session``.

        Returns
        -------
        BTInsight
            A handle to the run. Poll its ``state`` via
            ``client.btinsights.get_by_id(id=insight.id)`` for completion and view
            candidates in the insight viewer.

        Raises
        ------
        AlbertClientError
            The run configuration was rejected, for example the dataset is not
            ``READY`` or a setting is invalid.
        AlbertHTTPError
            Other failures.
        """
        body = DOEDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            name=name,
            settings=settings,
            session=chat_session,
            anchor_targets=anchor_targets,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(self.base_path, json=body)
        return BTInsight(**response.json())

    @validate_call
    def validate_optimization(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        objectives: dict[TargetId, DesignObjective] | None = None,
        settings: OptimizationRunSettings | None = None,
    ) -> DesignRunValidationResponse:
        """Validate an optimization run configuration without starting a job.

        Uses the same request shape as
        [`create_optimization`][albert.collections.design_runs.DesignRunCollection.create_optimization].

        Returns a preflight result with ``valid`` and ``violations``. ``valid=False`` with
        populated ``violations`` is a normal result and is not raised as an exception.

        Pre-check failures (e.g. dataset not ``READY``, objective out of scope, invalid
        settings) are raised as `AlbertClientError`,
        the same class of failure as calling
        [`create_optimization`][albert.collections.design_runs.DesignRunCollection.create_optimization]
        with a bad configuration.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset used to train the surrogate model.
        objectives : dict[TargetId, DesignObjective], optional
            Per-target objectives for the optimization run, each carrying an optional
            ``weight``. See [`DesignObjective`][albert.resources.design.DesignObjective].
        settings : OptimizationRunSettings, optional
            Run sizing for candidate generation and selection.

        Returns
        -------
        DesignRunValidationResponse
            Preflight result with ``valid``, ``violations``, and ``target_sample_counts``
            when available.

        Raises
        ------
        AlbertClientError
            Pre-check failures (invalid configuration before validation can run).
        AlbertHTTPError
            Other request failures.
        """
        body = OptimizationDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            objectives=objectives,
            settings=settings,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/{self._validate_suffix}", json=body)
        return DesignRunValidationResponse(**response.json())

    @validate_call
    def validate_doe(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        anchor_targets: list[str] | None = None,
        settings: DOERunSettings | None = None,
    ) -> DesignRunValidationResponse:
        """Validate a space-filling run configuration without starting a job.

        Uses the same request shape as
        [`create_doe`][albert.collections.design_runs.DesignRunCollection.create_doe].

        Returns a preflight result with ``valid`` and ``violations``. ``valid=False`` with
        populated ``violations`` is a normal result and is not raised as an exception.

        Pre-check failures (e.g. dataset not ``READY``, invalid settings) are raised as
        `AlbertClientError`, the same class of
        failure as calling
        [`create_doe`][albert.collections.design_runs.DesignRunCollection.create_doe]
        with a bad configuration.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset whose experiment history anchors the run.
        anchor_targets : list[str], optional
            Performance target ids that narrow which existing rows count as historical
            anchors for diversity.
        settings : DOERunSettings, optional
            Run sizing for space-filling sampling.

        Returns
        -------
        DesignRunValidationResponse
            Preflight result with ``valid``, ``violations``, and ``target_sample_counts``
            when available.

        Raises
        ------
        AlbertClientError
            Pre-check failures (invalid configuration before validation can run).
        AlbertHTTPError
            Other request failures.
        """
        body = DOEDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            settings=settings,
            anchor_targets=anchor_targets,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/{self._validate_suffix}", json=body)
        return DesignRunValidationResponse(**response.json())


class DesignRunV4Collection(DesignRunCollection):
    """Trigger inverse-design runs through the v4 ``design`` service (🧪Beta).

    This collection is accessed as ``client.design_runs_v4``. It has the same methods,
    arguments, and return types as
    [`DesignRunCollection`][albert.collections.design_runs.DesignRunCollection], except
    that the create methods return the queued
    [`DesignRun`][albert.resources.design_runs.DesignRun] instead of a ``BTInsight``, and
    the create and validate methods also accept ``parent_id``, ``design_space_id`` and
    ``design_model_config_id``. It adds methods to read stored runs and rename them.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base path for v4 design runs.

    Methods
    -------
    create_optimization(smart_dataset_id, name=None, objectives=None, settings=None, chat_session=None, parent_id=None, design_space_id=None, design_model_config_id=None) -> DesignRun
        Triggers a model-guided optimization run for a smart dataset.
    create_doe(smart_dataset_id, name=None, settings=None, chat_session=None, anchor_targets=None, parent_id=None, design_space_id=None, design_model_config_id=None) -> DesignRun
        Triggers a space-filling design run for a smart dataset.
    validate_optimization(smart_dataset_id, objectives=None, settings=None, parent_id=None, design_space_id=None, design_model_config_id=None) -> DesignRunValidationResponse
        Validates an optimization run configuration without starting a job.
    validate_doe(smart_dataset_id, settings=None, anchor_targets=None, parent_id=None, design_space_id=None, design_model_config_id=None) -> DesignRunValidationResponse
        Validates a space-filling run configuration without starting a job.
    get_by_id(id) -> DesignRun
        Get a stored design run by its ID.
    get_all(parent_id, state=None, method=None, max_items=None) -> Iterator[DesignRun]
        Get all design runs in a project.
    update(design_run) -> DesignRun
        Update the name or description of a design run.
    """

    _api_version = "v4"
    _validate_suffix = "validation"
    _updatable_attributes = {"name", "description"}
    _non_deletable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignRunV4Collection._api_version}/design/runs"

    @validate_call
    def create_optimization(  # type: ignore[override]
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        name: str | None = None,
        objectives: dict[TargetId, DesignObjective] | None = None,
        settings: OptimizationRunSettings | None = None,
        chat_session: ChatSessionRef | None = None,
        parent_id: ProjectId | None = None,
        design_space_id: DesignSpaceId | None = None,
        design_model_config_id: DesignModelConfigId | None = None,
    ) -> DesignRun:
        """Trigger a model-guided optimization run for a smart dataset.

        Takes the arguments of
        [`DesignRunCollection.create_optimization`][albert.collections.design_runs.DesignRunCollection.create_optimization]
        plus the three below, and returns the queued run.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset whose experiment history anchors the run.
        name : str, optional
            Display name for the run. A name is generated when ``None``.
        objectives : dict[TargetId, DesignObjective], optional
            Per-target objectives. When ``None``, all targets in the dataset are optimized.
        settings : OptimizationRunSettings, optional
            Run sizing for candidate generation and selection.
        chat_session : ChatSessionRef, optional
            Chat session to notify when the run completes.
        parent_id : ProjectId, optional
            The project (format ``PRO...``) that owns the run. When ``None``, the smart
            dataset's project is used.
        design_space_id : DesignSpaceId, optional
            A published design space (format ``DSP...``) to sample from. When ``None``, a
            space derived from the dataset is used.
        design_model_config_id : DesignModelConfigId, optional
            A published design model config (format ``DMC...``) to model with. When
            ``None``, a config derived from the dataset is used.

        Returns
        -------
        DesignRun
            The queued run. Poll it with
            [`get_by_id`][albert.collections.design_runs.DesignRunV4Collection.get_by_id].

        Raises
        ------
        AlbertClientError
            The run was rejected (HTTP 422). ``err.response.json()["message"]`` is the
            list of violations, each with ``code``, ``message`` and optional ``targetId``
            and ``components``.
        AlbertHTTPError
            Other failures.
        """
        body = OptimizationDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            name=name,
            objectives=objectives,
            settings=settings,
            session=chat_session,
            parent_id=parent_id,
            design_space_id=design_space_id,
            design_model_config_id=design_model_config_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(self.base_path, json=body)
        return DesignRun(**response.json())

    @validate_call
    def create_doe(  # type: ignore[override]
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        name: str | None = None,
        anchor_targets: list[str] | None = None,
        settings: DOERunSettings | None = None,
        chat_session: ChatSessionRef | None = None,
        parent_id: ProjectId | None = None,
        design_space_id: DesignSpaceId | None = None,
        design_model_config_id: DesignModelConfigId | None = None,
    ) -> DesignRun:
        """Trigger a space-filling DOE design run.

        Takes the arguments of
        [`DesignRunCollection.create_doe`][albert.collections.design_runs.DesignRunCollection.create_doe]
        plus ``parent_id``, ``design_space_id`` and ``design_model_config_id``, which
        mean the same as on
        [`create_optimization`][albert.collections.design_runs.DesignRunV4Collection.create_optimization],
        and returns the queued run.

        Returns
        -------
        DesignRun
            The queued run. Poll it with
            [`get_by_id`][albert.collections.design_runs.DesignRunV4Collection.get_by_id].

        Raises
        ------
        AlbertClientError
            The run was rejected (HTTP 422). ``err.response.json()["message"]`` is the
            list of violations, each with ``code``, ``message`` and optional ``targetId``
            and ``components``.
        AlbertHTTPError
            Other failures.
        """
        body = DOEDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            name=name,
            settings=settings,
            session=chat_session,
            anchor_targets=anchor_targets,
            parent_id=parent_id,
            design_space_id=design_space_id,
            design_model_config_id=design_model_config_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(self.base_path, json=body)
        return DesignRun(**response.json())

    @validate_call
    def validate_optimization(  # type: ignore[override]
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        objectives: dict[TargetId, DesignObjective] | None = None,
        settings: OptimizationRunSettings | None = None,
        parent_id: ProjectId | None = None,
        design_space_id: DesignSpaceId | None = None,
        design_model_config_id: DesignModelConfigId | None = None,
    ) -> DesignRunValidationResponse:
        """Validate an optimization run configuration without starting a job.

        Takes the same request as
        [`create_optimization`][albert.collections.design_runs.DesignRunV4Collection.create_optimization]
        and returns a preflight result with ``valid`` and ``violations``.

        Returns
        -------
        DesignRunValidationResponse
            Preflight result with ``valid``, ``violations``, and ``target_sample_counts``
            when available.

        Raises
        ------
        AlbertClientError
            The run was rejected (HTTP 422). ``err.response.json()["message"]`` is the
            list of violations, each with ``code``, ``message`` and optional ``targetId``
            and ``components``.
        AlbertHTTPError
            Other request failures.
        """
        body = OptimizationDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            objectives=objectives,
            settings=settings,
            parent_id=parent_id,
            design_space_id=design_space_id,
            design_model_config_id=design_model_config_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/{self._validate_suffix}", json=body)
        return DesignRunValidationResponse(**response.json())

    @validate_call
    def validate_doe(  # type: ignore[override]
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        anchor_targets: list[str] | None = None,
        settings: DOERunSettings | None = None,
        parent_id: ProjectId | None = None,
        design_space_id: DesignSpaceId | None = None,
        design_model_config_id: DesignModelConfigId | None = None,
    ) -> DesignRunValidationResponse:
        """Validate a space-filling run configuration without starting a job.

        Takes the same request as
        [`create_doe`][albert.collections.design_runs.DesignRunV4Collection.create_doe]
        and returns a preflight result with ``valid`` and ``violations``.

        Returns
        -------
        DesignRunValidationResponse
            Preflight result with ``valid``, ``violations``, and ``target_sample_counts``
            when available.

        Raises
        ------
        AlbertClientError
            The run was rejected (HTTP 422). ``err.response.json()["message"]`` is the
            list of violations, each with ``code``, ``message`` and optional ``targetId``
            and ``components``.
        AlbertHTTPError
            Other request failures.
        """
        body = DOEDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            settings=settings,
            anchor_targets=anchor_targets,
            parent_id=parent_id,
            design_space_id=design_space_id,
            design_model_config_id=design_model_config_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/{self._validate_suffix}", json=body)
        return DesignRunValidationResponse(**response.json())

    @validate_call
    def get_by_id(self, *, id: DesignRunId) -> DesignRun:
        """Get a stored design run by its ID.

        !!! example
            ```python
            run = client.design_runs_v4.get_by_id(id="DSR123")
            run.state
            # <DesignRunState.COMPLETE: 'complete'>
            ```

        Parameters
        ----------
        id : DesignRunId
            The design run ID (format ``DSR...``).

        Returns
        -------
        DesignRun
            The run and its status.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return DesignRun(**response.json())

    @validate_call
    def get_all(
        self,
        *,
        parent_id: ProjectId,
        state: DesignRunState | None = None,
        method: DesignMethod | None = None,
        max_items: int | None = None,
    ) -> Iterator[DesignRun]:
        """Get all design runs in a project.

        Results are returned as a lazily paginated iterator.

        !!! example
            ```python
            for run in client.design_runs_v4.get_all(parent_id="PRO123"):
                print(run.id, run.name, run.state)
            ```

        Parameters
        ----------
        parent_id : ProjectId
            The project (format ``PRO...``) whose runs to list.
        state : DesignRunState, optional
            Limit to runs in this lifecycle state.
        method : DesignMethod, optional
            Limit to ``generate`` or ``space_filling`` runs.
        max_items : int, optional
            Stop after this many runs.

        Returns
        -------
        Iterator[DesignRun]
            A lazily paginated iterator over the design runs.
        """
        params = {"parentId": parent_id}
        if state is not None:
            params["state"] = state
        if method is not None:
            params["method"] = method
        return _LastKeyCursorPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [DesignRun(**item) for item in items],
        )

    @validate_call
    def update(self, *, design_run: DesignRun) -> DesignRun:
        """Update the name or description of a design run.

        Retrieve the run with
        [`get_by_id`][albert.collections.design_runs.DesignRunV4Collection.get_by_id],
        modify ``name`` and/or ``description``, then pass it here. Only changed fields
        are applied. This works in every state.

        !!! example
            ```python
            run = client.design_runs_v4.get_by_id(id="DSR123")
            run.name = "Clearcoat sweep, rev B"
            updated = client.design_runs_v4.update(design_run=run)
            ```

        Parameters
        ----------
        design_run : DesignRun
            The run carrying the desired changes. Its ``id`` identifies which run to
            update.

        Returns
        -------
        DesignRun
            The updated design run.

        Notes
        -----
        The following fields can be updated: ``name``, ``description``.
        """
        existing = self.get_by_id(id=design_run.id)
        patch_payload = self._generate_patch_payload(
            existing=existing, updated=design_run
        ).model_dump(mode="json", by_alias=True)
        if not patch_payload["data"]:
            return existing
        response = self.session.patch(f"{self.base_path}/{design_run.id}", json=patch_payload)
        return DesignRun(**response.json())
