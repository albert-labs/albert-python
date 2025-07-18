from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    BTDatasetId,
    BTInsightId,
    BTModelId,
    BTModelSessionId,
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
    name: str
    category: BTInsightCategory
    metadata: dict[str, Any] | None = Field(default=None, alias="Metadata")
    state: BTInsightState | None = Field(default=None)
    id: BTInsightId | None = Field(default=None, alias="albertId")
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
