from typing import Any

import pandas as pd
from pydantic import AliasChoices, Field

from albert.core.shared.identifiers import ProjectId, ReportId
from albert.core.shared.models.base import BaseAlbertModel, BaseResource

ReportItem = dict[str, Any] | list[dict[str, Any]] | None


class ReportInfo(BaseAlbertModel):
    report_type_id: str = Field(..., alias="reportTypeId")
    report_type: str = Field(..., alias="reportType")
    category: str
    items: list[ReportItem] = Field(..., alias="Items")


class ColumnState(BaseAlbertModel):
    """Column State Object for reports."""

    col_id: str = Field(..., alias="colId")
    row_group_index: int | None = Field(default=None, alias="rowGroupIndex")
    agg_func: str | None = Field(default=None, alias="aggFunc")
    pivot: bool = Field(default=False)
    pivot_index: int | None = Field(default=None, alias="pivotIndex")
    row_group: bool = Field(default=False, alias="rowGroup")


class FilterModel(BaseAlbertModel):
    """Filter Model Object for reports."""

    filter_type: str = Field(..., alias="filterType")
    values: list[Any] | None = Field(default=None)


class FilterState(BaseAlbertModel):
    """Filters State Object for reports."""

    filter_models: list[FilterModel] = Field(default_factory=list, alias="filterModels")


class MetadataState(BaseAlbertModel):
    """Metadata State Object for reports."""

    grouped_rows: list[str] = Field(default_factory=list, alias="groupedRows")


class ChartConfiguration(BaseAlbertModel):
    """Chart Configuration Object for reports."""

    chart_type: str | None = Field(default=None, alias="chartType")
    # Add other chart configuration fields as needed


class ChartTemplate(BaseAlbertModel):
    """Chart Template Object for reports."""

    chart_type: str = Field(..., alias="chartType")
    # Add other chart template fields as needed


class ChartModelState(BaseAlbertModel):
    """Chart State Object for reports."""

    chart_template: ChartTemplate | None = Field(default=None, alias="chartTemplate")
    chart_configuration: ChartConfiguration | None = Field(
        default=None, alias="chartConfiguration"
    )


class ColumnMapping(BaseAlbertModel):
    """Column Mapping Object for reports."""

    # Add column mapping fields as needed
    pass


class FullAnalyticalReport(BaseResource):
    """A full analytical report in Albert.

    This resource represents a complete analytical report with all its configuration,
    data, and state information.

    Attributes
    ----------
    report_data_id : str | None
        Unique Identifier of the Report which is created. Read-only.
    report_type_id : str
        Type of report which will be created. Taken from reports/type API.
    report_type : str | None
        Type of report which will be created. Name taken from reports/type API.
    name : str
        Name of the report. Maximum length 500 characters.
    description : str | None
        Description of the report. Maximum length 1000 characters.
    project_id : str | None
        Project ID of the report. Not mandatory.
    project_name : str | None
        Name of the project.
    parent_id : str | None
        Parent ID of the report. Not mandatory.
    report_v2 : bool | None
        Whether this is a v2 report.
    input_data : dict[str, Any] | None
        Input data for the report.
    report_state : str | None
        Any string representing the report state.
    column_state : List[ColumnState] | None
        Column state objects.
    filter_state : FilterState | None
        Filters state object.
    meta_data_state : MetadataState | None
        Metadata state object.
    chart_model_state : List[ChartModelState] | None
        Chart state objects.
    field_mapping : List[ColumnMapping] | None
        Column mapping objects.
    source_report_id : str | None
        Report ID from which to copy states to the new report.
    created_by : str | None
        Specifies the createdBy id.
    """

    # Read-only fields
    id: ReportId | None = Field(
        default=None,
        alias=AliasChoices("id", "albertId"),
        serialization_alias="id",
        exclude=True,
        frozen=True,
    )

    # Required fields
    report_type_id: str = Field(..., alias="reportTypeId")
    name: str = Field(..., min_length=1, max_length=500)

    # Optional fields
    report_type: str | None = Field(default=None, alias="reportType")
    description: str | None = Field(default=None, max_length=1000)
    project_id: ProjectId | None = Field(default=None, alias="projectId")
    project_name: str | None = Field(default=None, alias="projectName")
    parent_id: str | None = Field(default=None, alias="parentId")
    report_v2: bool | None = Field(default=None, alias="reportV2")
    input_data: dict[str, Any] | None = Field(default=None, alias="inputData")
    report_state: str | None = Field(default=None, alias="reportState")
    column_state: list[ColumnState] | None = Field(default_factory=list, alias="columnState")
    filter_state: FilterState | None = Field(default=None, alias="filterState")
    meta_data_state: MetadataState | None = Field(default=None, alias="metaDataState")
    chart_model_state: list[ChartModelState] | None = Field(
        default_factory=list, alias="chartModelState"
    )
    field_mapping: list[ColumnMapping] | None = Field(default_factory=list, alias="FieldMapping")
    source_report_id: ReportId | None = Field(default=None, alias="sourceReportId")
    created_by: str | None = Field(default=None, alias="createdBy")

    report: list[dict[str, Any]] | None = Field(default=None, frozen=True)

    def get_raw_dataframe(self) -> pd.DataFrame:
        """
        Get the raw report data as a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            The raw report data.
        """
        if not self.report:
            raise ValueError("Report data is not available")
        return pd.DataFrame(self.report)
