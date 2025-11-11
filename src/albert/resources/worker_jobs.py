from datetime import datetime
from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import Status
from albert.core.shared.models.base import AuditFields


class WorkerJobState(str, Enum):
    """Enumerated worker job states returned by the Albert platform."""

    IN_PROGRESS = "inProgress"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUBMITTED = "submitted"


WORKER_JOB_PENDING_STATES: set[WorkerJobState] = {
    WorkerJobState.IN_PROGRESS,
    WorkerJobState.SUBMITTED,
}

WORKER_JOB_TERMINAL_STATES: set[WorkerJobState] = {
    WorkerJobState.SUCCESSFUL,
    WorkerJobState.FAILED,
    WorkerJobState.CANCELLED,
}


class WorkerJobMetadata(BaseAlbertModel):
    parent_type: str | None = Field(default=None, alias="parentType")
    parent_id: str | None = Field(default=None, alias="parentId")
    table_name: str | None = Field(default=None, alias="tableName")
    mapping: dict[str, str] | None = None
    namespace: str | None = None
    s3_input_key: str | None = Field(default=None, alias="s3InputKey")
    s3_output_key: str | None = Field(default=None, alias="s3OutputKey")


class WorkerJobCreateRequest(BaseAlbertModel):
    job_type: str = Field(alias="jobType")
    metadata: WorkerJobMetadata


class WorkerJob(BaseAlbertModel):
    job_type: str = Field(alias="jobType")
    metadata: WorkerJobMetadata
    status: Status | str | None = None
    state: WorkerJobState
    state_message: str | None = Field(default=None, alias="stateMessage")
    albert_id: str | None = Field(default=None, alias="albertId")
    created: datetime | None = None
    modified: datetime | None = None
    created_audit: AuditFields | None = Field(default=None, alias="Created")
    updated_audit: AuditFields | None = Field(default=None, alias="Updated")
    started_audit: AuditFields | None = Field(default=None, alias="Started")
    completed_audit: AuditFields | None = Field(default=None, alias="Completed")
