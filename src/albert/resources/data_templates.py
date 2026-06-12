from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass
from albert.core.shared.identifiers import AttachmentId, DataColumnId, DataTemplateId
from albert.core.shared.models.base import (
    AuditFields,
    BaseResource,
    EntityLink,
    EntityLinkWithName,
    LocalizedNames,
)
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.data_columns import DataColumn
from albert.resources.parameter_groups import DataType, ParameterValue, ValueValidation
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.tags import Tag
from albert.resources.units import Unit
from albert.resources.users import User


class CSVMapping(BaseAlbertModel):
    """A mapping between CSV column headers and data column IDs.

    Attributes
    ----------
    map_id : str | None
        A compact mapping string (e.g. ``"Header1:DAC2900#Header2:DAC4707"``).
    map_data : dict[str, str] | None
        A dictionary mapping CSV header names to data column IDs.
    """

    map_id: str | None = Field(
        alias="mapId", default=None, examples="Header1:DAC2900#Header2:DAC4707"
    )
    map_data: dict[str, str] | None = Field(
        alias="mapData", default=None, examples={"Header1": "DAC2900", "Header2": "DAC4707"}
    )


class Axis(str, Enum):
    X = "X"
    Y = "Y"


class CurveDBMetadata(BaseAlbertModel):
    """Database metadata for a curve data column result.

    Attributes
    ----------
    table_name : str | None
        The Athena/database table name storing the curve data.
    partition_key : str | None
        The partition key for the curve data table.
    """

    table_name: str | None = Field(default=None, alias="tableName")
    partition_key: str | None = Field(default=None, alias="partitionKey")


class StorageKeyReference(BaseAlbertModel):
    """S3 storage key references for a data column file result.

    Attributes
    ----------
    rawfile : str | None
        The raw file storage key.
    s3_input : str | None
        The S3 key for the input file.
    s3_output : str | None
        The S3 key for the processed output file.
    preview : str | None
        The S3 key for a preview image.
    thumb : str | None
        The S3 key for a thumbnail image.
    original : str | None
        The S3 key for the original file.
    """

    rawfile: str | None = None
    s3_input: str | None = Field(default=None, alias="s3Input")
    s3_output: str | None = Field(default=None, alias="s3Output")
    preview: str | None = None
    thumb: str | None = None
    original: str | None = None


class JobSummary(BaseAlbertModel):
    """A brief summary of a background processing job.

    Attributes
    ----------
    id : str | None
        The job identifier.
    state : str | None
        The current state of the job.
    """

    id: str | None = None
    state: str | None = None


class CurveDataEntityLink(EntityLinkWithName):
    """A link to a data column that provides one axis of a curve dataset.

    Attributes
    ----------
    id : DataColumnId
        The data column ID.
    axis : Axis | None
        Which axis this column represents (X or Y).
    unit : Unit | None
        The unit of measure for this axis.
    """

    id: DataColumnId
    axis: Axis | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")


class DataColumnValue(BaseResource):
    """A single data column entry within a data template, holding its configuration and value.

    Attributes
    ----------
    data_column : DataColumn | None
        The full DataColumn object. Provide either this or ``data_column_id``.
    data_column_id : DataColumnId | None
        The Albert ID of the data column. Provide either this or ``data_column``.
    name : str | None
        The display name of the column in this template context.
    original_name : str | None
        The original name of the column before any rename. Read-only.
    value : str | None
        The default or stored value for this column.
    hidden : bool
        Whether the column is hidden. Defaults to ``False``.
    unit : Unit | None
        The unit of measure for this column's values.
    calculation : str | None
        A formula or calculation expression for computed columns.
    sequence : str | None
        The display order of this column within the template.
    script : bool | None
        Whether this column uses a script for data import.
    db_metadata : CurveDBMetadata | None
        Database/Athena metadata for curve-type columns.
    storage_key_reference : StorageKeyReference | None
        S3 storage key references for file-backed column results.
    job : JobSummary | None
        Summary of the last background processing job for this column.
    csv_mapping : dict[str, str] | CSVMapping | None
        CSV header-to-column mapping for CSV import columns.
    validation : list[ValueValidation] | None
        Validation rules applied to values in this column.
    curve_data : list[CurveDataEntityLink] | None
        Axis column links for curve-type data columns.
    created : AuditFields | None
        Audit fields recording when this column value was created.
    """

    data_column: DataColumn | None = Field(exclude=True, default=None)
    data_column_id: DataColumnId | None = Field(alias="id", default=None)
    name: str | None = None
    original_name: str | None = Field(
        default=None, alias="originalName", exclude=True, frozen=True
    )
    value: str | None = None
    hidden: bool = False
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    calculation: str | None = None
    sequence: str | None = Field(default=None)
    script: bool | None = None
    db_metadata: CurveDBMetadata | None = Field(default=None, alias="athena")
    storage_key_reference: StorageKeyReference | None = Field(default=None, alias="s3Key")
    job: JobSummary | None = None
    csv_mapping: dict[str, str] | CSVMapping | None = Field(default=None, alias="csvMapping")
    validation: list[ValueValidation] | None = Field(default_factory=list)
    curve_data: list[CurveDataEntityLink] | None = Field(
        default=None,
        validation_alias=AliasChoices("CurveData", "curveData"),
        serialization_alias="curveData",
    )
    created: AuditFields | None = Field(
        default=None,
        alias="Created",
        validation_alias=AliasChoices("Created", "Added"),
        serialization_alias="Added",
    )

    @model_validator(mode="after")
    def check_for_id(self):
        if self.data_column_id is None and self.data_column is None:
            raise ValueError("Either data_column_id or data_column must be set")
        elif (
            self.data_column_id is not None
            and self.data_column is not None
            and self.data_column.id != self.data_column_id
        ):
            raise ValueError("If both are provided, data_column_id and data_column.id must match")
        elif self.data_column_id is None:
            self.data_column_id = self.data_column.id
        return self


