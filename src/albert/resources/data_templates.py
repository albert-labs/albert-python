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
    """A mapping between CSV column headers and data column IDs."""

    map_id: str | None = Field(
        alias="mapId", default=None, examples="Header1:DAC2900#Header2:DAC4707"
    )
    """A compact mapping string (e.g. ``"Header1:DAC2900#Header2:DAC4707"``)."""

    map_data: dict[str, str] | None = Field(
        alias="mapData", default=None, examples={"Header1": "DAC2900", "Header2": "DAC4707"}
    )
    """A dictionary mapping CSV header names to data column IDs."""


class Axis(str, Enum):
    X = "X"
    Y = "Y"


class CurveDBMetadata(BaseAlbertModel):
    """Database metadata for a curve data column result."""

    table_name: str | None = Field(default=None, alias="tableName")
    """The Athena/database table name storing the curve data."""

    partition_key: str | None = Field(default=None, alias="partitionKey")
    """The partition key for the curve data table."""


class StorageKeyReference(BaseAlbertModel):
    """S3 storage key references for a data column file result."""

    rawfile: str | None = None
    """The raw file storage key."""

    s3_input: str | None = Field(default=None, alias="s3Input")
    """The S3 key for the input file."""

    s3_output: str | None = Field(default=None, alias="s3Output")
    """The S3 key for the processed output file."""

    preview: str | None = None
    """The S3 key for a preview image."""

    thumb: str | None = None
    """The S3 key for a thumbnail image."""

    original: str | None = None
    """The S3 key for the original file."""


class JobSummary(BaseAlbertModel):
    """A brief summary of a background processing job."""

    id: str | None = None
    """The job identifier."""

    state: str | None = None
    """The current state of the job."""


class CurveDataEntityLink(EntityLinkWithName):
    """A link to a data column that provides one axis of a curve dataset."""

    id: DataColumnId
    """The data column ID."""

    axis: Axis | None = Field(default=None)
    """Which axis this column represents (X or Y)."""

    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    """The unit of measure for this axis."""


class DataColumnValue(BaseResource):
    """A result data column on a Data Template.

    A ``DataColumnValue`` binds a [`DataColumn`][albert.resources.data_columns.DataColumn] to
    a Data Template as one of the results the test captures (a "direct variable"). Data
    columns can be typed numeric, text, dropdown/enum, image, curve, date, or timestamp.
    On a Data Template the ``value`` typically holds an example value shown on the
    details page rather than measured data; actual measurements are stored as Property
    Data. When constructing one, provide either ``data_column`` or ``data_column_id``.

    !!! example
        ```python
        from albert.resources.data_templates import DataColumnValue

        column = DataColumnValue(data_column_id="DAC1", value="42")
        ```"""

    data_column: DataColumn | None = Field(exclude=True, default=None)
    """The full DataColumn resource this value binds to. Provide this or ``data_column_id``. Not serialized."""

    data_column_id: DataColumnId | None = Field(alias="id", default=None)
    """The ID of the bound DataColumn (format ``DAC...``). Serialized as ``id``. Provide this or ``data_column``."""

    name: str | None = None
    """The display name of the column."""

    original_name: str | None = Field(
        default=None, alias="originalName", exclude=True, frozen=True
    )
    """The original column name as stored in Albert. Read-only."""

    value: str | None = None
    """The column's example/default value shown on the Data Template details page."""

    hidden: bool = False
    """Whether the column is hidden. Defaults to False."""

    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    """The unit of measure for the column."""

    calculation: str | None = None
    """A calculation expression for a computed column."""

    sequence: str | None = Field(default=None)
    """The column's position within the template. Assigned by Albert."""

    script: bool | None = None
    db_metadata: CurveDBMetadata | None = Field(default=None, alias="athena")
    storage_key_reference: StorageKeyReference | None = Field(default=None, alias="s3Key")
    job: JobSummary | None = None
    csv_mapping: dict[str, str] | CSVMapping | None = Field(default=None, alias="csvMapping")
    validation: list[ValueValidation] | None = Field(default_factory=list)
    """Validation rules applied to the column value (e.g. enum options, numeric range)."""

    curve_data: list[CurveDataEntityLink] | None = Field(
        default=None,
        validation_alias=AliasChoices("CurveData", "curveData"),
        serialization_alias="curveData",
    )
    """For curve columns, the linked X/Y curve result columns."""

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
    """A definition of what a test captures (a DAT).

    A ``DataTemplate`` (Data Template, ID format ``DAT...``) describes a test in two
    parts: its ``data_column_values`` are the measured RESULTS (the data columns, or
    "direct variables"), and its ``parameter_values`` are the CONDITIONS under which
    the test is run (the "indirect variables"). A Data Template does not itself store
    measured values; those are recorded as Property Data. When the template is paired
    with a Workflow inside a Block, only its parameters (not its result columns) flow
    into the Workflow's setpoints.

    Templates are managed through
    [`DataTemplateCollection`][albert.collections.data_templates.DataTemplateCollection]
    (``client.data_templates``).

    !!! example
        ```python
        from albert.resources.data_templates import DataTemplate, DataColumnValue

        template = DataTemplate(
            name="Tensile Strength Test",
            data_column_values=[DataColumnValue(data_column_id="DAC1")],
        )
        ```"""

    name: str
    """The name of the data template. Required."""

    id: DataTemplateId | None = Field(None, alias="albertId")
    """The Albert Data Template ID (format ``DAT...``). Set when the template is retrieved from or created in Albert. Serialized as ``albertId``."""

    description: str | None = None
    """A free-text description of the template."""

    security_class: SecurityClass | None = Field(default=None, alias="class")
    """The access/security class of the template. Serialized as ``class``."""

    verified: bool = False
    """The approval/governance state of the template. Defaults to False."""

    users_with_access: list[SerializeAsEntityLink[User]] | None = Field(alias="ACL", default=None)
    """The access-control list of users who can access the template. Serialized as ``ACL``."""

    data_column_values: list[DataColumnValue] | None = Field(alias="DataColumns", default=None)
    """The measured results the test captures (its data columns / direct variables). See [`DataColumnValue`][albert.resources.data_templates.DataColumnValue]."""

    parameter_values: list[ParameterValue] | None = Field(alias="Parameters", default=None)
    """The conditions under which the test is run (its indirect variables). See [`ParameterValue`][albert.resources.parameter_groups.ParameterValue]."""

    deleted_parameters: list[ParameterValue] | None = Field(
        alias="DeletedParameters", default=None, frozen=True, exclude=True
    )
    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="Metadata")
    """Custom metadata fields. Allowed keys are defined by the workspace's CustomFields configuration."""

    documents: list[EntityLink] = Field(
        default_factory=list, alias="Documents", exclude=True, frozen=True
    )

    # Read-only convenience fields from API
    original_name: str | None = Field(
        default=None, alias="originalName", exclude=True, frozen=True
    )
    """The original template name as stored in Albert. Read-only."""

    full_name: str | None = Field(default=None, alias="fullName", exclude=True, frozen=True)
    """The fully qualified template name. Read-only. See Also --------"""


