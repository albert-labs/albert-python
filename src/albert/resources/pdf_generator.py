from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel


class PDFTemplate(BaseAlbertModel):
    """The HTML template sources used to render a PDF.

    Each source is an HTML file with Mustache placeholders: ``{{field}}``
    inserts a value, ``{{#list}}...{{/list}}`` repeats a block per item, and
    ``{{{field}}}`` inserts without HTML escaping (needed for image URLs).
    The valid placeholder names are exactly the keys of the ``data`` object
    supplied at render time, using dotted paths for nested values. Label
    payloads pass ``data={"labels": [...]}``, so those templates wrap their
    body in ``{{#labels}}...{{/labels}}`` and read each entity's fields under
    ``{{info.<field>}}``.

    When ``header`` or ``footer`` is set, the pages render with that header or
    footer template. Header and footer templates can show page numbers and
    document metadata via elements with the classes ``pageNumber``,
    ``totalPages``, ``date``, and ``title`` (e.g.
    ``<span class="pageNumber"></span>``).
    """

    body: str
    """URL or S3 path of the Mustache HTML template for the document body."""

    header: str | None = Field(default=None)
    """URL or S3 path of the Mustache HTML template for the page header, optional."""

    footer: str | None = Field(default=None)
    """URL or S3 path of the Mustache HTML template for the page footer, optional."""


class PDFMargin(BaseAlbertModel):
    """Page margins for a rendered PDF, as CSS lengths (e.g. ``"0mm"``, ``"0.5in"``)."""

    top: str | None = Field(default=None)
    """Top margin."""

    bottom: str | None = Field(default=None)
    """Bottom margin."""

    left: str | None = Field(default=None)
    """Left margin."""

    right: str | None = Field(default=None)
    """Right margin."""


class PDFOptions(BaseAlbertModel):
    """Page rendering options for a generated PDF.

    These are the only rendering settings the PDF generator reads; any other
    keys are ignored. Set either ``format`` or an explicit ``width`` and
    ``height`` pair (both must be set for the pair to apply).
    """

    width: str | None = Field(default=None)
    """Page width as a CSS length (e.g. ``"3in"``). Applied together with ``height``."""

    height: str | None = Field(default=None)
    """Page height as a CSS length (e.g. ``"1in"``). Applied together with ``width``."""

    format: str | None = Field(default=None)
    """Named paper format (e.g. ``"A4"``, ``"Letter"``). Alternative to
    ``width``/``height``."""

    margin: PDFMargin | None = Field(default=None)
    """Page margins, optional."""

    landscape: bool | None = Field(default=None)
    """When True, render in landscape orientation."""

    render_background_image: bool | None = Field(default=None, alias="renderBackgroundImage")
    """When True, print CSS background colors and images."""

    hide_header_from_first_page: bool | None = Field(default=None, alias="hideHeaderFromFirstPage")
    """When True and a header template is set, the first page renders without
    the header."""


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

    options: PDFOptions | dict[str, Any] | None = Field(default=None)
    """Page rendering options, optional. See [`PDFOptions`][albert.resources.pdf_generator.PDFOptions]
    for the recognized settings."""

    albert_id: str | None = Field(default=None, alias="albertId")
    """An identifier echoed back in the response, optional."""
