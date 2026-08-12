from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import SmartDatasetId, TargetId
from albert.resources.btinsight import BTInsight
from albert.resources.chats import ChatSessionRef
from albert.resources.design import (
    DesignMethod,
    DesignRunSettings,
    DesignRunValidationResponse,
    SpaceFillingRunSettings,
)
from albert.resources.targets import Criterion


def _validate_create_args(
    *,
    method: DesignMethod,
    objectives: dict[TargetId, Criterion] | None,
    settings: DesignRunSettings | SpaceFillingRunSettings | None,
    anchor_targets: list[str] | None,
) -> None:
    if method is DesignMethod.SPACE_FILLING:
        if objectives is not None:
            raise ValueError(
                "objectives cannot be used with method='space_filling'. "
                "Space-filling proposes a batch that covers the design space relative "
                "to existing experiments; it does not optimize toward target values."
            )
        if isinstance(settings, DesignRunSettings):
            raise ValueError(
                "Generate run settings cannot be used with method='space_filling'. "
                "Pass SpaceFillingRunSettings instead."
            )
    elif anchor_targets is not None:
        raise ValueError(
            "anchor_targets is only supported for method='space_filling'. "
            "It narrows which existing rows count as historical anchors; "
            "it has no meaning for model-guided generate runs."
        )
    if method is DesignMethod.GENERATE and isinstance(settings, SpaceFillingRunSettings):
        raise ValueError(
            "Space-filling run settings cannot be used with method='generate'. "
            "Pass DesignRunSettings instead."
        )


