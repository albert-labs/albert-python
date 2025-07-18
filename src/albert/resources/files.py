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
    name: str
    namespace: FileNamespace
    content_type: str = Field(..., alias="contentType")
    metadata: list[dict[str, str]] | None = Field(default=None)
    category: FileCategory | None = Field(default=None)
    url: str | None = Field(default=None)


class SignURLPOST(BaseAlbertModel):
    files: list[SignURLPOSTFile]


class FileInfo(BaseAlbertModel):
    name: str
    size: int
    etag: str
    namespace: FileNamespace | None = Field(default=None)
    content_type: str = Field(..., alias="contentType")
    last_modified: datetime = Field(..., alias="lastModified")
    metadata: list[dict[str, str]] = Field(..., default_factory=list)
