from datetime import datetime
from enum import Enum

from pydantic import Field

from albert.utils.types import BaseAlbertModel


class FileNamespace(str, Enum):
    AGENT = "agent"
    BREAKTHROUGH = "breakthrough"
    PIPELINE = "pipeline"
    PUBLIC = "public"
    RESULT = "result"
    SDS = "sds"


class FileInfo(BaseAlbertModel):
    name: str
    size: int
    etag: str
    namespace: FileNamespace | None = Field(default=None)
    content_type: str = Field(..., alias="contentType")
    last_modified: datetime = Field(..., alias="lastModified")
    metadata: list[dict[str, str]] = Field(..., default_factory=list)