def _build_design_run_request(
    *,
    smart_dataset_id: SmartDatasetId,
    objectives: dict[TargetId, Criterion] | None = None,
    method: DesignMethod = DesignMethod.GENERATE,
    settings: DesignRunSettings | SpaceFillingRunSettings | None = None,
    chat_session: ChatSessionRef | None = None,
    anchor_targets: list[str] | None = None,
) -> dict:
    _validate_create_args(
        method=method,
        objectives=objectives,
        settings=settings,
        anchor_targets=anchor_targets,
    )
    body: dict = {"smartDatasetId": smart_dataset_id, "method": method.value}
    if method is DesignMethod.GENERATE and objectives is not None:
        body["objectives"] = {
            tid: c.model_dump(by_alias=True, mode="json", exclude_none=True)
            for tid, c in objectives.items()
        }
    if settings is not None:
        body["settings"] = settings.model_dump(by_alias=True, mode="json", exclude_none=True)
    if anchor_targets is not None:
        body["anchorTargets"] = anchor_targets
    if chat_session is not None:
        body["session"] = chat_session.model_dump(by_alias=True, mode="json", exclude_none=True)
    return body


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
    create(smart_dataset_id, objectives=None, settings=None, method=DesignMethod.GENERATE, chat_session=None) -> BTInsight
        Triggers an inverse-design run for a smart dataset.
    validate(smart_dataset_id, objectives=None, settings=None, method=DesignMethod.GENERATE) -> DesignRunValidationResponse
        Validates a design-run configuration without starting a job.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignRunCollection._api_version}/designruns"

    _validate_create_args = staticmethod(_validate_create_args)

    @validate_call
    def create(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        objectives: dict[TargetId, Criterion] | None = None,
        method: DesignMethod = DesignMethod.GENERATE,
        settings: DesignRunSettings | SpaceFillingRunSettings | None = None,
        chat_session: ChatSessionRef | None = None,
        anchor_targets: list[str] | None = None,
    ) -> BTInsight:
        """Trigger an inverse-design run for a smart dataset.

        Two methods are available:

        **``generate``** trains a surrogate on historical data and searches for
        candidates predicted to meet your targets. Each candidate carries predicted
        values, uncertainty, and a score. Use this when the user wants candidates
        optimized toward specific performance targets.

        **``space_filling``** proposes a batch that **covers the design space** and
        is spread relative to the experiments the user already has in the Smart
        Dataset. It produces **no scores and no predictions** and trains no model.
        It needs **no objectives**; passing them is an error. Use it when there is
        little or no data to model, or when the user wants a screening or starting
        batch rather than optimized candidates.

        The historical experiments a run accounts for are fixed by the **Smart
        Dataset**, not by anything on this call. To compare against a different
        history, use a different Smart Dataset. For space-filling only,
        ``anchor_targets`` optionally narrows the comparison further to rows that
        already have a measurement for every listed target id. That changes which
        existing rows the batch is spread against, not what the batch is optimized
        for — there is no direction, target value, or scoring involved.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset whose experiment history anchors the run.
        objectives : dict[TargetId, Criterion], optional
            Per-target objectives for ``generate`` only. Each key must be present
            within the dataset. When ``None``, all targets in the dataset are
            optimized using their own target values. Must not be passed with
            ``space_filling``.
        method : DesignMethod, default DesignMethod.GENERATE
            ``generate`` for model-guided optimization, or ``space_filling`` for a
            coverage batch with no scoring.
        settings : DesignRunSettings or SpaceFillingRunSettings, optional
            Method-specific run sizing. See
            [`DesignRunSettings`][albert.resources.design.DesignRunSettings] and
            [`SpaceFillingRunSettings`][albert.resources.design.SpaceFillingRunSettings].
        chat_session : ChatSessionRef, optional
            Chat session to notify when the run completes. See
            [`ChatSessionRef`][albert.resources.chats.ChatSessionRef]. Omit for no
            callback; the run is still tracked through the returned ``BTInsight``.
            Serialized to the wire as ``session``.
        anchor_targets : list[str], optional
            Space-filling only. Performance target ids; only experiments measured
            on every listed target count as historical anchors for diversity.

        Returns
        -------
        BTInsight
            A handle to the run. Poll its ``state`` via
            ``client.btinsights.get_by_id(id=insight.id)`` for completion and view
            candidates in the insight viewer.
        """
        body = _build_design_run_request(
            smart_dataset_id=smart_dataset_id,
            objectives=objectives,
            method=method,
            settings=settings,
            chat_session=chat_session,
            anchor_targets=anchor_targets,
        )
        response = self.session.post(self.base_path, json=body)
        return BTInsight(**response.json())

    @validate_call
    def validate(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        objectives: dict[TargetId, Criterion] | None = None,
        method: DesignMethod = DesignMethod.GENERATE,
        settings: DesignRunSettings | SpaceFillingRunSettings | None = None,
        anchor_targets: list[str] | None = None,
    ) -> DesignRunValidationResponse:
        """Validate a design run configuration without starting a job.

        Uses the same request shape as [`create`][albert.collections.design_runs.DesignRunCollection.create].

        Returns a preflight result with ``valid`` and ``violations``. ``valid=False`` with
        populated ``violations`` is a normal result and is not raised as an exception.

        Pre-check failures (e.g. dataset not ``READY``, objective out of scope, invalid
        settings) are raised as [`AlbertClientError`][albert.exceptions.AlbertClientError],
        the same class of failure as calling
        [`create`][albert.collections.design_runs.DesignRunCollection.create] with a bad
        configuration.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset used to train the surrogate model.
        objectives : dict[TargetId, Criterion], optional
            Per-target objectives for ``generate`` only.
        method : DesignMethod, default DesignMethod.GENERATE
            The design method to validate.
        settings : DesignRunSettings or SpaceFillingRunSettings, optional
            Method-specific run sizing.
        anchor_targets : list[str], optional
            Space-filling only. See [`create`][albert.collections.design_runs.DesignRunCollection.create].

        Returns
        -------
        DesignRunValidationResponse
            Preflight result with ``valid``, ``violations``, ``target_sample_counts``,
            and ``in_scope_row_count`` when available.

        Raises
        ------
        AlbertClientError
            Pre-check failures (invalid configuration before validation can run).
        AlbertHTTPError
            Other request failures. See [`AlbertHTTPError`][albert.exceptions.AlbertHTTPError].
        """
        body = _build_design_run_request(
            smart_dataset_id=smart_dataset_id,
            objectives=objectives,
            method=method,
            settings=settings,
            anchor_targets=anchor_targets,
        )
        response = self.session.post(f"{self.base_path}/validate", json=body)
        return DesignRunValidationResponse(**response.json())
