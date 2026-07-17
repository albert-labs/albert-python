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
    """Metadata describing the context of a worker job."""

    parent_type: str | None = Field(default=None, alias="parentType")
    """The entity type this job operates on (e.g. ``"inventory"``)."""

    parent_id: str | None = Field(default=None, alias="parentId")
    """The Albert ID of the entity this job is associated with."""

    table_name: str | None = Field(default=None, alias="tableName")
    """The database table name relevant to the job."""

    mapping: dict[str, str] | None = None
    """Column or field mapping used by the job."""

    namespace: str | None = None
    """The file namespace for job inputs/outputs."""

    s3_input_key: str | None = Field(default=None, alias="s3InputKey")
    """The S3 key for the job's input file."""

    s3_output_key: str | None = Field(default=None, alias="s3OutputKey")
    """The S3 key for the job's output file."""


class WorkerJobCreateRequest(BaseAlbertModel):
    """Request payload for creating a new worker job."""

    job_type: str = Field(alias="jobType")
    """The type of job to create (e.g. ``"importCSV"``)."""

    metadata: WorkerJobMetadata
    """Metadata describing the job context."""


class WorkerJob(BaseAlbertModel):
    """A background worker job running on the Albert platform."""

    job_type: str = Field(alias="jobType")
    """The type of the job."""

    metadata: WorkerJobMetadata
    """Metadata describing the job context."""

    status: Status | str | None = None
    """The status of the job."""

    state: WorkerJobState
    """The current state of the job (e.g. inProgress, successful, failed)."""

    state_message: str | None = Field(default=None, alias="stateMessage")
    """An optional message describing the current state or error."""

    albert_id: str | None = Field(default=None, alias="albertId")
    """The Albert ID assigned to the job."""

    created: datetime | None = None
    """The timestamp when the job was created."""

    modified: datetime | None = None
    """The timestamp when the job was last modified."""

    created_audit: AuditFields | None = Field(default=None, alias="Created")
    """Audit fields for job creation."""

    updated_audit: AuditFields | None = Field(default=None, alias="Updated")
    """Audit fields for the last job update."""

    started_audit: AuditFields | None = Field(default=None, alias="Started")
    """Audit fields for when the job started."""

    completed_audit: AuditFields | None = Field(default=None, alias="Completed")
    """Audit fields for when the job completed."""
