from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import SmartDatasetId, TargetId
from albert.resources.btinsight import BTInsight
from albert.resources.chats import ChatSessionRef
from albert.resources.design import (
    DesignRunValidationResponse,
    DOEDesignRunRequest,
    DOERunSettings,
    OptimizationDesignRunRequest,
    OptimizationRunSettings,
)
from albert.resources.targets import Criterion


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

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignRunCollection._api_version}/designruns"

    @validate_call
    def create_optimization(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        name: str | None = None,
        objectives: dict[TargetId, Criterion] | None = None,
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
        objectives : dict[TargetId, Criterion], optional
            Per-target objectives. Each key must be present within the dataset.
            When ``None``, all targets in the dataset are optimized using their own
            target values.
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
        against, not what the batch is optimized for — there is no direction, target
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
        objectives: dict[TargetId, Criterion] | None = None,
        settings: OptimizationRunSettings | None = None,
    ) -> DesignRunValidationResponse:
        """Validate an optimization run configuration without starting a job.

        Uses the same request shape as
        [`create_optimization`][albert.collections.design_runs.DesignRunCollection.create_optimization].

        Returns a preflight result with ``valid`` and ``violations``. ``valid=False`` with
        populated ``violations`` is a normal result and is not raised as an exception.

        Pre-check failures (e.g. dataset not ``READY``, objective out of scope, invalid
        settings) are raised as [`AlbertClientError`][albert.exceptions.AlbertClientError],
        the same class of failure as calling
        [`create_optimization`][albert.collections.design_runs.DesignRunCollection.create_optimization]
        with a bad configuration.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset used to train the surrogate model.
        objectives : dict[TargetId, Criterion], optional
            Per-target objectives for the optimization run.
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
            Other request failures. See [`AlbertHTTPError`][albert.exceptions.AlbertHTTPError].
        """
        body = OptimizationDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            objectives=objectives,
            settings=settings,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/validate", json=body)
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
        [`AlbertClientError`][albert.exceptions.AlbertClientError], the same class of
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
            Other request failures. See [`AlbertHTTPError`][albert.exceptions.AlbertHTTPError].
        """
        body = DOEDesignRunRequest(
            smart_dataset_id=smart_dataset_id,
            settings=settings,
            anchor_targets=anchor_targets,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/validate", json=body)
        return DesignRunValidationResponse(**response.json())
