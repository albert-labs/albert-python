from datetime import datetime
from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel


class FileNamespace(str, Enum):
    """The storage namespace a file lives in."""

    AGENT = "agent"
    """Files used by Albert agents."""
    BREAKTHROUGH = "breakthrough"
    """Files associated with Breakthrough (data science / modeling)."""
    PIPELINE = "pipeline"
    """Files used by data pipelines."""
    PUBLIC = "public"
    """Publicly accessible files."""
    RESULT = "result"
    """Files produced as results and attached to entities (the common default)."""
    SDS = "sds"
    """Safety Data Sheet files."""


class FileCategory(str, Enum):
    """The kind of file being stored."""

    SDS = "SDS"
    """A Safety Data Sheet document."""
    OTHER = "Other"
    """A general-purpose file with no specialized handling."""


class SignURLPOSTFile(BaseAlbertModel):
    """Request entry describing a single file to be signed for upload.

    Used internally to build the payload for
    [`get_signed_upload_url`][albert.collections.files.FileCollection.get_signed_upload_url]."""

    name: str
    """The name (storage key) to store the file under."""

    namespace: FileNamespace
    """The namespace to store the file in."""

    content_type: str = Field(..., alias="contentType")
    """The MIME type of the file."""

    metadata: list[dict[str, str]] | None = Field(default=None)
    """Optional key/value metadata to store with the file."""

    category: FileCategory | None = Field(default=None)
    """The category of the file (e.g. SDS, Other)."""

    url: str | None = Field(default=None)
    """The signed URL returned by the API for this file."""


class SignURLPOST(BaseAlbertModel):
    """Request body wrapping the list of files to sign for upload."""

    files: list[SignURLPOSTFile]
    """The files to request signed upload URLs for."""


class FileInfo(BaseAlbertModel):
    """Metadata about a stored file in Albert.

    Returned by
    [`get_by_name`][albert.collections.files.FileCollection.get_by_name]. Its ``name``
    can be used as the ``key`` of an
    [`Attachment`][albert.resources.attachments.Attachment]."""

    name: str
    """The name (storage key) of the file."""

    size: int
    """The size of the file in bytes."""

    etag: str
    """The storage entity tag (checksum) for the file."""

    namespace: FileNamespace | str | None = Field(default=None)
    """The namespace the file is stored in."""

    content_type: str = Field(..., alias="contentType")
    """The MIME type of the file."""

    last_modified: datetime = Field(..., alias="lastModified")
    """When the file was last modified."""

    metadata: list[dict[str, str]] = Field(..., default_factory=list)
    """Key/value metadata stored with the file."""
