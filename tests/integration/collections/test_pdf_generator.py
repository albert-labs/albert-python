from albert.client import Albert


def test_generate_barcode(client: Albert):
    """Test generate_barcode returns an inline barcode image."""
    barcode = client.pdf_generator.generate_barcode(text="B1234-001")
    assert barcode.startswith("data:image/png;base64,")


def test_generate_barcode_as_signed_url(client: Albert):
    """Test generate_barcode returns a URL when as_signed_url is True."""
    barcode = client.pdf_generator.generate_barcode(text="B1234-001", as_signed_url=True)
    assert barcode.startswith("http")


def test_generate_qr_code(client: Albert):
    """Test generate_qr_code returns an inline QR code image."""
    qr_code = client.pdf_generator.generate_qr_code(text="LOTB1234")
    assert qr_code.startswith("data:image/png;base64,")
