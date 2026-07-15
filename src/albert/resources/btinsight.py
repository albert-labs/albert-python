from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    BTDatasetId,
    BTInsightId,
    BTModelId,
    BTModelSessionId,
    ProjectId,
)
from albert.core.shared.models.base import BaseResource


class BTInsightCategory(str, Enum):
    """The kind of Breakthrough output an insight represents.

    Attributes
    ----------
    OPTIMIZER : str
        A standard optimizer result.
    CUSTOM_OPTIMIZER : str
        A custom-configured optimizer result.
    IMPACT_CHART : str
        An impact chart showing how inputs affect an outcome.
    MOLECULE : str
        A molecule-related insight.
    SMART_DOE : str
        A smart design-of-experiments result.
    GENERATE : str
        A generative result (e.g. generated candidates).
    """

    OPTIMIZER = "Optimizer"
    CUSTOM_OPTIMIZER = "Custom Optimizer"
    IMPACT_CHART = "Impact Chart"
    MOLECULE = "Molecule"
    SMART_DOE = "Smart DOE"
    GENERATE = "Generate"


class BTInsightState(str, Enum):
    """Progress state of a Breakthrough insight computation.

    Attributes
    ----------
    QUEUED : str
        The computation has been queued but has not started.
    BUILDING_MODELS : str
        Underlying models are being trained.
    GENERATING_CANDIDATES : str
        Candidate solutions are being generated.
    COMPLETE : str
        The computation has finished successfully.
    ERROR : str
        The computation failed.
    """

    QUEUED = "Queued"
    BUILDING_MODELS = "Building Models"
    GENERATING_CANDIDATES = "Generating Candidates"
    COMPLETE = "Complete"
    ERROR = "Error"


class BTInsightPayloadType(str, Enum):
    """Which system produced an insight's payload.

    Attributes
    ----------
    BREAKTHROUGH : str
        Payload produced by Breakthrough.
    ALBERTO : str
        Legacy payload configuration retained for backwards compatibility with
        insights created in 2024 that predate the current session schema; slated
        for deprecation.
    """

    BREAKTHROUGH = "Breakthrough"
    ALBERTO = "Alberto"


class BTInsightRegistry(BaseAlbertModel):
    """Result metadata recorded for a Breakthrough insight.

    Attributes
    ----------
    build_logs : dict or None
        Free-form logs captured while the insight was computed.
    metrics : dict or None
        Free-form performance metrics recorded for the insight.
    settings : dict or None
        Free-form settings used to produce the insight.
    """

    build_logs: dict[str, Any] | None = Field(default=None, alias="BuildLogs")
    metrics: dict[str, Any] | None = Field(default=None, alias="Metrics")
    settings: dict[str, Any] | None = Field(default=None, alias="Settings")


class BTInsight(BaseResource, protected_namespaces=()):
    """An output or insight produced by Breakthrough.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. An insight captures a
    Breakthrough result, such as an optimizer run, impact chart, or set of
    generated candidates. It can trace back to the dataset, model session, and
    model it came from via ``dataset_id``, ``model_session_id``, and ``model_id``
    (see :class:`~albert.resources.btdataset.BTDataset` and
    :class:`~albert.resources.btmodel.BTModel`). Insights are managed through
    :class:`~albert.collections.btinsight.BTInsightCollection`.

    Attributes
    ----------
    name : str
        Human-readable name of the insight.
    category : BTInsightCategory
        The kind of Breakthrough output this insight represents.
    metadata : dict or None
        Free-form metadata associated with the insight.
    state : BTInsightState or None
        Current progress state of the insight computation.
    id : BTInsightId or None
        Unique identifier of the insight (format ``INS...``). Assigned by Albert on
        creation.
    parent_id : ProjectId or None
        Identifier of the project the insight belongs to (format ``PRO...``).
    dataset_id : BTDatasetId or None
        Identifier of the dataset the insight is based on (format ``DST...``).
    model_session_id : BTModelSessionId or None
        Identifier of the model session the insight came from (format ``MDS...``).
    model_id : BTModelId or None
        Identifier of the model the insight came from (format ``MDL...``).
    output_key : str or None
        Storage key for the insight's output artifact, if applicable.
    start_time : str or None
        When the insight computation started, if recorded.
    end_time : str or None
        When the insight computation finished, if recorded.
    total_time : str or None
        Total time taken to compute the insight, if recorded.
    raw_payload : dict or None
        The raw result payload produced for the insight.
    payload_type : BTInsightPayloadType or None
        Which system produced the payload.
    registry : BTInsightRegistry or None
        Result metadata (logs, metrics, settings) recorded for the insight.
    content_edited : bool or None
        Whether the insight's content has been manually edited.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.btinsight import BTInsight, BTInsightCategory

        insight = BTInsight(
            name="Cost optimizer run",
            category=BTInsightCategory.OPTIMIZER,
        )
        ```
    """

    name: str
    category: BTInsightCategory
    metadata: dict[str, Any] | None = Field(default=None, alias="Metadata")
    state: BTInsightState | None = Field(default=None)
    id: BTInsightId | None = Field(default=None, alias="albertId")
    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    dataset_id: BTDatasetId | None = Field(default=None, alias="datasetId")
    model_session_id: BTModelSessionId | None = Field(default=None, alias="modelSessionId")
    model_id: BTModelId | None = Field(default=None, alias="modelId")
    output_key: str | None = Field(default=None, alias="outputKey")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    total_time: str | None = Field(default=None, alias="totalTime")
    raw_payload: dict[str, Any] | None = Field(default=None, alias="RawPayload")
    payload_type: BTInsightPayloadType | None = Field(default=None, alias="payloadType")
    registry: BTInsightRegistry | None = Field(default=None, alias="Registry")
    content_edited: bool | None = Field(default=None, alias="contentEdited")
