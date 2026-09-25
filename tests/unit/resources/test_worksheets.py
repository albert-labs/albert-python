
from albert.resources.sheets import Sheet
from albert.resources.worksheets import Worksheet


def _make_sheet() -> Sheet:
    return Sheet(
        id="WKS1S1",
        name="Sheet 1",
        hidden=False,
        designs=[{"id": "DES1", "design_type": "products"}],
        project_id="PRO1",
    )


def test_add_session_to_sheets_noop_without_session():
    """Test that sheets and designs keep no session when the worksheet has none."""
    sheet = _make_sheet()
    worksheet = Worksheet(sheets=[sheet], project_id="PRO1")
    assert worksheet.session is None
    assert sheet.session is None
    assert sheet.designs[0].session is None


def test_add_session_to_sheets_propagates_session(offline_session):
    """Test that a worksheet's session is propagated to its sheets and their designs."""
    sheet = _make_sheet()
    worksheet = Worksheet(sheets=[sheet], project_id="PRO1", session=offline_session)
    assert worksheet.session is offline_session
    # Same objects are mutated in place, not copied.
    assert worksheet.sheets[0] is sheet
    assert sheet.session is offline_session
    assert sheet.designs[0].session is offline_session
