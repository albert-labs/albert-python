from datetime import date
from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import AttachmentId
from albert.core.shared.models.base import BaseResource, EntityLinkWithName
from albert.resources.hazards import HazardStatement, HazardSymbol


class AttachmentCategory(str, Enum):
    """The kind of file an attachment represents.

    ``OTHER``, ``SDS``, ``LABEL``, and ``SCRIPT`` are the original, fully supported
    categories. All other categories are currently in beta and are only intended
    for use with
    [`upload_and_attach_document_to_inventory_item`][albert.collections.attachments.AttachmentCollection.upload_and_attach_document_to_inventory_item].

    !!! warning "Beta Feature!"
        Categories other than ``OTHER``, ``SDS``, ``LABEL``, and ``SCRIPT`` are in beta.
        Please do not use them in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!
    """

    OTHER = "Other"
    """A general-purpose file with no specialized handling."""
    SDS = "SDS"
    """A Safety Data Sheet document, typically carrying hazard metadata."""
    LABEL = "Label"
    """A product or container label."""
    SCRIPT = "Script"
    """An executable or automation script."""
    ALLERGEN = "Allergen"
    """An allergen statement document."""
    ANIMAL_DERIVED = "AnimalDerived"
    """An animal-derived materials declaration."""
    BMR = "BMR"
    """A batch manufacturing record."""
    BROCHURE = "Brochure"
    """A product or marketing brochure."""
    CHANGE_NOTIFICATION = "ChangeNotification"
    """A change notification document."""
    COA = "CoA"
    """A certificate of analysis."""
    EPD = "EPD"
    """An environmental product declaration."""
    FOOD_CONTACT = "FoodContact"
    """A food contact compliance letter."""
    MFR = "MFR"
    """A master formula record."""
    NDA = "NDA"
    """An NDA or confidentiality agreement."""
    PATENT = "Patent"
    """A patent document."""
    PCF = "PCF"
    """A product carbon footprint document."""
    RELIGIOUS_ORGANIC_CERT = "ReligiousOrganicCert"
    """A Halal, Kosher, or organic certification."""
    RSL = "RSL"
    """An RSL compliance letter."""
    SUPPLIER_QUESTIONNAIRE = "SupplierQuestionnaire"
    """A supplier questionnaire document."""
    TDS = "TDS"
    """A technical data sheet."""


class AttachmentMetadata(BaseAlbertModel):
    """Optional safety and classification metadata for an attachment.

    Populated primarily for SDS attachments (see
    [`upload_and_attach_sds_to_inventory_item`][albert.collections.attachments.AttachmentCollection.upload_and_attach_sds_to_inventory_item])."""

    symbols: list[HazardSymbol] | None = Field(default=None, alias="Symbols")
    """Hazard pictograms/symbols associated with the material."""

    un_number: str | None = Field(default=None, alias="unNumber")
    """The UN number identifying the hazardous substance."""

    storage_class: str | None = Field(default=None, alias="storageClass")
    """The storage class code for the material."""

    storage_class_name: str | None = Field(default=None, alias="storageClassName", frozen=True)
    """The human-readable storage class name. Read-only."""

    hazard_statement: list[HazardStatement] | None = Field(default=None, alias="hazardStatement")
    """Hazard statements (e.g. H-phrases) for the material."""

    jurisdiction: str | None = Field(default=None, frozen=True)
    """The resolved jurisdiction name. Read-only."""

    language: str | None = Field(default=None, frozen=True)
    """The resolved language name. Read-only."""

    jurisdiction_code: str | None = Field(default=None, alias="jurisdictionCode")
    """The jurisdiction code for the document (e.g. ``"US"``)."""

    language_code: str | None = Field(default=None, alias="languageCode")
    """The language code for the document (e.g. ``"EN"``)."""

    wgk: str | None = None
    """The German water hazard class (Wassergefährdungsklasse) classification."""

    description: str | None = None
    """A free-text description of the attachment."""

    extensions: list[EntityLinkWithName] | None = None
    """Links to related extension entities."""


class Attachment(BaseResource):
    """A record linking an uploaded file to a parent entity in Albert.

    Attachments associate a stored file with a parent entity such as a Note,
    Task, Project, or Inventory Item. The file itself is uploaded through the
    [`FileCollection`][albert.collections.files.FileCollection]; the attachment's ``key``
    must match the stored [`name`][albert.resources.files.FileInfo.name].
    Attachments are managed through the
    [`AttachmentCollection`][albert.collections.attachments.AttachmentCollection].

    !!! example
        ```python
        from albert.resources.attachments import Attachment
        attachment = Attachment(
            parent_id="INVA9999999",
            name="datasheet.pdf",
            key="INVA9999999/documents/datasheet.pdf",
        )
        ```"""

    id: AttachmentId | None = Field(default=None, alias="albertId")
    """The Albert ID of the attachment (format ``ATT...``). Assigned by Albert when the attachment is created."""

    parent_id: str = Field(..., alias="parentId")
    """The ID of the entity the file is attached to. Must include the full entity prefix (e.g. ``"INVA9999999"``)."""

    name: str
    """The display name of the attached file."""

    key: str
    """The storage key of the underlying file; matches the uploaded file's name."""

    namespace: str = Field(default="result", alias="nameSpace")
    """The storage namespace of the file. Defaults to ``"result"``."""

    category: AttachmentCategory | str | None = None
    """The kind of file (e.g. SDS, Label). See [`AttachmentCategory`][albert.resources.attachments.AttachmentCategory]."""

    revision_date: date | None = Field(default=None, alias="revisionDate")
    """The revision date of the document, when applicable (e.g. for SDS files)."""

    file_size: int | None = Field(default=None, alias="fileSize", exclude=True, frozen=True)
    """The size of the file in bytes. Read-only."""

    mime_type: str | None = Field(default=None, alias="mimeType", exclude=True, frozen=True)
    """The MIME type of the file. Read-only."""

    signed_url: str | None = Field(default=None, alias="signedURL", exclude=True, frozen=True)
    """A temporary signed download URL. Read-only."""

    signed_url_v2: str | None = Field(default=None, alias="signedURLV2", exclude=True, frozen=True)
    """A temporary signed download URL (v2). Read-only."""

    metadata: AttachmentMetadata | None = Field(default=None, alias="Metadata")
    """Optional safety and classification metadata. See [`AttachmentMetadata`][albert.resources.attachments.AttachmentMetadata]."""


# TO DO: Script and SDS attachment
