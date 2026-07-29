from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import SecurityClass
from albert.core.shared.models.base import AuditFields, EntityLink, LocalizedNames
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.inventory import InventoryItem
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.tagged_base import BaseTaggedResource
from albert.resources.tags import Tag
from albert.resources.units import Unit
from albert.resources.users import User


class PGType(str, Enum):
    """The kind of task a [`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup] relates to.

    A Parameter Group is about making a sample and/or prepping it for measurement,
    and its type records which sort of task it is used in.

    Attributes
    ----------
    GENERAL : str
        A group used in a general lab task (anything that is not a batch or
        property task).
    BATCH : str
        A group used in a Batch Task ([`BatchTask`][albert.resources.tasks.BatchTask]),
        e.g. a mixing step when manufacturing a batch.
    PROPERTY : str
        A group used in a property (measurement) task to prep a sample for testing.
    """

    GENERAL = "general"
    BATCH = "batch"
    PROPERTY = "property"


class DataType(str, Enum):
    """The data type of a parameter value, driving how it is validated.

    Used by [`ValueValidation`][albert.resources.parameter_groups.ValueValidation] to declare what kind of value a parameter
    accepts.

    Attributes
    ----------
    NUMBER : str
        A numeric value.
    STRING : str
        A free-text string value.
    ENUM : str
        A value restricted to a fixed set of options (see
        [`EnumValidationValue`][albert.resources.parameter_groups.EnumValidationValue]).
    IMAGE : str
        An image value.
    CURVE : str
        A curve (series) value.
    DATE : str
        A calendar date value stored as ``YYYY-MM-DD``.
    TIMESTAMP : str
        A date-and-time value in ISO 8601 format with a UTC offset
        (e.g. ``2026-05-21T14:32:00+02:00``).
    """

    NUMBER = "number"
    STRING = "string"
    ENUM = "enum"
    IMAGE = "image"
    CURVE = "curve"
    DATE = "date"
    TIMESTAMP = "timestamp"


class Operator(str, Enum):
    """A comparison operator constraining a numeric parameter value.

    Used by [`ValueValidation`][albert.resources.parameter_groups.ValueValidation] to bound acceptable values (e.g. ``gte`` with
    a ``min`` requires the value to be at least ``min``).

    Attributes
    ----------
    BETWEEN : str
        Value must fall between ``min`` and ``max`` (inclusive).
    LESS_THAN : str
        Value must be less than ``max``.
    LESS_THAN_OR_EQUAL : str
        Value must be less than or equal to ``max``.
    GREATER_THAN_OR_EQUAL : str
        Value must be greater than or equal to ``min``.
    GREATER_THAN : str
        Value must be greater than ``min``.
    EQUALS : str
        Value must equal the specified value.
    """

    BETWEEN = "between"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN_OR_EQUAL = "gte"
    GREATER_THAN = "gt"
    EQUALS = "eq"


class EnumValidationValue(BaseAlbertModel):
    """Represents a value for an enum type validation."""

    text: str = Field()
    """The text of the enum value."""

    id: str | None = Field(default=None)
    """The ID of the enum value. If not provided, the ID will be generated upon creation."""
    # read only field
    original_text: str | None = Field(
        default=None, exclude=True, frozen=True, alias="originalText"
    )


class ValueValidation(BaseAlbertModel):
    """A validation rule constraining a [`ParameterValue`][albert.resources.parameter_groups.ParameterValue].

    Declares the expected [`DataType`][albert.resources.parameter_groups.DataType] for a parameter value and, optionally,
    the bounds or allowed options it must satisfy. Attach one or more of these to a
    [`ParameterValue`][albert.resources.parameter_groups.ParameterValue] via its ``validation`` field.

    When ``datatype`` is ``date`` or ``timestamp``, ``value``, ``min``, and ``max`` are
    strings in the wire format documented on [`DataType`][albert.resources.parameter_groups.DataType].

    !!! example
        ```python
        from albert.resources.parameter_groups import (
            DataType,
            Operator,
            ValueValidation,
        )

        rule = ValueValidation(
            datatype=DataType.NUMBER,
            operator=Operator.BETWEEN,
            min="0",
            max="100",
        )
        ```"""

    datatype: DataType = Field(...)
    """The data type the value must conform to. Required."""

    value: str | list[EnumValidationValue] | None = Field(default=None)
    """For ``ENUM`` types, the list of allowed options (see [`EnumValidationValue`][albert.resources.parameter_groups.EnumValidationValue]); otherwise an optional expected value. For ``date`` and ``timestamp`` types, a string in the wire format documented on [`DataType`][albert.resources.parameter_groups.DataType]."""

    min: str | None = Field(default=None)
    """The lower bound, used with ``operator``. For numeric types, a numeric string; for ``date`` and ``timestamp`` types, a string in the wire format documented on [`DataType`][albert.resources.parameter_groups.DataType]."""

    max: str | None = Field(default=None)
    """The upper bound, used with ``operator``. For numeric types, a numeric string; for ``date`` and ``timestamp`` types, a string in the wire format documented on [`DataType`][albert.resources.parameter_groups.DataType]."""

    operator: Operator | None = Field(default=None)
    """The comparison operator applied against ``min`` and/or ``max``."""


