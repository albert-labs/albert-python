from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import AuditFields


class DocumentState(str, Enum):
    """Lifecycle state of a document version."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DocumentClass(str, Enum):
    """Access class of a document."""

    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentVersion(BaseAlbertModel):
    """A single version entry in a document's version history.

    Each entry represents one version of a document attached to a Data Template.
    Obtain the document ID from
    [`DataTemplate.documents`][albert.resources.data_templates.DataTemplate.documents]
    and pass it to
    [`get_document_version_history`][albert.collections.data_templates.DataTemplateCollection.get_document_version_history].

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        dt = client.data_templates.get_by_id(id="DAT8967")
        for doc in dt.documents:
            for version in client.data_templates.get_document_version_history(
                document_id=doc.id
            ):
                print(version.doc_version, version.state)
        ```
    """

    id: str | None = Field(default=None, alias="albertId")
    """The document ID (format ``DOC...``)."""

    name: str | None = Field(default=None)
    """The document name."""

    name_space: str | None = Field(default=None, alias="nameSpace")
    """The S3 bucket namespace."""

    key: str | None = Field(default=None)
    """The S3 storage path for this version."""

    version_id: str | None = Field(default=None, alias="versionId")
    """The S3 version key for this version."""

    doc_version: int | None = Field(default=None, alias="docVersion")
    """The sequential version number (increments with each new version)."""

    document_class: DocumentClass | None = Field(default=None, alias="class")
    """The access class of the document."""

    state: DocumentState | None = Field(default=None)
    """The lifecycle state of this document version."""

    signed_url: str | None = Field(default=None, alias="signedUrl")
    """A short-lived S3 download URL for this version's file."""

    published_at: str | None = Field(default=None, alias="publishedAt")
    """The timestamp when this version was published, if applicable."""

    created: AuditFields | None = Field(default=None, alias="Created")
    """Who created this version and when."""

    updated: AuditFields | None = Field(default=None, alias="Updated")
    """Who last updated this version and when."""
