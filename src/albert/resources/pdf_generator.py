from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel


class PDFTemplate(BaseAlbertModel):
    """The HTML template sources used to render a PDF."""

    body: str
    """URL or S3 path of the Mustache HTML template for the document body."""

    header: str | None = Field(default=None)
    """URL or S3 path of the Mustache HTML template for the page header, optional."""

    footer: str | None = Field(default=None)
    """URL or S3 path of the Mustache HTML template for the page footer, optional."""


class PDFS3Storage(BaseAlbertModel):
    """The storage destination for a generated PDF."""

    bucket: str = Field(alias="Bucket")
    """The S3 bucket the generated PDF is stored in."""

    key: str = Field(alias="Key")
    """The S3 object key the generated PDF is stored under."""

    acl: str | None = Field(default=None, alias="ACL")
    """The S3 ACL applied to the generated PDF, optional."""

    force_overwrite: bool | None = Field(default=None, alias="forceOverwrite")
    """When True, regenerate the PDF even if a cached copy already exists."""


class PDFGenerationRequest(BaseAlbertModel):
    """A request to render a PDF from HTML templates and data.

    The ``template`` HTML is rendered with ``data`` using Mustache placeholders,
    printed to PDF, and stored at the ``s3_storage`` destination.
    """

    template: PDFTemplate
    """The HTML template sources to render."""

    data: dict[str, Any] = Field(default_factory=dict)
    """The values substituted into the template's Mustache placeholders."""

    s3_storage: PDFS3Storage = Field(alias="s3Storage")
    """Where the generated PDF is stored."""

    options: dict[str, Any] | None = Field(default=None)
    """Page rendering options such as ``width``, ``height``, ``format``,
    ``margin``, and ``landscape``, optional."""

    albert_id: str | None = Field(default=None, alias="albertId")
    """An identifier echoed back in the response, optional."""
