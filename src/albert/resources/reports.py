from typing import Any

import pandas as pd
from pydantic import AliasChoices, Field

from albert.core.shared.identifiers import ProjectId, ReportId
from albert.core.shared.models.base import BaseAlbertModel, BaseResource

ReportItem = dict[str, Any] | list[dict[str, Any]] | None


class ReportInfo(BaseAlbertModel):
    """The result of running a report on demand.

    Returned by the ``get_report`` family of methods on
    [`ReportCollection`][albert.collections.reports.ReportCollection].

    Attributes
    ----------
    report_type_id : str
        The report type ID that was run (e.g. ``"RET51"``).
    report_type : str
        The human-readable name of the report type.
    category : str
        The report category (e.g. ``"analytics"`` or ``"datascience"``).
    items : list[ReportItem]
        The computed report result rows. Each item is a dict (or list of dicts)
        whose shape depends on the report type.
    """

    report_type_id: str = Field(..., alias="reportTypeId")
    report_type: str = Field(..., alias="reportType")
    category: str
    items: list[ReportItem] = Field(..., alias="Items")


class ColumnState(BaseAlbertModel):
    """The display and grouping state of a single report column.

    Attributes
    ----------
    col_id : str
        The identifier of the column.
    row_group_index : int | None
        The column's position among the row-grouping columns, if grouped.
    agg_func : str | None
        The aggregation function applied to the column (e.g. ``"sum"``).
    pivot : bool
        Whether the column is used as a pivot column.
    pivot_index : int | None
        The column's position among the pivot columns, if pivoted.
    row_group : bool
        Whether the column is used to group rows.
    """

    col_id: str = Field(..., alias="colId")
    row_group_index: int | None = Field(default=None, alias="rowGroupIndex")
    agg_func: str | None = Field(default=None, alias="aggFunc")
    pivot: bool = Field(default=False)
    pivot_index: int | None = Field(default=None, alias="pivotIndex")
    row_group: bool = Field(default=False, alias="rowGroup")


class FilterModel(BaseAlbertModel):
    """A single filter applied to a report.

    Attributes
    ----------
    filter_type : str
        The kind of filter (e.g. ``"set"`` or ``"text"``).
    values : list[Any] | None
        The values the filter matches against.
    """

    filter_type: str = Field(..., alias="filterType")
    values: list[Any] | None = Field(default=None)


class FilterState(BaseAlbertModel):
    """The collection of filters applied to a report.

    Attributes
    ----------
    filter_models : list[FilterModel]
        The individual filters that make up the report's filter state.
    """

    filter_models: list[FilterModel] = Field(default_factory=list, alias="filterModels")


class MetadataState(BaseAlbertModel):
    """The metadata state of a report.

    Attributes
    ----------
    grouped_rows : list[str]
        The identifiers of rows that are grouped in the report.
    """

    grouped_rows: list[str] = Field(default_factory=list, alias="groupedRows")


class ChartConfiguration(BaseAlbertModel):
    """The configuration of a chart on a report.

    Attributes
    ----------
    chart_type : str | None
        The type of chart (e.g. ``"bar"`` or ``"line"``).
    """

    chart_type: str | None = Field(default=None, alias="chartType")
    # Add other chart configuration fields as needed


class ChartTemplate(BaseAlbertModel):
    """The template describing a chart's base type on a report.

    Attributes
    ----------
    chart_type : str
        The type of chart (e.g. ``"bar"`` or ``"line"``).
    """

    chart_type: str = Field(..., alias="chartType")
    # Add other chart template fields as needed


class ChartModelState(BaseAlbertModel):
    """The saved state of a single chart on a report.

    Attributes
    ----------
    chart_template : ChartTemplate | None
        The chart's base template.
    chart_configuration : ChartConfiguration | None
        The chart's configuration.
    """

    chart_template: ChartTemplate | None = Field(default=None, alias="chartTemplate")
    chart_configuration: ChartConfiguration | None = Field(
        default=None, alias="chartConfiguration"
    )


class ColumnMapping(BaseAlbertModel):
    """A mapping of report fields to columns.

    This model currently defines no fields.
    """

    pass


class FullAnalyticalReport(BaseResource):
    """A saved analytical report in Albert.

    This resource represents a complete analytical report: its report type, the
    data it was run over, and its saved display state (columns, filters, grouping,
    and charts). Retrieve one with
    [`get_full_report`][albert.collections.reports.ReportCollection.get_full_report] or create
    one with [`create_report`][albert.collections.reports.ReportCollection.create_report].

    !!! example
        ```python
        from albert.resources.reports import FullAnalyticalReport

        report = FullAnalyticalReport(
            report_type_id="ALB#RET22",
            name="My New Report",
            description="A test report",
        )
        ```

    Attributes
    ----------
    id : ReportId | None
        The Albert ID of the report (format ``REP...``). Set by Albert; read-only.
    report_type_id : str
        The report type ID identifying which report to run. Required.
    name : str
        The report's name (1 to 500 characters). Required.
    report_type : str | None
        The human-readable name of the report type.
    description : str | None
        A description of the report (maximum 1000 characters).
    project_id : str | None
        The Project the report is scoped to, if any (format ``PRO...``).
    project_name : str | None
        The name of the scoped project.
    parent_id : str | None
        The parent entity the report belongs to, if any.
    report_v2 : bool | None
        Whether this is a v2 report.
    input_data : dict[str, Any] | None
        Input describing what the report is run over, keyed by field name.
    report_state : str | None
        A string capturing the overall report state.
    column_state : list[ColumnState] | None
        The saved display and grouping state of each column.
    filter_state : FilterState | None
        The saved filters applied to the report.
    meta_data_state : MetadataState | None
        The saved metadata state (e.g. grouped rows).
    chart_model_state : list[ChartModelState] | None
        The saved state of each chart on the report.
    field_mapping : list[ColumnMapping] | None
        The mapping of report fields to columns.
    source_report_id : ReportId | None
        A report to copy state from when creating this report (format ``REP...``).
    created_by : str | None
        The ID of the user who created the report. Read-only.
    report : list[dict[str, Any]] | None
        The raw report result rows. Populated when the report is retrieved;
        read-only. Use [`get_raw_dataframe`][albert.resources.reports.FullAnalyticalReport.get_raw_dataframe] to read it as a DataFrame.
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
        """Return the raw report data as a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            The raw report result rows.

        Raises
        ------
        ValueError
            If the report has no result data (e.g. it was built locally rather
            than retrieved from Albert).
        """
        if not self.report:
            raise ValueError("Report data is not available")
        return pd.DataFrame(self.report)
