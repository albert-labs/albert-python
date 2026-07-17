from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.pdf_generator import PDFOptions, PDFS3Storage, PDFTemplate


class PDFGeneratorCollection(BaseCollection):
    """Manage PDF, barcode, and QR code generation in the Albert platform.

    Renders Mustache HTML templates with data into stored PDFs, and generates
    barcode and QR code images from text. This is the rendering engine behind
    printable label templates; see
    [`LabelTemplateCollection`][albert.collections.label_templates.LabelTemplateCollection]
    for the higher-level label workflow.

    This collection is accessed as ``client.pdf_generator``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        barcode = client.pdf_generator.generate_barcode(text="B1234-001")
        barcode[:22]
        # 'data:image/png;base64,'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for PDF generator requests.

    Methods
    -------
    generate_pdf(template, data, s3_storage, options=None, albert_id=None) -> str
        Render a PDF from an HTML template and data, returning a download URL.
    generate_barcode(text, text_size=None, as_signed_url=False) -> str
        Generate a barcode image from text.
    generate_qr_code(text) -> str
        Generate a QR code image from text.
    """

    _api_version = "v2"

    def __init__(self, *, session: AlbertSession):
        """Initialize a PDFGeneratorCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{PDFGeneratorCollection._api_version}/pdfgenerator"

    @validate_call
    def generate_pdf(
        self,
        *,
        template: PDFTemplate,
        data: dict[str, Any],
        s3_storage: PDFS3Storage,
        options: PDFOptions | dict[str, Any] | None = None,
        albert_id: str | None = None,
    ) -> str:
        """Render a PDF from an HTML template and data.

        The template HTML is rendered with ``data`` using Mustache
        placeholders, printed to PDF, and stored at the ``s3_storage``
        destination. A short-lived download URL for the PDF is returned.

        The inputs typically come from a
        [`LabelPrintPayload`][albert.resources.label_templates.LabelPrintPayload]
        produced by
        [`get_print_payload`][albert.collections.label_templates.LabelTemplateCollection.get_print_payload].

        !!! example
            ```python
            payload = client.label_templates.get_print_payload(
                inventory_lot_number_id="LOTB1234",
            )
            url = client.pdf_generator.generate_pdf(
                template=payload.template,
                data=payload.data,
                s3_storage=payload.s3_storage,
                options=payload.options,
            )
            ```

        Parameters
        ----------
        template : PDFTemplate
            The HTML template sources to render. ``template.body`` is required.
        data : dict[str, Any]
            The values substituted into the template's Mustache placeholders.
        s3_storage : PDFS3Storage
            Where the generated PDF is stored.
        options : PDFOptions or dict[str, Any], optional
            Page rendering options. See [`PDFOptions`][albert.resources.pdf_generator.PDFOptions]
            for the recognized settings; unrecognized keys are ignored.
        albert_id : str, optional
            An optional identifier to associate with the generated PDF.

        Returns
        -------
        str
            A short-lived URL for downloading the generated PDF.
        """
        payload: dict[str, Any] = {
            "template": template.model_dump(by_alias=True, mode="json", exclude_none=True),
            "data": data,
            "s3Storage": s3_storage.model_dump(by_alias=True, mode="json", exclude_none=True),
        }
        if isinstance(options, PDFOptions):
            options = options.model_dump(by_alias=True, mode="json", exclude_none=True)
        if options is not None:
            payload["options"] = options
        if albert_id is not None:
            payload["albertId"] = albert_id

        response = self.session.post(f"{self.base_path}/generate", json=payload)
        return response.json()["presignedURL"]

    @validate_call
    def generate_barcode(
        self,
        *,
        text: str,
        text_size: int | None = None,
        as_signed_url: bool = False,
    ) -> str:
        """Generate a barcode image from text.

        !!! example
            ```python
            barcode = client.pdf_generator.generate_barcode(text="B1234-001")
            barcode[:22]
            # 'data:image/png;base64,'
            ```

        Parameters
        ----------
        text : str
            The text to encode in the barcode.
        text_size : int, optional
            The size of the human-readable text rendered below the barcode.
        as_signed_url : bool, optional
            When True, return a short-lived URL for the stored barcode image
            instead of an inline ``data:`` URI. Defaults to False.

        Returns
        -------
        str
            The barcode image as a base64 ``data:`` URI, or a short-lived URL
            when ``as_signed_url`` is True.
        """
        params: dict[str, Any] = {"text": text, "textsize": text_size}
        if as_signed_url:
            params["s3url"] = "true"
        response = self.session.get(f"{self.base_path}/barcode", params=params)
        return response.json()["barCode"]

    @validate_call
    def generate_qr_code(self, *, text: str) -> str:
        """Generate a QR code image from text.

        !!! example
            ```python
            qr = client.pdf_generator.generate_qr_code(text="LOTB1234")
            qr[:22]
            # 'data:image/png;base64,'
            ```

        Parameters
        ----------
        text : str
            The text to encode in the QR code.

        Returns
        -------
        str
            The QR code image as a base64 ``data:`` URI.
        """
        response = self.session.get(f"{self.base_path}/qrcode", params={"text": text})
        return response.json()["qrCode"]
