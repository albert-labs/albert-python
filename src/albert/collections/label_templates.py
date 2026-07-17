import json
from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.pdf_generator import PDFGeneratorCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import (
    InventoryId,
    LabelTemplateId,
    LotId,
    TaskId,
)
from albert.core.utils import ensure_list
from albert.resources.label_templates import (
    LabelPrintPayload,
    LabelTemplate,
    LabelTemplateType,
)


class LabelTemplateCollection(BaseCollection):
    """Manage Label Templates in the Albert platform.

    A label template pairs a tenant-scoped Mustache HTML file with page
    rendering options, and drives printable outputs such as inventory lot
    barcode labels, batch task labels, and formula reports. Label Template
    IDs use the ``TMP`` prefix.

    Printing a label is a two-step flow: [`get_print_payload`][albert.collections.label_templates.LabelTemplateCollection.get_print_payload]
    assembles the label data for an entity (for example a Lot), and
    [`generate_pdf`][albert.collections.pdf_generator.PDFGeneratorCollection.generate_pdf]
    renders it to a stored PDF. Use [`generate_label_pdf`][albert.collections.label_templates.LabelTemplateCollection.generate_label_pdf]
    to run both steps in one call.

    This collection is accessed as ``client.label_templates``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        url = client.label_templates.generate_label_pdf(
            inventory_lot_number_id="LOTB1234",
        )
        # 'https://s3.us-west-2.amazonaws.com/...'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for label template requests.

    Methods
    -------
    create(label_template, template_html=None, header_html=None, footer_html=None) -> LabelTemplate
        Create a new label template, optionally uploading its HTML files.
    get_by_id(id) -> LabelTemplate
        Get a single label template by its ID.
    get_all(...) -> Iterator[LabelTemplate]
        Get all label templates, with optional filters.
    update(label_template) -> LabelTemplate
        Update an existing label template.
    delete(id) -> None
        Delete a label template by its ID.
    get_print_payload(...) -> LabelPrintPayload
        Assemble the render payload for printing a label.
    generate_label_pdf(...) -> str
        Generate a label PDF for a Lot and return its download URL.
    get_batch_label_url(task_id, lot_id=None) -> str
        Generate a hazard batch label PDF for a batch task.
    get_formula_report_url(formula_id, template_id=None, lot_id=None) -> str
        Generate a formula report PDF.
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "template_file", "default", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a LabelTemplateCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{LabelTemplateCollection._api_version}/template"

    @validate_call
    def create(
        self,
        *,
        label_template: LabelTemplate,
        template_html: str | bytes | None = None,
        header_html: str | bytes | None = None,
        footer_html: str | bytes | None = None,
    ) -> LabelTemplate:
        """Create a new label template.

        When HTML content is provided, it is uploaded and stored for the
        tenant alongside the new template. ``template_html`` is stored under
        the ``template_file`` name, and ``header_html`` / ``footer_html`` are
        stored under the ``header`` / ``footer`` file names from the
        template's ``metadata``. Without HTML content, the template record is
        created pointing at an already-stored ``template_file``.

        The HTML file is a complete Mustache HTML document whose body is
        wrapped in a ``{{#labels}} ... {{/labels}}`` section. See the Label
        Templates page in the docs Examples section for the authoring rules
        and available fields.

        !!! example
            ```python
            from pathlib import Path

            from albert.resources.label_templates import LabelTemplate, LabelTemplateType

            template = LabelTemplate(
                name="3x1 Inventory Label",
                type=LabelTemplateType.INVENTORY,
                template_file="3x1-inventory-label.html",
                metadata={"width": "3in", "height": "1in"},
            )
            created = client.label_templates.create(
                label_template=template,
                template_html=Path("3x1-inventory-label.html").read_text(),
            )
            created.id
            # 'TMP123'
            ```

        Parameters
        ----------
        label_template : LabelTemplate
            The label template to create. ``name`` is required; ``type`` and
            ``template_file`` should be set for the template to be usable.
        template_html : str or bytes, optional
            The Mustache HTML content for the template body. Stored under the
            ``template_file`` name.
        header_html : str or bytes, optional
            The Mustache HTML content for the page header. Stored under the
            ``metadata["header"]`` file name.
        footer_html : str or bytes, optional
            The Mustache HTML content for the page footer. Stored under the
            ``metadata["footer"]`` file name.

        Returns
        -------
        LabelTemplate
            The newly created label template, fully populated.

        Raises
        ------
        ValueError
            If HTML content is provided without a corresponding file name on
            the template.
        """
        payload = label_template.model_dump(
            by_alias=True, mode="json", exclude_none=True, exclude_unset=True
        )

        if template_html is None and header_html is None and footer_html is None:
            response = self.session.post(self.base_path, json=payload)
            return self.get_by_id(id=response.json()["albertId"])

        metadata = label_template.metadata or {}
        files = []
        if template_html is not None:
            if not label_template.template_file:
                raise ValueError("`template_file` must be set to upload `template_html`.")
            files.append(("file", (label_template.template_file, template_html, "text/html")))
        if header_html is not None:
            header_file = metadata.get("header")
            if not header_file:
                raise ValueError("`metadata['header']` must be set to upload `header_html`.")
            files.append(("headerFile", (header_file, header_html, "text/html")))
        if footer_html is not None:
            footer_file = metadata.get("footer")
            if not footer_file:
                raise ValueError("`metadata['footer']` must be set to upload `footer_html`.")
            files.append(("footerFile", (footer_file, footer_html, "text/html")))

        response = self.session.post(
            self.base_path,
            files=files,
            data={"templateInfo": json.dumps(payload)},
            # Unset the session's JSON content type so the multipart boundary is used.
            headers={"Content-Type": None},
        )
        return self.get_by_id(id=response.json()["albertId"])

    @validate_call
    def get_by_id(self, *, id: LabelTemplateId) -> LabelTemplate:
        """Get a label template by its ID.

        !!! example
            ```python
            template = client.label_templates.get_by_id(id="TMP123")
            template.name
            # 'Small Inventory Label'
            ```

        Parameters
        ----------
        id : LabelTemplateId
            The Label Template ID (format ``TMP...``).

        Returns
        -------
        LabelTemplate
            The fully populated LabelTemplate.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return LabelTemplate(**response.json())

    @validate_call
    def get_all(
        self,
        *,
        name: str | None = None,
        type: LabelTemplateType | list[LabelTemplateType] | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[LabelTemplate]:
        """Get all label templates, with optional filters.

        Results are returned as a lazily paginated iterator.

        !!! example
            ```python
            from albert.resources.label_templates import LabelTemplateType

            for template in client.label_templates.get_all(
                type=LabelTemplateType.INVENTORY,
            ):
                print(template.id, template.name, template.default)
            ```

        Parameters
        ----------
        name : str, optional
            Filter templates by name.
        type : LabelTemplateType or list[LabelTemplateType], optional
            Filter templates by type (e.g. ``inventory`` for inventory lot
            labels).
        start_key : str, optional
            Provide the ``lastKey`` from a previous request to resume
            pagination.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over
            all matches.

        Returns
        -------
        Iterator[LabelTemplate]
            A lazily paginated iterator of matching label templates.
        """
        params = {
            "name": name,
            "type": ensure_list(type),
            "startKey": start_key,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [LabelTemplate(**item) for item in items],
        )

    @validate_call
    def update(self, *, label_template: LabelTemplate) -> LabelTemplate:
        """Update an existing label template.

        Fetch a template (e.g. via [`get_by_id`][albert.collections.label_templates.LabelTemplateCollection.get_by_id]), modify the updatable
        fields on the returned object, then pass it here. The template is
        matched by its ``id``.

        !!! example
            ```python
            template = client.label_templates.get_by_id(id="TMP123")
            template.name = "Small Inventory Label (2in)"
            updated = client.label_templates.update(label_template=template)
            ```

        Parameters
        ----------
        label_template : LabelTemplate
            The label template to update. Its ``id`` must be set.

        Returns
        -------
        LabelTemplate
            The updated LabelTemplate, re-fetched from Albert.

        Notes
        -----
        The following fields can be updated: ``default``, ``metadata``,
        ``name``, ``template_file``.
        """
        current = self.get_by_id(id=label_template.id)
        patch_payload = self._generate_patch_payload(
            existing=current,
            updated=label_template,
            generate_metadata_diff=False,
        )
        if patch_payload.data:
            self.session.patch(
                f"{self.base_path}/{label_template.id}",
                json=patch_payload.model_dump(mode="json", by_alias=True),
            )
        return self.get_by_id(id=label_template.id)

    @validate_call
    def delete(self, *, id: LabelTemplateId) -> None:
        """Delete a label template by its ID.

        !!! example
            ```python
            client.label_templates.delete(id="TMP123")
            ```

        Parameters
        ----------
        id : LabelTemplateId
            The Label Template ID to delete (format ``TMP...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    @validate_call
    def get_print_payload(
        self,
        *,
        type: LabelTemplateType = LabelTemplateType.INVENTORY,
        inventory_lot_number_id: LotId | list[LotId] | None = None,
        albert_id: InventoryId | None = None,
        task_id: TaskId | None = None,
        lot_id: str | None = None,
        template_id: LabelTemplateId | None = None,
        jurisdiction: str | None = None,
    ) -> LabelPrintPayload:
        """Assemble the render payload for printing a label.

        Gathers everything needed to render the label for the given entity:
        the resolved template file URLs (``payload.template.body`` is the URL
        of the tenant's Mustache HTML file), the per-entity label data
        (including barcode and QR code images), page options, and the storage
        destination. Pass the payload fields to
        [`generate_pdf`][albert.collections.pdf_generator.PDFGeneratorCollection.generate_pdf]
        to render the PDF, or use [`generate_label_pdf`][albert.collections.label_templates.LabelTemplateCollection.generate_label_pdf]
        to do both steps in one call.

        !!! example
            ```python
            payload = client.label_templates.get_print_payload(
                inventory_lot_number_id="LOTB1234",
                template_id="TMP123",
            )
            payload.template.body
            # 'https://s3.us-west-2.amazonaws.com/.../templates/TEN123/small-inventory-label.html'
            ```

        Parameters
        ----------
        type : LabelTemplateType, optional
            The kind of label to assemble. Defaults to ``inventory`` (Lot
            barcode labels). Supported types are ``inventory``, ``batch``,
            ``property``, ``propertytaskreport``, ``batchtemplate``, and
            ``generaltasklabel``; the ``batchlabel`` and ``formulareport``
            types render directly via [`get_batch_label_url`][albert.collections.label_templates.LabelTemplateCollection.get_batch_label_url]
            and [`get_formula_report_url`][albert.collections.label_templates.LabelTemplateCollection.get_formula_report_url] instead.
        inventory_lot_number_id : LotId or list[LotId], optional
            The Lot ID(s) to print (format ``LOT...``). Required when ``type``
            is ``inventory``.
        albert_id : InventoryId, optional
            The Inventory ID (format ``INV...``). Required when ``type`` is
            ``batch``, ``property``, or ``propertytaskreport``.
        task_id : TaskId, optional
            The Task ID (format ``TAS...``). Required when ``type`` is
            ``batch``, ``property``, ``propertytaskreport``,
            ``batchtemplate``, or ``generaltasklabel``.
        lot_id : str, optional
            Restrict property task labels to a specific lot.
        template_id : LabelTemplateId, optional
            The Label Template ID to render with (format ``TMP...``). When not
            provided, the tenant default template for the type is used.
        jurisdiction : str, optional
            The jurisdiction used to select hazard pictograms.

        Returns
        -------
        LabelPrintPayload
            The assembled label render payload.
        """
        params: dict[str, Any] = {
            "type": type,
            "inventoryLotNumberId": ensure_list(inventory_lot_number_id) or None,
            "albertId": albert_id,
            "taskId": task_id,
            "lotId": lot_id,
            "templateId": template_id,
            "jurisdiction": jurisdiction,
        }
        response = self.session.get(f"{self.base_path}/print", params=params)
        return LabelPrintPayload(**response.json())

    @validate_call
    def generate_label_pdf(
        self,
        *,
        inventory_lot_number_id: LotId | list[LotId],
        template_id: LabelTemplateId | None = None,
        jurisdiction: str | None = None,
    ) -> str:
        """Generate a barcode label PDF for one or more Lots.

        Assembles the label data for the given Lot(s) and renders it to a
        stored PDF using the given template (or the tenant default). This is
        the one-call equivalent of [`get_print_payload`][albert.collections.label_templates.LabelTemplateCollection.get_print_payload]
        followed by [`generate_pdf`][albert.collections.pdf_generator.PDFGeneratorCollection.generate_pdf].

        !!! example
            ```python
            url = client.label_templates.generate_label_pdf(
                inventory_lot_number_id="LOTB1234",
                template_id="TMP123",
            )
            # 'https://s3.us-west-2.amazonaws.com/...'
            ```

        Parameters
        ----------
        inventory_lot_number_id : LotId or list[LotId]
            The Lot ID(s) to print (format ``LOT...``).
        template_id : LabelTemplateId, optional
            The Label Template ID to render with (format ``TMP...``). When not
            provided, the tenant default inventory label template is used.
        jurisdiction : str, optional
            The jurisdiction used to select hazard pictograms.

        Returns
        -------
        str
            A short-lived URL for downloading the generated label PDF.
        """
        payload = self.get_print_payload(
            type=LabelTemplateType.INVENTORY,
            inventory_lot_number_id=inventory_lot_number_id,
            template_id=template_id,
            jurisdiction=jurisdiction,
        )
        pdf_generator = PDFGeneratorCollection(session=self.session)
        return pdf_generator.generate_pdf(
            template=payload.template,
            data=payload.data,
            s3_storage=payload.s3_storage,
            options=payload.options,
            albert_id=template_id,
        )

    @validate_call
    def get_batch_label_url(
        self,
        *,
        task_id: TaskId,
        lot_id: str | None = None,
    ) -> str:
        """Generate a hazard batch label PDF for a batch task.

        Renders the GHS-style batch label (hazard pictograms, signal word,
        hazard and precautionary statements) for the formulas on a batch task
        and returns a short-lived URL for the finished PDF. This label type is
        rendered by the platform's document generator rather than from a
        tenant label template file.

        !!! example
            ```python
            url = client.label_templates.get_batch_label_url(task_id="TAS1234")
            # 'https://s3.us-west-2.amazonaws.com/...'
            ```

        Parameters
        ----------
        task_id : TaskId
            The batch Task ID (format ``TAS...``).
        lot_id : str, optional
            A specific lot number to print, when the task produced multiple
            lots.

        Returns
        -------
        str
            A short-lived URL for downloading the generated batch label PDF.
        """
        params = {"taskId": task_id, "lotId": lot_id}
        response = self.session.get(f"{self.base_path}/sds", params=params)
        return response.json()["data"]

    @validate_call
    def get_formula_report_url(
        self,
        *,
        formula_id: InventoryId,
        template_id: LabelTemplateId | None = None,
        lot_id: str | None = None,
    ) -> str:
        """Generate a formula report PDF.

        Renders a full report for a formula (composition, property task
        results, and related details) using a ``formulareport`` template and
        returns a short-lived URL for the finished PDF.

        !!! example
            ```python
            url = client.label_templates.get_formula_report_url(
                formula_id="INVA1234-001",
                template_id="TMP123",
            )
            # 'https://s3.us-west-2.amazonaws.com/...'
            ```

        Parameters
        ----------
        formula_id : InventoryId
            The formula Inventory ID (format ``INV...``).
        template_id : LabelTemplateId, optional
            The ``formulareport`` template to render with (format ``TMP...``).
            When not provided, the tenant default is used.
        lot_id : str, optional
            Restrict the report to a specific lot.

        Returns
        -------
        str
            A short-lived URL for downloading the generated report PDF.
        """
        params = {
            "formulaId": formula_id,
            "templateId": template_id,
            "lotId": lot_id,
        }
        response = self.session.get(f"{self.base_path}/formulareport", params=params)
        return response.json()["presignedURL"]
