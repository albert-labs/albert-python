from datetime import date
from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import AttachmentId
from albert.core.shared.models.base import BaseResource, EntityLinkWithName
from albert.core.shared.types import MetadataItem
from albert.resources.hazards import HazardStatement, HazardSymbol


class AttachmentCategory(str, Enum):
    OTHER = "Other"
    SDS = "SDS"
    LABEL = "Label"
    SCRIPT = "Script"


class AttachmentMetadata(BaseAlbertModel):
    symbols: list[HazardSymbol] | None = Field(default=None, alias="Symbols")
    un_number: str | None = Field(default=None, alias="unNumber")
    storage_class: str | None = Field(default=None, alias="storageClass")
    storage_class_name: str | None = Field(default=None, alias="storageClassName", frozen=True)
    hazard_statement: list[HazardStatement] | None = Field(default=None, alias="hazardStatement")
    jurisdiction: str | None = Field(default=None, frozen=True)
    language: str | None = Field(default=None, frozen=True)
    jurisdiction_code: str | None = Field(default=None, alias="jurisdictionCode")
    language_code: str | None = Field(default=None, alias="languageCode")
    wgk: str | None = None
    description: str | None = None
    extensions: list[EntityLinkWithName] | None = None


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
    metadata: AttachmentMetadata | dict[str, MetadataItem | list[dict[str, Any]]] | None = Field(
        default=None, alias="Metadata"
    )


# TO DO: Script and SDS attachment