class ImportMode(str, Enum):
    """How a curve example's source CSV is ingested.

    Attributes
    ----------
    SCRIPT
        Run the attached column script first, then import its output (requires a script
        attachment on the column).
    CSV
        Ingest the CSV file directly.
    """

    SCRIPT = "SCRIPT"
    CSV = "CSV"


class CurveExample(BaseAlbertModel):
    """An example row for a curve data column on a Data Template.

    Sets the example row shown only on the Data Template details page (not in tasks).
    A curve is a complex type, so it is sourced from a CSV file. Provide exactly one
    source: a local ``file_path`` or an existing ``attachment_id``. Pass this to
    [`set_curve_example`][albert.collections.data_templates.DataTemplateCollection.set_curve_example].

    !!! example
        ```python
        from albert.resources.data_templates import CurveExample

        example = CurveExample(file_path="viscosity_curve.csv")
        ```"""

    type: Literal[DataType.CURVE] = DataType.CURVE
    mode: ImportMode = ImportMode.CSV
    """``ImportMode.CSV`` ingests the CSV directly; ``ImportMode.SCRIPT`` runs the attached script first (requires a script attachment on the column). Defaults to CSV."""

    field_mapping: dict[str, str] | None = None
    """Optional header-to-curve-result mapping, e.g. ``{"visc": "Viscosity"}``. Overrides auto-detected mappings."""

    file_path: str | Path | None = None
    """Local path to the source CSV file."""

    attachment_id: AttachmentId | None = None
    """Existing attachment ID of the source CSV file. Provide exactly one source CSV (local path or existing attachment)."""

    @model_validator(mode="after")
    def _require_curve_source(self) -> CurveExample:
        if (self.file_path is None) == (self.attachment_id is None):
            raise ValueError(
                "Provide exactly one of file_path or attachment_id for curve examples."
            )
        return self


class ImageExample(BaseAlbertModel):
    """An example row for an image data column on a Data Template.

    Sets the example row shown only on the Data Template details page (not in tasks).
    An image is a complex type sourced from a local file. Pass this to
    [`set_image_example`][albert.collections.data_templates.DataTemplateCollection.set_image_example].

    !!! example
        ```python
        from albert.resources.data_templates import ImageExample

        example = ImageExample(file_path="fracture_surface.png")
        ```"""

    type: Literal[DataType.IMAGE] = DataType.IMAGE
    file_path: str | Path
    """Local path to the source image file."""


class DataTemplateSearchItemDataColumn(BaseAlbertModel):
    """A lightweight data column reference within a data template search result."""

    id: str
    """The Albert ID of the data column."""

    name: str | None = None
    """The name of the data column."""

    localized_names: LocalizedNames = Field(alias="localizedNames")
    """Localized name variants for the data column."""


class DataTemplateSearchItem(BaseAlbertModel, HydrationMixin[DataTemplate]):
    """Lightweight representation of a DataTemplate returned from search."""

    id: str = Field(alias="albertId")
    """The Albert ID of the data template."""

    name: str
    """The name of the data template."""

    data_columns: list[DataTemplateSearchItemDataColumn] | None = Field(
        alias="dataColumns", default=None
    )
    """The data column summaries included in the template."""

    owner: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="owner")
    """The owners of the data template."""

    tags: list[SerializeAsEntityLink[Tag]] | None = Field(default=None, alias="tags")
    """Tags associated with the data template."""

    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="acl")
    """Users with explicit access to the data template."""

    created_at: str | None = Field(default=None, alias="createdAt")
    """ISO 8601 timestamp of when the template was created."""

    created_by_name: str | None = Field(default=None, alias="createdByName")
    """The name of the user who created the template."""

    metadata: dict[str, Any] | None = Field(default=None, alias="metadata")
    """Custom metadata attached to the template."""

    team: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="team")
    """Team members associated with the template."""

    standards: list[dict[str, Any]] | None = Field(default=None, alias="standards")
    """Standards linked to the template."""
