from enum import Enum
from typing import Any

from pydantic import Field

from albert.exceptions import AlbertException
from albert.resources.base import BaseResource, BaseSessionResource
from albert.utils.types import BaseAlbertModel


class BTModelCategory(str, Enum):
    USER_MODEL = "userModel"
    ALBERT_MODEL = "albertModel"


class BTModelState(str, Enum):
    QUEUED = "Queued"
    BUILDING_MODELS = "Building Models"
    GENERATING_CANDIDATES = "Generating Candidates"
    COMPLETE = "Complete"
    ERROR = "Error"


class BTModelRegistry(BaseAlbertModel):
    build_logs: dict[str, Any] | None = Field(None, alias="BuildLogs")
    metrics: dict[str, Any] | None = Field(None, alias="Metrics")


class BTModelSession(BaseSessionResource, protected_namespaces=()):
    name: str
    category: BTModelCategory
    dataset_id: str = Field(..., alias="datasetId")
    id: str | None = Field(default=None)
    default_model: str | None = Field(default=None, alias="defaultModel")
    total_time: str | None = Field(default=None, alias="totalTime")
    model_count: int | None = Field(default=None, alias="modelCount")
    target: list[str] | None = Field(default=None)
    registry: BTModelRegistry | None = Field(default=None, alias="Registry")
    albert_model_details: dict[str, Any] | None = Field(default=None, alias="albertModelDetails")
    flag: bool = Field(default=False)

    @property
    def models(self):
        from albert.collections.btmodel import BTModelCollection

        if self._session is None:
            raise AlbertException("Parent entity is missing a session.")
        if self.id is None:
            raise AlbertException("Parent entity is missing an Albert ID.")

        return BTModelCollection(session=self._session, parent_id=self.id)


class BTModel(BaseResource, protected_namespaces=()):
    name: str
    target: list[str]
    state: BTModelState
    dataset_id: str = Field(..., alias="datasetId")
    id: str | None = Field(default=None)
    parent_id: str | None = Field(default=None, alias="parentId")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    total_time: str | None = Field(default=None, alias="totalTime")
    model_binary_key: str | None = Field(default=None, alias="modelBinaryKey")
    flag: bool = Field(default=False)
