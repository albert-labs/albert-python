from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.shared.models.base import BaseAlbertModel, BaseResource


class ReportTemplateCategory(str, Enum):
    """The category of a report template.

    Attributes
    ----------
    ANALYTICS : str
        Analytics reports.
    DATASCIENCE : str
        Data science reports.
    REPORTS : str
        General reports.
    """

    ANALYTICS = "analytics"
    DATASCIENCE = "datascience"
    REPORTS = "reports"


class ReportTemplateSubCategory(str, Enum):
    """The sub-category of a report template, describing its subject area.

    Attributes
    ----------
    PROJECT : str
        A single project.
    INVENTORY : str
        Inventory items.
    TASKS : str
        Tasks.
    PRODUCTS : str
        Products.
    PROJECTS : str
        Projects.
    INVENTORY_LOTS_AND_HAZARDS : str
        Inventory lots and their hazards.
    PRODUCTS_FORMULAS : str
        Products and formulas.
    RESULT_AND_TASK_DATA : str
        Result and task data.
    BATCH_TASKS_AND_INVENTORY_USAGE : str
        Batch tasks and inventory usage.
    """

    PROJECT = "Project"
    INVENTORY = "Inventory"
    TASKS = "Tasks"
    PRODUCTS = "Products"
    PROJECTS = "Projects"
    INVENTORY_LOTS_AND_HAZARDS = "Inventory Lots and Hazards"
    PRODUCTS_FORMULAS = "Products / Formulas"
    RESULT_AND_TASK_DATA = "Result and Task Data"
    BATCH_TASKS_AND_INVENTORY_USAGE = "Batch Tasks and Inventory Usage"


class FilterType(str, Enum):
    """The input type of a report template filter.

    Attributes
    ----------
    DROPDOWN : str
        A dropdown selection populated from a data source.
    ENUM : str
        A fixed set of enumerated values.
    BOOLEAN : str
        A true/false toggle.
    NUMBER : str
        A numeric value.
    """

    DROPDOWN = "dropDown"
    ENUM = "enum"
    BOOLEAN = "boolean"
    NUMBER = "number"


class FilterOption(BaseAlbertModel):
    """A filter option for a report template."""

    name: str = Field(..., description="Name of the filter")
    type: FilterType | None = Field(default=None, description="Type of the filter")
    label: str | None = Field(default=None, description="Display label for the filter")
    url: str | None = Field(default=None, description="URL for filter data")
    payload_id: str | None = Field(
        default=None, alias="payloadId", description="Payload ID for the filter"
    )
    method: str | None = Field(default=None, description="HTTP method for filter data")
    values: list[Any] | None = Field(default=None, description="Available values for the filter")
    default: bool | None = Field(default=None, description="Whether this filter is default")
    single_select: bool | None = Field(
        default=None, alias="singleSelect", description="Whether single selection is allowed"
    )
    default_value: list[str] | None = Field(
        default=None, alias="defaultValue", description="Default values for the filter"
    )


class FilterOptions(BaseAlbertModel):
    """Filter options configuration for a report template."""

    min_filters: int | None = Field(
        default=None, alias="minFilters", description="Minimum number of filters required"
    )
    filters: list[FilterOption] | None = Field(
        default=None, description="List of available filters"
    )


class FieldMapping(BaseAlbertModel):
    """Field mapping configuration for a report template."""

    url: str = Field(..., description="URL for the field mapping")
    field_name: str = Field(..., alias="fieldName", description="Name of the field")
    display_name: str = Field(..., alias="displayName", description="Display name for the field")


class ReportTemplate(BaseResource):
    """A reusable report configuration in Albert.

    A report template defines a report type that can be run: its available
    filters and its default column, chart, and metadata state. Templates are
    retrieved through
    [`ReportTemplateCollection`][albert.collections.report_templates.ReportTemplateCollection] and are
    grouped by [`ReportTemplateCategory`][albert.resources.report_templates.ReportTemplateCategory] and [`ReportTemplateSubCategory`][albert.resources.report_templates.ReportTemplateSubCategory].

    Attributes
    ----------
    id : str | None
        The Albert ID of the report template. Set when the template is retrieved
        from Albert.
    name : str
        The name of the report template (1 to 255 characters).
    description : str | None
        A description of the report template (maximum 1000 characters).
    filter_options : FilterOptions | None
        The filters available when running the template.
    filter_state : dict | None
        The template's default filter state.
    meta_data_state : dict | None
        The template's default metadata state.
    chart_model_state : list | None
        The template's default chart state.
    column_state : list | None
        The template's default column state.
    sp_name : str
        The stored-procedure name backing the report.
    category : ReportTemplateCategory
        The category of the report template.
    sub_category : ReportTemplateSubCategory | None
        The subject-area sub-category of the report template.
    custom_fields : list[str] | None
        The names of custom fields associated with the report template.
    field_mapping : list[FieldMapping] | None
        The mapping between report fields and their display names.
    """

    id: str | None = Field(default=None, alias="albertId")
    name: str = Field(..., min_length=1, max_length=255, description="Name of the report template")
    description: str | None = Field(
        default=None, max_length=1000, description="Description of the report template"
    )
    filter_options: FilterOptions | None = Field(
        default=None, alias="filterOptions", description="Filter options configuration"
    )
    filter_state: dict[str, Any] | None = Field(
        default=None, alias="filterState", description="Current state of filters"
    )
    meta_data_state: dict[str, Any] | None = Field(
        default=None, alias="metaDataState", description="Current state of metadata"
    )
    chart_model_state: list[Any] | None = Field(
        default=None, alias="chartModelState", description="Current state of chart models"
    )
    column_state: list[Any] | None = Field(
        default=None, alias="columnState", description="Current state of columns"
    )
    sp_name: str = Field(..., alias="spName", description="Stored procedure name")
    category: ReportTemplateCategory = Field(..., description="Category of the report template")
    sub_category: ReportTemplateSubCategory | None = Field(
        default=None, alias="subCategory", description="Sub-category of the report template"
    )
    custom_fields: list[str] | None = Field(
        default=None, alias="customFields", description="List of custom field names"
    )
    field_mapping: list[FieldMapping] | None = Field(
        default=None, alias="fieldMapping", description="Field mapping configuration"
    )
