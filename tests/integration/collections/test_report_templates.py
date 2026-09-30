import pytest

from albert.client import Albert
from albert.resources.report_templates import ReportTemplate


def test_report_template_get_all(client: Albert):
    templates = client.report_templates.get_all()
    if not templates:
        pytest.skip("No report templates in testing environment")
    for rt in templates:
        assert rt.id is not None
        assert isinstance(rt, ReportTemplate)


def test_report_template_get_by_id_accepts_fully_qualified_id(client: Albert):
    """Test get_by_id accepts a fully qualified ``ALB#...`` template ID."""
    templates = client.report_templates.get_all()
    if not templates:
        pytest.skip("No report templates in testing environment")
    template = templates[0]
    qualified = f"ALB#{template.id}"
    fetched = client.report_templates.get_by_id(id=qualified)
    assert fetched.id == template.id
    assert fetched.name == template.name
