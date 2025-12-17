from enum import Enum

from pydantic import AliasChoices, Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass
from albert.core.shared.identifiers import DataColumnId, DataTemplateId
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
from albert.resources.parameter_groups import ParameterValue, ValueValidation
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.units import Unit
from albert.resources.users import User


class CSVMapping(BaseAlbertModel):
    map_id: str | None = Field(
        alias="mapId", default=None, examples="Header1:DAC2900#Header2:DAC4707"
    )
    map_data: dict[str, str] | None = Field(
        alias="mapData", default=None, examples={"Header1": "DAC2900", "Header2": "DAC4707"}
    )


class CurveDBMetadata(BaseAlbertModel):
    table_name: str | None = Field(default=None, alias="tableName")
    partition_key: str | None = Field(default=None, alias="partitionKey")


class StorageKeyReference(BaseAlbertModel):
    rawfile: str | None = None
    s3_input: str | None = Field(default=None, alias="s3Input")
    s3_output: str | None = Field(default=None, alias="s3Output")


class JobSummary(BaseAlbertModel):
    id: str | None = None
    state: str | None = None


class Axis(str, Enum):
    X = "X"
    Y = "Y"


class CurveDataEntityLink(EntityLinkWithName):
    id: DataColumnId
    axis: Axis | None = Field(default=None)
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")


class DataColumnValue(BaseResource):
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


class Axis(str, Enum):
    X = "X"
    Y = "Y"


class DataTemplate(BaseTaggedResource):
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


class DataTemplateSearchItemDataColumn(BaseAlbertModel):
    id: str
    name: str | None = None
    localized_names: LocalizedNames = Field(alias="localizedNames")


class DataTemplateSearchItem(BaseAlbertModel, HydrationMixin[DataTemplate]):
    id: str = Field(alias="albertId")
    name: str
    data_columns: list[DataTemplateSearchItemDataColumn] | None = Field(
        alias="dataColumns", default=None
    )
