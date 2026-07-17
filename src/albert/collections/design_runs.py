from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import SmartDatasetId, TargetId
from albert.resources.btinsight import BTInsight
from albert.resources.design import DesignMethod, DesignRunSettings
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
    create(smart_dataset_id, objectives=None, settings=None, method=DesignMethod.GENERATE) -> BTInsight
        Triggers a model-guided candidate-generation run for a smart dataset.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignRunCollection._api_version}/designruns"

    @validate_call
    def create(
        self,
        *,
        smart_dataset_id: SmartDatasetId,
        objectives: dict[TargetId, Criterion] | None = None,
        method: DesignMethod = DesignMethod.GENERATE,
        settings: DesignRunSettings | None = None,
    ) -> BTInsight:
        """Trigger an inverse-design run for a smart dataset.

        Uses a default design space and model derived from the dataset. By default,
        every target in the dataset's scope is optimized using its own target value;
        pass ``objectives`` to optimize a chosen subset with custom operators/values.

        Parameters
        ----------
        smart_dataset_id : SmartDatasetId
            The smart dataset used to train the surrogate model.
        objectives : dict[TargetId, Criterion], optional
            Per-target objectives, keyed by target id. Each key must be present within the dataset. When provided, only these targets are optimized.
            When ``None``, all targets in the dataset are optimized using their
            own target values.
        method : DesignMethod, default DesignMethod.GENERATE
            The design method to use.
        settings : DesignRunSettings, optional
            Design run settings. See :class:`~albert.resources.design.DesignRunSettings`
            for what each field controls and its allowed range.

        Returns
        -------
        BTInsight
            A handle to the run. Poll its ``state`` via
            ``client.btinsights.get_by_id(id=insight.id)`` for completion and view
            candidates in the Breakthrough insight viewer.
        """
        body: dict = {"smartDatasetId": smart_dataset_id, "method": method.value}
        if objectives is not None:
            body["objectives"] = {
                tid: c.model_dump(by_alias=True, mode="json", exclude_none=True)
                for tid, c in objectives.items()
            }
        if settings is not None:
            body["settings"] = settings.model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(self.base_path, json=body)
        return BTInsight(**response.json())
