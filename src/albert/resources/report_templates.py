from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.shared.models.base import BaseAlbertModel, BaseResource


class ReportTemplateCategory(str, Enum):
    """The category of a report template."""

    ANALYTICS = "analytics"
    DATASCIENCE = "datascience"
    REPORTS = "reports"


class ReportTemplateSubCategory(str, Enum):
    """The sub-category of a report template."""

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
    """The type of filter for report templates."""

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
    """A report template in Albert.

    Attributes
    ----------
    id : str | None
        The Albert ID of the report template. Set when the report template is retrieved from Albert.
    name : str
        The name of the report template. Must be between 1 and 255 characters.
    description : str | None
        Description of the report template. Maximum length 1000 characters.
    filter_options : FilterOptions | None
        Filter options configuration for the report template.
    filter_state : dict | None
        Current state of filters for the report template.
    meta_data_state : dict | None
        Current state of metadata for the report template.
    chart_model_state : list | None
        Current state of chart models for the report template.
    column_state : list | None
        Current state of columns for the report template.
    sp_name : str
        Stored procedure name for the report template.
    category : ReportTemplateCategory
        Category of the report template.
    sub_category : ReportTemplateSubCategory | None
        Sub-category of the report template.
    custom_fields : list[str] | None
        List of custom field names associated with the report template.
    field_mapping : list[FieldMapping] | None
        Field mapping configuration for the report template.
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
