from datetime import date
from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import AttachmentId
from albert.core.shared.models.base import BaseResource, EntityLinkWithName
from albert.resources.hazards import HazardStatement, HazardSymbol


class AttachmentCategory(str, Enum):
    OTHER = "Other"
    SDS = "SDS"
    LABEL = "Label"
    SCRIPT = "Script"


class AttachmentMetadata(BaseAlbertModel):
    """Supplemental metadata stored with an attachment.

    Attributes
    ----------
    symbols : list[HazardSymbol] | None
        Hazard pictogram symbols associated with the attachment.
    un_number : str | None
        UN number for hazardous-material documents.
    storage_class : str | None
        Storage class identifier.
    storage_class_name : str | None
        Human-readable name of the storage class. Read-only.
    hazard_statement : list[HazardStatement] | None
        Hazard statements associated with the attachment.
    jurisdiction : str | None
        Jurisdiction for the document. Read-only.
    language : str | None
        Language of the document. Read-only.
    jurisdiction_code : str | None
        Machine-readable jurisdiction code.
    language_code : str | None
        Machine-readable language code.
    wgk : str | None
        German Water Hazard Class (WGK) value.
    description : str | None
        Description of the attachment content.
    extensions : list[EntityLinkWithName] | None
        Additional entity links associated with this attachment.
    """

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
    """A file attached to an entity such as a Note, Task, Project, or Inventory item.

    Attributes
    ----------
    id : AttachmentId | None
        The Albert ID of the attachment.
    parent_id : str
        The Albert ID of the entity this attachment belongs to.
    name : str
        The display name of the attachment.
    key : str
        The storage key of the attached file. Must match the ``name`` of the corresponding
        uploaded File.
    namespace : str
        The file namespace. Defaults to ``"result"``.
    category : AttachmentCategory | None
        The category of the attachment (e.g. ``SDS``, ``Label``, ``Script``, ``Other``).
    revision_date : date | None
        The revision date of the attached document.
    file_size : int | None
        The size of the file in bytes. Read-only.
    mime_type : str | None
        The MIME type of the file. Read-only.
    signed_url : str | None
        A pre-signed download URL for the file. Read-only.
    signed_url_v2 : str | None
        An alternate pre-signed download URL. Read-only.
    metadata : AttachmentMetadata | None
        Additional metadata (e.g. hazard symbols for SDS attachments).
    """

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
    metadata: AttachmentMetadata | None = Field(default=None, alias="Metadata")


# TO DO: Script and SDS attachment
