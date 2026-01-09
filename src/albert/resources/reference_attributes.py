from __future__ import annotations

from pydantic import Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DataColumnId,
    ParameterId,
    ReferenceAttributeId,
    UnitId,
)
from albert.core.shared.models.base import AuditFields, BaseResource
from albert.core.shared.types import SerializeAsEntityLink
from albert.resources.data_columns import DataColumn
from albert.resources.parameter_groups import ValueValidation
from albert.resources.parameters import ParameterCategory
from albert.resources.units import Unit
from albert.resources.workflows import Workflow


class ReferenceAttributeParameter(BaseAlbertModel):
    """
    Parameter value attached to a reference attribute.

    Attributes
    ----------
    id : ParameterId
        The parameter identifier.
    category : ParameterCategory | None
        The parameter category.
    value : str | float | int | None
        The parameter value.
    unit_id : UnitId | None
        The unit identifier for the parameter value.
    unit : SerializeAsEntityLink[Unit] | None
        The unit information for the parameter value.
    name : str | None
        The parameter name.
    """

    id: ParameterId
    category: ParameterCategory | None = None
    value: str | float | int | None = None
    unit_id: UnitId | None = Field(default=None, alias="unitId")
    unit: SerializeAsEntityLink[Unit] | None = Field(
        default=None,
        alias="unit",
    )
    name: str | None = None


class ReferenceAttribute(BaseResource):
    """
    Represents a reference attribute.

    Attributes
    ----------
    id : ReferenceAttributeId | None
        The Albert identifier for the reference attribute.
    reference_name : str | None
        The reference attribute name.
    full_name : str | None
        The full name (data column name + reference attribute name).
    name_override : bool | None
        Whether the name was overridden.
    data_column : SerializeAsEntityLink[DataColumn] | None
        The linked data column.
    data_column_id : DataColumnId | None
        The linked data column identifier.
    unit : SerializeAsEntityLink[Unit] | None
        The linked unit.
    unit_id : UnitId | None
        The linked unit identifier.
    workflow : SerializeAsEntityLink[Workflow] | None
        The linked workflow.
    validation : list[ValueValidation] | None
        Validation rules for the reference attribute.
    parameters : list[ReferenceAttributeParameter] | None
        Parameter values for the reference attribute.
    status : Status | None
        The reference attribute status.
    created : AuditFields | None
        Audit fields for creation.
    updated : AuditFields | None
        Audit fields for last update.
    """

    id: ReferenceAttributeId | None = Field(default=None, alias="albertId")
    reference_name: str | None = Field(default=None, alias="referenceName")
    full_name: str | None = Field(default=None, alias="fullName")
    name_override: bool | None = Field(default=None, alias="nameOverride")
    data_column: SerializeAsEntityLink[DataColumn] | None = Field(default=None, alias="datacolumn")
    data_column_id: DataColumnId | None = Field(default=None, alias="datacolumnId")
    unit: SerializeAsEntityLink[Unit] | None = Field(default=None, alias="unit")
    unit_id: UnitId | None = Field(default=None, alias="unitId")
    workflow: SerializeAsEntityLink[Workflow] | None = Field(default=None, alias="workflow")
    validation: list[ValueValidation] | None = None
    parameters: list[ReferenceAttributeParameter] | None = None

    created: AuditFields | None = Field(default=None, alias="created", frozen=True)
    updated: AuditFields | None = Field(default=None, alias="updated", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_parameters(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        parameters = data.get("parameters") or data.get("Parameters")
        if isinstance(parameters, dict):
            data["parameters"] = parameters.get("values", [])
        return data

    @model_validator(mode="after")
    def _normalize_linked_ids(self) -> ReferenceAttribute:
        if self.data_column_id is None and self.data_column is not None:
            object.__setattr__(self, "data_column_id", self.data_column.id)
        if self.unit_id is None and self.unit is not None:
            object.__setattr__(self, "unit_id", self.unit.id)
        return self
