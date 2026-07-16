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
    """Build logs and metrics recorded for a model session.

    Attributes
    ----------
    build_logs : dict or None
        Free-form logs captured while the session's models were built.
    metrics : dict or None
        Free-form performance metrics recorded for the session's models.
    """

    build_logs: dict[str, Any] | None = Field(None, alias="BuildLogs")
    metrics: dict[str, Any] | None = Field(None, alias="Metrics")


class BTModelSession(BaseResource, protected_namespaces=()):
    """A parent session grouping a related set of Breakthrough models.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. A model session ties
    together the models produced from a single dataset
    ([`BTDataset`][albert.resources.btdataset.BTDataset]) in one modeling run. The
    individual models are represented by [`BTModel`][albert.resources.btmodel.BTModel] and managed through
    [`BTModelSessionCollection`][albert.collections.btmodel.BTModelSessionCollection] and
    [`BTModelCollection`][albert.collections.btmodel.BTModelCollection].

    Attributes
    ----------
    name : str
        Human-readable name of the session.
    category : BTModelSessionCategory
        Whether the session was built by a user or by Albert.
    id : BTModelSessionId or None
        Unique identifier of the session (format ``MDS...``). Assigned by Albert on
        creation.
    dataset_id : BTDatasetId
        Identifier of the dataset the session's models are built from (format
        ``DST...``).
    default_model : str or None
        Name of the session's default model, if one is designated.
    total_time : str or None
        Total time taken to build the session, if recorded.
    model_count : int or None
        Number of models contained in the session, if reported.
    target : list of str or None
        The target variable(s) the session's models predict.
    registry : BTModelRegistry or None
        Build logs and metrics recorded for the session.
    albert_model_details : dict or None
        Details specific to an Albert-built session, when applicable.
    flag : bool
        Boolean marker on the session. Defaults to False.

    !!! example
        ```python
        from albert.resources.btmodel import BTModelSession, BTModelSessionCategory

        session = BTModelSession(
            name="Tensile strength study",
            category=BTModelSessionCategory.USER_MODEL,
            dataset_id="DST1",
        )
        ```
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

    Attributes
    ----------
    name : str
        Human-readable name of the model.
    id : BTModelId or None
        Unique identifier of the model (format ``MDL...``). Assigned by Albert on
        creation.
    dataset_id : BTDatasetId or None
        Identifier of the dataset the model is built from (format ``DST...``).
    parent_id : BTModelSessionId or None
        Identifier of the parent session (format ``MDS...``), or None if the model
        is detached.
    metadata : dict or None
        Free-form metadata associated with the model.
    type : BTModelType or None
        Whether the model belongs to a session or is detached.
    state : BTModelState or None
        Current progress state of the model build.
    target : list of str or None
        The target variable(s) the model predicts.
    start_time : str or None
        When the model build started, if recorded.
    end_time : str or None
        When the model build finished, if recorded.
    total_time : str or None
        Total time taken to build the model, if recorded.
    model_binary_key : str or None
        Storage key for the trained model artifact, if applicable.
    flag : bool
        Boolean marker on the model. Defaults to False.

    !!! example
        ```python
        from albert.resources.btmodel import BTModel

        model = BTModel(name="Random forest v1")
        ```
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
