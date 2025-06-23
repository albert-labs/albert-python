from enum import Enum
from typing import Any

from pydantic import Field

from albert.resources.base import BaseResource
from albert.resources.identifiers import BTDatasetId, BTModelId, BTModelSessionId
from albert.utils.types import BaseAlbertModel


class BTModelSessionCategory(str, Enum):
    """Enumeration for BTModelSession categories."""

    USER_MODEL = "userModel"
    ALBERT_MODEL = "albertModel"


class BTModelRegistry(BaseAlbertModel):
    """Registry for BTModelSession."""

    build_logs: dict[str, Any] | None = Field(None, alias="BuildLogs")
    metrics: dict[str, Any] | None = Field(None, alias="Metrics")


class BTModelSession(BaseResource, protected_namespaces=()):
    """Parent session for a set of BTModels.

    Attributes
    ----------
    name : str
        The name of the model session.
    category : BTModelSessionCategory
        The category of the model session (e.g., userModel, albertModel).
    id : BTModelSessionId | None
        The unique identifier for the model session.
    dataset_id : BTDatasetId
        The identifier for the dataset associated with the model session.
    default_model : str | None
        The default model name for the session, if applicable.
    total_time : str | None
        The total time taken for the session, if applicable.
    model_count : int | None
        The number of models in the session, if applicable.
    target : list[str] | None
        The target variables for the models in the session, if applicable.
    registry : BTModelRegistry | None
        The registry containing build logs and metrics for the session, if applicable.
    albert_model_details : dict[str, Any] | None
        Details specific to the Albert model, if applicable.
    """

    name: str
    category: BTModelSessionCategory
    id: BTModelSessionId | None = Field(default=None)
    dataset_id: BTDatasetId = Field(..., alias="datasetId")
    default_model: str | None = Field(default=None, alias="defaultModel")
    total_time: str | None = Field(default=None, alias="totalTime")
    model_count: int | None = Field(default=None, alias="modelCount")
    target: list[str] | None = Field(default=None)
    registry: BTModelRegistry | None = Field(default=None, alias="Registry")
    albert_model_details: dict[str, Any] | None = Field(default=None, alias="albertModelDetails")
    flag: bool = Field(default=False)


class BTModelType(str, Enum):
    """Enumeration for BTModel types."""

    SESSION = "Session"
    DETACHED = "Detached"


class BTModelState(str, Enum):
    """Enumeration for BTModel states."""

    QUEUED = "Queued"
    BUILDING_MODELS = "Building Models"
    GENERATING_CANDIDATES = "Generating Candidates"
    COMPLETE = "Complete"
    ERROR = "Error"


class BTModel(BaseResource, protected_namespaces=()):
    """A single Breakthrough model.

    A BTModel may have a `parent_id` or be a detached, standalone model.

    Attributes
    ----------
    name : str
        The name of the model.
    id : BTModelId | None
        The unique identifier for the model.
    dataset_id : BTDatasetId | None
        The identifier for the dataset associated with the model.
    parent_id : BTModelSessionId | None
        The identifier for the parent model session, if applicable.
    metadata : dict[str, Any] | None
        Metadata associated with the model, if applicable.
    type : BTModelType | None
        The type of the model (e.g., Session, Detached).
    state : BTModelState | None
        The current state of the model (e.g., Queued, Building Models, Complete).
    target : list[str] | None
        The target variables for the model, if applicable.
    start_time : str | None
        The start time of the model creation, if applicable.
    end_time : str | None
        The end time of the model creation, if applicable.
    total_time : str | None
        The total time taken for the model creation, if applicable.
    model_binary_key : str | None
        The storage key for the model data, if applicable.
    """

    name: str
    id: BTModelId | None = Field(default=None)
    dataset_id: BTDatasetId | None = Field(default=None, alias="datasetId")
    parent_id: BTModelSessionId | None = Field(default=None, alias="parentId")
    metadata: dict[str, Any] | None = Field(default=None, alias="Metadata")
    type: BTModelType | None = Field(default=None)
    state: BTModelState | None = Field(default=None)
    target: list[str] | None = Field(default=None)
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    total_time: str | None = Field(default=None, alias="totalTime")
    model_binary_key: str | None = Field(default=None, alias="modelBinaryKey")
    flag: bool = Field(default=False)
