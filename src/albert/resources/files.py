from datetime import datetime
from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel


class FileNamespace(str, Enum):
    AGENT = "agent"
    BREAKTHROUGH = "breakthrough"
    PIPELINE = "pipeline"
    PUBLIC = "public"
    RESULT = "result"
    SDS = "sds"


class FileCategory(str, Enum):
    SDS = "SDS"
    OTHER = "Other"


class SignURLPOSTFile(BaseAlbertModel):
    """Descriptor for a single file to be uploaded via a pre-signed URL.

    Attributes
    ----------
    name : str
        The file name to use in storage.
    namespace : FileNamespace
        The storage namespace for the file.
    content_type : str
        The MIME type of the file.
    metadata : list[dict[str, str]] | None
        Additional key-value metadata to attach to the file.
    category : FileCategory | None
        The file category (e.g. ``SDS``, ``Other``).
    url : str | None
        The pre-signed upload URL returned by the server.
    """

    name: str
    namespace: FileNamespace
    content_type: str = Field(..., alias="contentType")
    metadata: list[dict[str, str]] | None = Field(default=None)
    category: FileCategory | None = Field(default=None)
    url: str | None = Field(default=None)


class SignURLPOST(BaseAlbertModel):
    """Request payload for obtaining pre-signed upload URLs for one or more files.

    Attributes
    ----------
    files : list[SignURLPOSTFile]
        The files to request upload URLs for.
    """

    files: list[SignURLPOSTFile]


class FileInfo(BaseAlbertModel):
    """Metadata about a file stored in Albert.

    Attributes
    ----------
    name : str
        The file name.
    size : int
        The file size in bytes.
    etag : str
        The ETag of the stored file.
    namespace : FileNamespace | None
        The storage namespace the file belongs to.
    content_type : str
        The MIME type of the file.
    last_modified : datetime
        The timestamp when the file was last modified.
    metadata : list[dict[str, str]]
        Key-value metadata attached to the file.
    """

    name: str
    size: int
    etag: str
    namespace: FileNamespace | None = Field(default=None)
    content_type: str = Field(..., alias="contentType")
    last_modified: datetime = Field(..., alias="lastModified")
    metadata: list[dict[str, str]] = Field(..., default_factory=list)
