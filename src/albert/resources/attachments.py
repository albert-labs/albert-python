from datetime import date
from enum import Enum

from pydantic import Field

from albert.core.shared.identifiers import AttachmentId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


class AttachmentCategory(str, Enum):
    OTHER = "Other"
    SDS = "SDS"
    LABEL = "Label"
    SCRIPT = "Script"


class Attachment(BaseResource):
    """Used for attching files to Notes on Tasks, Projects, Inventory, etc.
    Key should match File.name"""

    id: AttachmentId | None = Field(default=None, alias="albertId")
    parent_id: str = Field(..., alias="parentId")
    name: str
    key: str
    namespace: str = Field(default="result", alias="nameSpace")
    category: AttachmentCategory | None = None
    revision_date: date | None = Field(default=None, alias="revisionDate")
    file_size: int | None = Field(default=None, alias="fileSize", exclude=True, frozen=True)
    mime_type: str | None = Field(default=None, alias="mimeType", exclude=True, frozen=True)
    signed_url: str | None = Field(default=None, alias="signedURL", exclude=True, frozen=True)
    signed_url_v2: str | None = Field(default=None, alias="signedURLV2", exclude=True, frozen=True)
    metadata: dict[str, MetadataItem] | None = Field(
        default=None, alias="Metadata", exclude=True, frozen=True
    )


# TO DO: Script and SDS attachment