class ParameterValue(BaseAlbertModel):
    """A single [`Parameter`][albert.resources.parameters.Parameter] and its value within a [`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup].

    A ``ParameterValue`` binds one Parameter to the value, unit, and validation
    rules it takes inside a group. Each entry must reference an existing Parameter,
    so provide exactly one of ``id`` (the Parameter's Albert ID) or ``parameter``
    (the [`Parameter`][albert.resources.parameters.Parameter] object itself); when a
    ``parameter`` is given, the ``id``, ``category``, and ``name`` are populated
    from it. Values are later fixed to setpoints inside a
    [`Workflow`][albert.resources.workflows.Workflow].

    !!! example
        ```python
        from albert.resources.parameter_groups import ParameterValue

        # Reference the parameter by its Albert ID
        value = ParameterValue(id="PRM1", value="500")
        ```"""

    parameter: Parameter | None = Field(default=None, exclude=True)
    """The Parameter this value is associated with. Provide either ``id`` or ``parameter``. Excluded from serialization."""

    id: str | None = Field(default=None)
    """The Albert ID of the associated Parameter. Provide either ``id`` or ``parameter``."""

    category: ParameterCategory | None = Field(default=None)
    """The category of the parameter (``Normal`` or ``Special``). Populated from ``parameter`` when one is provided."""

    short_name: str | None = Field(alias="shortName", default=None)
    """A short name for the parameter value. Serialized as ``shortName``."""

    value: str | SerializeAsEntityLink[InventoryItem] | SerializeAsEntityLink[User] | None = Field(
        default=None
    )
    """The value of the parameter. Can be a plain string, an [`InventoryItem`][albert.resources.inventory.InventoryItem] (e.g. when the parameter represents an instrument choice), or a [`User`][albert.resources.users.User] (e.g. a user reference such as "Performed By")."""

    unit: SerializeAsEntityLink[Unit] | None = Field(alias="Unit", default=None)
    """The unit of measure for the value. Serialized as ``Unit``."""

    added: AuditFields | None = Field(alias="Added", default=None, exclude=True)
    required: bool | None = Field(default=None)
    """Whether this parameter is required. Defaults to False."""

    validation: list[ValueValidation] | None = Field(default_factory=list)
    """Validation rules applied to the value. See [`ValueValidation`][albert.resources.parameter_groups.ValueValidation]."""

    # Read-only fields
    name: str | None = Field(default=None, exclude=True, frozen=True)
    """The name of the parameter. Read-only."""

    sequence: str | None = Field(default=None, exclude=True)
    """The sequence of the parameter within the group. Read-only."""

    original_short_name: str | None = Field(
        default=None, alias="originalShortName", frozen=True, exclude=True
    )
    original_name: str | None = Field(
        default=None, alias="originalName", frozen=True, exclude=True
    )

    @field_validator("value", mode="before")
    @classmethod
    def validate_parameter_value(cls, value: Any) -> Any:
        # Bug in ParameterGroups sometimes returns incorrect JSON from batch endpoint
        # Set to None if value is a dict but no ID field
        # Reference: https://linear.app/albert-invent/issue/IN-10
        if isinstance(value, dict) and "id" not in value:
            return None
        return value

    @model_validator(mode="after")
    def set_parameter_fields(self) -> ParameterValue:
        if self.parameter is None and self.id is None:
            raise ValueError("Please provide either an id or an parameter object.")

        if self.parameter is not None:
            object.__setattr__(self, "id", self.parameter.id)
            object.__setattr__(self, "category", self.parameter.category)
            object.__setattr__(self, "name", self.parameter.name)

        return self


