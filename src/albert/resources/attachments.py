from enum import Enum
from typing import Literal

from pydantic import Field

from albert.resources.base import BaseResource


class AttachmentCategory(str, Enum):
    OTHER = "Other"
    SDS = "SDS"
    LABEL = "Label"
    SCRIPT = "Script"


class Attachment(BaseResource):
    """Used for attching files to Notes on Tasks, Projects, Inventory, etc.
    Key should match File.name"""

    id: str | None = Field(default=None, alias="albertId")
    parent_id: str = Field(..., alias="parentId")
    name: str
    key: str
    namespace: str = Field(default="result", alias="nameSpace")
    category: Literal[AttachmentCategory.OTHER] | None = None
    file_size: int | None = Field(default=None, alias="fileSize", exclude=True, frozen=True)
    mime_type: str | None = Field(default=None, alias="mimeType", exclude=True, frozen=True)
    signed_url: str | None = Field(default=None, alias="signedURL", exclude=True, frozen=True)
    signed_url_v2: str | None = Field(default=None, alias="signedURLV2", exclude=True, frozen=True)
    metadata: dict[str, str] | None = Field(
        default=None, alias="Metadata", exclude=True, frozen=True
    )


# TO DO: Script and SDS attachment
