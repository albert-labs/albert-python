from enum import Enum
from typing import Any

from pydantic import Field

from albert.resources.base import BaseResource


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


class BTInsight(BaseResource, protected_namespaces=()):
    name: str
    category: BTInsightCategory
    metadata: dict[str, Any] = Field(alias="Metadata")
    state: BTInsightState | None = Field(default=None)
    id: str | None = Field(default=None, alias="albertId")
    dataset_id: str | None = Field(default=None, alias="datasetId")
    model_session_id: str | None = Field(default=None, alias="modelSessionId")
    output_key: str | None = Field(default=None, alias="outputKey")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    total_time: str | None = Field(default=None, alias="totalTime")
    raw_payload: dict[str, Any] | None = Field(default=None, alias="RawPayload")
    payload_type: BTInsightPayloadType | None = Field(default=None, alias="payloadType")
    registry: dict[str, Any] | None = Field(default=None, alias="Registry")
    content_edited: bool | None = Field(default=None, alias="contentEdited")
