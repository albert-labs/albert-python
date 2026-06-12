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
    OPTIMIZER = "Optimizer"
    CUSTOM_OPTIMIZER = "Custom Optimizer"
    IMPACT_CHART = "Impact Chart"
    MOLECULE = "Molecule"
    SMART_DOE = "Smart DOE"
    GENERATE = "Generate"


class BTInsightState(str, Enum):
    QUEUED = "Queued"
    BUILDING_MODELS = "Building Models"
    GENERATING_CANDIDATES = "Generating Candidates"
    COMPLETE = "Complete"
    ERROR = "Error"


class BTInsightPayloadType(str, Enum):
    BREAKTHROUGH = "Breakthrough"
    ALBERTO = "Alberto"


class BTInsightRegistry(BaseAlbertModel):
    """Registry for the BTInsight.

    Registry contains result metadata for the BTInsight.
    Additional attributes can be added to the registry as needed.
    """

    build_logs: dict[str, Any] | None = Field(default=None, alias="BuildLogs")
    metrics: dict[str, Any] | None = Field(default=None, alias="Metrics")
    settings: dict[str, Any] | None = Field(default=None, alias="Settings")


class BTInsight(BaseResource, protected_namespaces=()):
    """A Breakthrough insight result generated from a model or optimization run.

    Attributes
    ----------
    name : str
        The name of the insight.
    category : BTInsightCategory
        The category of the insight (e.g. Optimizer, Impact Chart, Smart DOE).
    metadata : dict[str, Any] | None
        Metadata associated with the insight run.
    state : BTInsightState | None
        The current state of the insight (e.g. Queued, Building Models, Complete, Error).
    id : BTInsightId | None
        The Albert ID of the insight.
    parent_id : ProjectId | None
        The ID of the project this insight belongs to.
    dataset_id : BTDatasetId | None
        The ID of the dataset used to generate this insight.
    model_session_id : BTModelSessionId | None
        The ID of the model session associated with this insight.
    model_id : BTModelId | None
        The ID of the model used to generate this insight.
    output_key : str | None
        The storage key for the insight output file.
    start_time : str | None
        The time the insight run started.
    end_time : str | None
        The time the insight run finished.
    total_time : str | None
        The total elapsed time for the insight run.
    raw_payload : dict[str, Any] | None
        The raw result payload from the insight run.
    payload_type : BTInsightPayloadType | None
        The type of payload (Breakthrough or Alberto).
    registry : BTInsightRegistry | None
        Build logs, metrics, and settings for the insight.
    content_edited : bool | None
        Whether the insight content has been manually edited.
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