class ParameterGroup(BaseTaggedResource):
    """A reusable set of parameters (PRG) for making or prepping a sample.

    A Parameter Group bundles [`Parameter`][albert.resources.parameters.Parameter]
    entities, along with their values, units, and validation rules, into a reusable
    unit. Whereas a Data Template's parameters relate to a given measurement, a
    Parameter Group is about *making* the sample and/or *prepping* it for
    measurement (e.g. a mixing step or a cure schedule). Some groups drive Batch
    Tasks ([`BatchTask`][albert.resources.tasks.BatchTask]); others are stacked within a
    task. A group's parameters, together with a Data Template's parameters, are
    fixed to setpoints inside a [`Workflow`][albert.resources.workflows.Workflow].

    Once saved, a group is referenced by its Parameter Group ID (format ``PRG...``,
    e.g. ``"PRG1"``). Store test standards (e.g. ASTM or ISO) under the
    ``"Standards"`` key of ``metadata``.

    Groups are managed through
    [`ParameterGroupCollection`][albert.collections.parameter_groups.ParameterGroupCollection]
    (``client.parameter_groups``).

    !!! example
        ```python
        from albert.resources.parameter_groups import (
            ParameterGroup,
            ParameterValue,
            PGType,
        )

        pg = ParameterGroup(
            name="Mixing Step",
            type=PGType.BATCH,
            parameters=[ParameterValue(id="PRM1", value="500")],
        )
        ```"""

    name: str
    """The name of the parameter group. Required."""

    type: PGType | None = Field(default=None)
    """The kind of task the group relates to (``general``, ``batch``, or ``property``)."""

    id: str | None = Field(None, alias="albertId")
    """The Albert Parameter Group ID (format ``PRG...``). Set when the group is retrieved from or created in Albert. Serialized as ``albertId``."""

    description: str | None = Field(default=None)
    """A free-text description of the group."""

    security_class: SecurityClass = Field(default=SecurityClass.RESTRICTED, alias="class")
    """The access/security class of the group. Defaults to ``RESTRICTED``. Serialized as ``class``."""

    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="ACL")
    """Access-control entries governing who can act on the group. Serialized as ``ACL``."""

    metadata: dict[str, MetadataItem] = Field(alias="Metadata", default_factory=dict)
    """Custom metadata fields. Test standards are stored under the ``"Standards"`` key. Serialized as ``Metadata``."""

    parameters: list[ParameterValue] = Field(default_factory=list, alias="Parameters")
    """The parameters in the group, each with its value, unit, and validation. See [`ParameterValue`][albert.resources.parameter_groups.ParameterValue]. Serialized as ``Parameters``."""

    # Read-only fields
    verified: bool = Field(default=False, exclude=True, frozen=True)
    """Whether the group has been verified (an approval/governance state). Read-only."""

    documents: list[EntityLink] = Field(default_factory=list, exclude=True, frozen=True)
    """Documents (e.g. SOPs) associated with the Parameter Group. See Also --------"""


class ParameterSearchItemParameter(BaseAlbertModel):
    """A lightweight parameter reference within a parameter group search result."""

    name: str | None = None
    """The name of the parameter."""

    id: str
    """The Albert ID of the parameter."""

    localized_names: LocalizedNames = Field(alias="localizedNames")
    """Localized name variants for the parameter."""


class ParameterGroupSearchItem(BaseAlbertModel, HydrationMixin[ParameterGroup]):
    """A lightweight, partially populated parameter group from search results.

    Returned by
    [`search`][albert.collections.parameter_groups.ParameterGroupCollection.search].
    Search results omit some detail for speed; call `hydrate()` to fetch the
    full [`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup]."""

    name: str
    """The name of the parameter group."""

    type: PGType | None = Field(default=None)
    """The kind of task the group relates to."""

    id: str | None = Field(None, alias="albertId")
    """The Albert Parameter Group ID (format ``PRG...``). Serialized as ``albertId``."""

    description: str | None = Field(default=None)
    """A free-text description of the group."""

    parameters: list[ParameterSearchItemParameter] = Field(
        default_factory=list, alias="parameters"
    )
    """Lightweight references to the parameters in the group."""

    owner: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="owner")
    """The owner(s) of the group."""

    tags: list[SerializeAsEntityLink[Tag]] | None = Field(default=None, alias="tags")
    """Tags on the group."""

    acl: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="acl")
    """Access-control entries on the group."""

    created_at: str | None = Field(default=None, alias="createdAt")
    """When the group was created. Serialized as ``createdAt``."""

    created_by_name: str | None = Field(default=None, alias="createdByName")
    """The name of the user who created the group. Serialized as ``createdByName``."""

    metadata: dict[str, MetadataItem] | None = Field(default=None, alias="metadata")
    """Custom metadata fields. Serialized as ``metadata``."""

    team: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="team")
    """The team associated with the group."""
