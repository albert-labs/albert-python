from pydantic import Field, model_validator

from albert.resources.base import (
    BaseAlbertModel,
    MetadataItem,
    SecurityClass,
)
from albert.resources.data_columns import DataColumn
from albert.resources.identifiers import DataTemplateId
from albert.resources.parameter_groups import ParameterValue, ValueValidation
from albert.resources.serialization import SerializeAsEntityLink
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


class DataColumnValue(BaseAlbertModel):
    data_column: DataColumn = Field(exclude=True, default=None)
    data_column_id: str = Field(alias="id", default=None)
    value: str | None = None
    hidden: bool = False
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="Unit")
    calculation: str | None = None
    sequence: str | None = Field(default=None, exclude=True)
    validation: list[ValueValidation] | None = Field(default_factory=list)

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
    name: str
    id: DataTemplateId | None = Field(None, alias="albertId")
    description: str | None = None
    security_class: SecurityClass | None = None
    verified: bool = False
    users_with_access: list[SerializeAsEntityLink[User]] | None = Field(alias="ACL", default=None)
    data_column_values: list[DataColumnValue] | None = Field(alias="DataColumns", default=None)
    parameter_values: list[ParameterValue] | None = Field(alias="Parameters", default=None)
    deleted_parameters: list[ParameterValue] | None = Field(
        alias="DeletedParameters", default=None, frozen=True, exclude=True
    )
    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="Metadata")
