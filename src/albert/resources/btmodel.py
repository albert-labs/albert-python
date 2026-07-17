from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import BTDatasetId, BTModelId, BTModelSessionId
from albert.core.shared.models.base import BaseResource


class BTModelSessionCategory(str, Enum):
    """Who built a Breakthrough model session.

    Attributes
    ----------
    USER_MODEL : str
        A session built by a user.
    ALBERT_MODEL : str
        A session built automatically by Albert.
    """

    USER_MODEL = "userModel"
    ALBERT_MODEL = "albertModel"


class BTModelRegistry(BaseAlbertModel):
    """Build logs and metrics recorded for a model session."""

    build_logs: dict[str, Any] | None = Field(None, alias="BuildLogs")
    """Free-form logs captured while the session's models were built."""
    metrics: dict[str, Any] | None = Field(None, alias="Metrics")
    """Free-form performance metrics recorded for the session's models."""


class BTModelSession(BaseResource, protected_namespaces=()):
    """A parent session grouping a related set of Breakthrough models.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. A model session ties
    together the models produced from a single dataset
    ([`BTDataset`][albert.resources.btdataset.BTDataset]) in one modeling run. The
    individual models are represented by [`BTModel`][albert.resources.btmodel.BTModel] and managed through
    [`BTModelSessionCollection`][albert.collections.btmodel.BTModelSessionCollection] and
    [`BTModelCollection`][albert.collections.btmodel.BTModelCollection].

    !!! example
        ```python
        from albert.resources.btmodel import BTModelSession, BTModelSessionCategory

        session = BTModelSession(
            name="Tensile strength study",
            category=BTModelSessionCategory.USER_MODEL,
            dataset_id="DST1",
        )
        ```"""

    name: str
    """Human-readable name of the session."""
    category: BTModelSessionCategory
    """Whether the session was built by a user or by Albert."""
    id: BTModelSessionId | None = Field(default=None)
    """Unique identifier of the session (format ``MDS...``). Assigned by Albert on creation."""
    dataset_id: BTDatasetId = Field(..., alias="datasetId")
    """Identifier of the dataset the session's models are built from (format ``DST...``)."""
    default_model: str | None = Field(default=None, alias="defaultModel")
    """Name of the session's default model, if one is designated."""
    total_time: str | None = Field(default=None, alias="totalTime")
    """Total time taken to build the session, if recorded."""
    model_count: int | None = Field(default=None, alias="modelCount")
    """Number of models contained in the session, if reported."""
    target: list[str] | None = Field(default=None)
    """The target variable(s) the session's models predict."""
    registry: BTModelRegistry | None = Field(default=None, alias="Registry")
    """Build logs and metrics recorded for the session."""
    albert_model_details: dict[str, Any] | None = Field(default=None, alias="albertModelDetails")
    """Details specific to an Albert-built session, when applicable."""
    flag: bool = Field(default=False)
    """Boolean marker on the session. Defaults to False."""


class BTModelType(str, Enum):
    """Whether a model belongs to a session or stands alone.

    Attributes
    ----------
    SESSION : str
        A model that belongs to a parent model session.
    DETACHED : str
        A standalone model with no parent session.
    """

    SESSION = "Session"
    DETACHED = "Detached"


class BTModelState(str, Enum):
    """Progress state of a Breakthrough model build.

    Attributes
    ----------
    QUEUED : str
        The build has been queued but has not started.
    BUILDING_MODELS : str
        Models are being trained.
    GENERATING_CANDIDATES : str
        Candidate solutions are being generated.
    COMPLETE : str
        The build has finished successfully.
    ERROR : str
        The build failed.
    """

    QUEUED = "Queued"
    BUILDING_MODELS = "Building Models"
    GENERATING_CANDIDATES = "Generating Candidates"
    COMPLETE = "Complete"
    ERROR = "Error"


class BTModel(BaseResource, protected_namespaces=()):
    """A single trained Breakthrough model.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. A model can belong to a
    parent session ([`BTModelSession`][albert.resources.btmodel.BTModelSession]), in which case ``parent_id`` is set to
    the session ID, or be a detached, standalone model. Models are managed through
    [`BTModelCollection`][albert.collections.btmodel.BTModelCollection].

    !!! example
        ```python
        from albert.resources.btmodel import BTModel

        model = BTModel(name="Random forest v1")
        ```"""

    name: str
    """Human-readable name of the model."""
    id: BTModelId | None = Field(default=None)
    """Unique identifier of the model (format ``MDL...``). Assigned by Albert on creation."""
    dataset_id: BTDatasetId | None = Field(default=None, alias="datasetId")
    """Identifier of the dataset the model is built from (format ``DST...``)."""
    parent_id: BTModelSessionId | None = Field(default=None, alias="parentId")
    """Identifier of the parent session (format ``MDS...``), or None if the model is detached."""
    metadata: dict[str, Any] | None = Field(default=None, alias="Metadata")
    """Free-form metadata associated with the model."""
    type: BTModelType | None = Field(default=None)
    """Whether the model belongs to a session or is detached."""
    state: BTModelState | None = Field(default=None)
    """Current progress state of the model build."""
    target: list[str] | None = Field(default=None)
    """The target variable(s) the model predicts."""
    start_time: str | None = Field(default=None, alias="startTime")
    """When the model build started, if recorded."""
    end_time: str | None = Field(default=None, alias="endTime")
    """When the model build finished, if recorded."""
    total_time: str | None = Field(default=None, alias="totalTime")
    """Total time taken to build the model, if recorded."""
    model_binary_key: str | None = Field(default=None, alias="modelBinaryKey")
    """Storage key for the trained model artifact, if applicable."""
    flag: bool = Field(default=False)
    """Boolean marker on the model. Defaults to False."""
