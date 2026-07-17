from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.shared.models.base import BaseAlbertModel, BaseResource
from albert.resources.pdf_generator import PDFS3Storage, PDFTemplate


class LabelTemplateType(str, Enum):
    """The type of a label template, describing what it renders.

    Attributes
    ----------
    BATCH : str
        Product/Formula lot labels.
    PROPERTY : str
        Property task labels.
    INVENTORY : str
        Inventory lot labels.
    BATCH_LABEL : str
        Batch task labels.
    FORMULA_REPORT : str
        Product/Formula reports.
    BATCH_TEMPLATE : str
        Batch task templates.
    PROPERTY_TASK_REPORT : str
        Property task reports.
    GENERAL_TASK_LABEL : str
        General task labels.
    """

    BATCH = "batch"
    PROPERTY = "property"
    INVENTORY = "inventory"
    BATCH_LABEL = "batchlabel"
    FORMULA_REPORT = "formulareport"
    BATCH_TEMPLATE = "batchtemplate"
    PROPERTY_TASK_REPORT = "propertytaskreport"
    GENERAL_TASK_LABEL = "generaltasklabel"


class LabelTemplate(BaseResource):
    """A label template in the Albert platform.

    A label template pairs a tenant-scoped Mustache HTML file with page
    rendering options. Templates drive the printable outputs in Albert, such
    as inventory lot barcode labels, batch task labels, and formula reports.
    Label Template IDs use the ``TMP`` prefix.

    See [`LabelTemplateCollection`][albert.collections.label_templates.LabelTemplateCollection]
    for creating, retrieving, and rendering label templates.
    """

    id: str | None = Field(default=None, alias="albertId")
    """The Albert ID of the label template (format ``TMP...``)."""

    name: str = Field(min_length=1, max_length=255)
    """The display name of the template. Unique per tenant."""

    description: str | None = Field(default=None)
    """A human-readable description of the template, optional."""

    type: LabelTemplateType | None = Field(default=None)
    """The type of output the template renders (e.g. ``inventory`` for
    inventory lot labels)."""

    template_file: str | None = Field(default=None, alias="templateFile", max_length=500)
    """The file name of the Mustache HTML template stored for the tenant
    (e.g. ``"my-label.html"``)."""

    default: bool | None = Field(default=None)
    """When True, this template is the tenant default for its type."""

    custom_ui_type: str | None = Field(default=None, alias="customUiType", frozen=True)
    """The display name of the template type shown in the UI. Read-only."""

    metadata: dict[str, Any] | None = Field(default=None)
    """Page rendering options and template settings, such as ``width``,
    ``height``, ``margin``, and header/footer file names, optional."""


class LabelPrintPayload(BaseAlbertModel):
    """The assembled render payload for printing a label.

    Contains everything needed to generate the final PDF: the resolved
    template file URLs, the label data for each entity, page options, and the
    storage destination. Pass these fields to
    [`generate_pdf`][albert.collections.pdf_generator.PDFGeneratorCollection.generate_pdf]
    to render the PDF, or use
    [`generate_label_pdf`][albert.collections.label_templates.LabelTemplateCollection.generate_label_pdf]
    to do both steps in one call.
    """

    template: PDFTemplate
    """The resolved template file URLs. ``template.body`` is the URL of the
    tenant's Mustache HTML file."""

    data: dict[str, Any] = Field(default_factory=dict)
    """The label data rendered into the template. For labels this contains a
    ``labels`` list with one entry per printed entity, whose fields the
    template reads under ``info`` (e.g. ``{{info.inventoryName}}``)."""

    s3_storage: PDFS3Storage = Field(alias="s3Storage")
    """The storage destination for the generated PDF."""

    options: dict[str, Any] | None = Field(default=None)
    """Page rendering options such as ``width``, ``height``, and ``margin``,
    optional."""

    metadata: Any | None = Field(default=None)
    """Template settings parsed from the template file's metadata block,
    optional."""

    manual_fields: Any | None = Field(default=None, alias="manualFields")
    """Fields the template expects the user to fill in manually, optional."""
