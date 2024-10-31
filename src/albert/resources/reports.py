from typing import Any

from pydantic import Field

from albert.resources.base import BaseResource

ReportItem = dict[str, Any] | list[dict[str, Any]] | None


class ReportInfo(BaseResource):
    report_type_id: str = Field(..., alias="reportTypeId")
    report_type: str = Field(..., alias="reportType")
    category: str
    items: list[ReportItem] = Field(..., alias="Items")
