import pytest

from albert.client import Albert
from albert.resources.report_templates import ReportTemplate


@pytest.mark.skip(reason="Report Templates not loaded into testing environment yet")
def test_report_template_get_all(client: Albert):
    for rt in client.report_templates.get_all():
        assert rt.id is not None
        assert isinstance(rt, ReportTemplate)


def test_report_template_get_by_id_accepts_fully_qualified_id(client: Albert):
    """Test get_by_id round-trips a fully qualified ``ALB#...`` template ID."""
    templates = client.report_templates.get_all()
    qualified = next((rt.id for rt in templates if rt.id and "#" in rt.id), None)
    if qualified is None:
        pytest.skip("No fully qualified report templates in testing environment")
    fetched = client.report_templates.get_by_id(id=qualified)
    assert fetched.id == qualified