class DataTemplate(BaseTaggedResource):
    """A data template defining data columns and parameters for measurement tasks.

    Attributes
    ----------
    name : str
        The name of the data template.
    id : DataTemplateId | None
        The Albert ID of the data template.
    description : str | None
        A description of the data template.
    security_class : SecurityClass | None
        The security classification of the data template.
    verified : bool
        Whether the data template has been verified. Defaults to ``False``.
    users_with_access : list[User] | None
        Users who have explicit access to this data template.
    data_column_values : list[DataColumnValue] | None
        The data column definitions included in this template.
    parameter_values : list[ParameterValue] | None
        The parameter definitions included in this template.
    deleted_parameters : list[ParameterValue] | None
        Parameters that have been removed from this template. Read-only.
    metadata : dict[str, MetadataItem] | None
        Custom metadata attached to the data template.
    documents : list[EntityLink]
        Documents linked to this data template. Read-only.
    original_name : str | None
        The original name before any rename. Read-only.
    full_name : str | None
        The fully qualified name including any parent context. Read-only.
    """

    name: str
    id: DataTemplateId | None = Field(None, alias="albertId")
    description: str | None = None
    security_class: SecurityClass | None = Field(default=None, alias="class")
    verified: bool = False
    users_with_access: list[SerializeAsEntityLink[User]] | None = Field(alias="ACL", default=None)
    data_column_values: list[DataColumnValue] | None = Field(alias="DataColumns", default=None)
    parameter_values: list[ParameterValue] | None = Field(alias="Parameters", default=None)
    deleted_parameters: list[ParameterValue] | None = Field(
        alias="DeletedParameters", default=None, frozen=True, exclude=True
    )
    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="Metadata")
    documents: list[EntityLink] = Field(
        default_factory=list, alias="Documents", exclude=True, frozen=True
    )

    # Read-only convenience fields from API
    original_name: str | None = Field(
        default=None, alias="originalName", exclude=True, frozen=True
    )
    full_name: str | None = Field(default=None, alias="fullName", exclude=True, frozen=True)


class ImportMode(str, Enum):
    SCRIPT = "SCRIPT"
    CSV = "CSV"


class CurveExample(BaseAlbertModel):
    """
    Curve example data for a data template column.

    Attributes
    ----------
    mode : ImportMode
        ``ImportMode.CSV`` ingests the CSV directly; ``ImportMode.SCRIPT`` runs the attached
        script first (requires a script attachment on the column).
    field_mapping : dict[str, str] | None
        Optional header-to-curve-result mapping, e.g. ``{"visc": "Viscosity"}``. Overrides
        auto-detected mappings.
    file_path : str | Path | None
        Local path to source CSV file.
    attachment_id : AttachmentId | None
        Existing attachment ID of source CSV file.
        Provide exactly one source CSV (local path or existing attachment).
    """

    type: Literal[DataType.CURVE] = DataType.CURVE
    mode: ImportMode = ImportMode.CSV
    field_mapping: dict[str, str] | None = None
    file_path: str | Path | None = None
    attachment_id: AttachmentId | None = None

    @model_validator(mode="after")
    def _require_curve_source(self) -> CurveExample:
        if (self.file_path is None) == (self.attachment_id is None):
            raise ValueError(
                "Provide exactly one of file_path or attachment_id for curve examples."
            )
        return self


class ImageExample(BaseAlbertModel):
    """Example data for an image data column."""

    type: Literal[DataType.IMAGE] = DataType.IMAGE
    file_path: str | Path


class DataTemplateSearchItemDataColumn(BaseAlbertModel):
    """A lightweight data column reference within a data template search result.

    Attributes
    ----------
    id : str
        The Albert ID of the data column.
    name : str | None
        The name of the data column.
    localized_names : LocalizedNames
        Localized name variants for the data column.
    """

    id: str
    name: str | None = None
    localized_names: LocalizedNames = Field(alias="localizedNames")


class DataTemplateSearchItem(BaseAlbertModel, HydrationMixin[DataTemplate]):
    """Lightweight representation of a DataTemplate returned from search.

    Attributes
    ----------
    id : str
        The Albert ID of the data template.
    name : str
        The name of the data template.
    data_columns : list[DataTemplateSearchItemDataColumn] | None
        The data column summaries included in the template.
    owner : list[User] | None
        The owners of the data template.
    tags : list[User] | None
        Tags associated with the data template.
    acl : list[User] | None
        Users with explicit access to the data template.
    created_at : str | None
        ISO 8601 timestamp of when the template was created.
    created_by_name : str | None
        The name of the user who created the template.
    metadata : dict[str, Any] | None
        Custom metadata attached to the template.
    team : list[User] | None
        Team members associated with the template.
    standards : list[dict[str, Any]] | None
        Standards linked to the template.
    """

    id: str = Field(alias="albertId")
    name: str
    data_columns: list[DataTemplateSearchItemDataColumn] | None = Field(
        alias="dataColumns", default=None
    )
    owner: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="owner")
    tags: list[SerializeAsEntityLink[Tag]] | None = Field(default=None, alias="tags")
    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="acl")
    created_at: str | None = Field(default=None, alias="createdAt")
    created_by_name: str | None = Field(default=None, alias="createdByName")
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata")
    team: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="team")
    standards: list[dict[str, Any]] | None = Field(default=None, alias="standards")
