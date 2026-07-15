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
    """Metadata describing the context of a worker job.

    Attributes
    ----------
    parent_type : str | None
        The entity type this job operates on (e.g. ``"inventory"``).
    parent_id : str | None
        The Albert ID of the entity this job is associated with.
    table_name : str | None
        The database table name relevant to the job.
    mapping : dict[str, str] | None
        Column or field mapping used by the job.
    namespace : str | None
        The file namespace for job inputs/outputs.
    s3_input_key : str | None
        The S3 key for the job's input file.
    s3_output_key : str | None
        The S3 key for the job's output file.
    """

    parent_type: str | None = Field(default=None, alias="parentType")
    parent_id: str | None = Field(default=None, alias="parentId")
    table_name: str | None = Field(default=None, alias="tableName")
    mapping: dict[str, str] | None = None
    namespace: str | None = None
    s3_input_key: str | None = Field(default=None, alias="s3InputKey")
    s3_output_key: str | None = Field(default=None, alias="s3OutputKey")


class WorkerJobCreateRequest(BaseAlbertModel):
    """Request payload for creating a new worker job.

    Attributes
    ----------
    job_type : str
        The type of job to create (e.g. ``"importCSV"``).
    metadata : WorkerJobMetadata
        Metadata describing the job context.
    """

    job_type: str = Field(alias="jobType")
    metadata: WorkerJobMetadata


class WorkerJob(BaseAlbertModel):
    """A background worker job running on the Albert platform.

    Attributes
    ----------
    job_type : str
        The type of the job.
    metadata : WorkerJobMetadata
        Metadata describing the job context.
    status : Status | str | None
        The status of the job.
    state : WorkerJobState
        The current state of the job (e.g. inProgress, successful, failed).
    state_message : str | None
        An optional message describing the current state or error.
    albert_id : str | None
        The Albert ID assigned to the job.
    created : datetime | None
        The timestamp when the job was created.
    modified : datetime | None
        The timestamp when the job was last modified.
    created_audit : AuditFields | None
        Audit fields for job creation.
    updated_audit : AuditFields | None
        Audit fields for the last job update.
    started_audit : AuditFields | None
        Audit fields for when the job started.
    completed_audit : AuditFields | None
        Audit fields for when the job completed.
    """

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
