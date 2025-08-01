import pytest

from albert.client import Albert
from albert.resources.report_templates import ReportTemplate


@pytest.mark.skip(reason="Report Templates not loaded into testing environment yet")
def test_report_template_get_all(client: Albert):
    for rt in client.report_templates.get_all():
        assert rt.id is not None
        assert isinstance(rt, ReportTemplate)
