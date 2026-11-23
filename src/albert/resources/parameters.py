from enum import Enum
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import Status
from albert.core.shared.identifiers import ParameterId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem
from albert.resources._mixins import HydrationMixin


class SpecialParameterType(str, Enum):
    """The specific entity type referenced by a Special
    [`Parameter`][albert.resources.parameters.Parameter].

    Not returned by the platform parameter API (use Zeus reports RET48/RET52 to
    read the subtype from experiment data). Writable on
    [`ParameterValue`][albert.resources.parameter_groups.ParameterValue] and
    [`TargetParameter`][albert.resources.targets.TargetParameter].

    Each member implies an id-namespace for the value column in experiment reports
    (RET48/RET52): ``RAW_MATERIALS`` values carry ``INVA...`` ids, ``CONSUMABLES``
    carry ``INVB...`` ids, ``EQUIPMENT`` carry ``INVC...`` ids, and ``FORMULAS``
    carry ``INVMO...`` ids.

    Mirrors [`InventoryCategory`][albert.resources.inventory.InventoryCategory],
    the canonical "kind of material" an
    [`InventoryItem`][albert.resources.inventory.InventoryItem] belongs to. A
    Special parameter's value is always a reference to an `InventoryItem`, so its
    subtype is one of that enum's members.

    Attributes
    ----------
    RAW_MATERIALS : str
        A raw material entity. Values appear as ``INVA...`` ids in report columns.
    CONSUMABLES : str
        A consumable entity. Values appear as ``INVB...`` ids in report columns.
    EQUIPMENT : str
        An equipment entity. Values appear as ``INVC...`` ids in report columns.
    FORMULAS : str
        A formula entity (a mixture designed through a Worksheet). Values appear
        as ``INVMO...`` ids in report columns.
    """

    RAW_MATERIALS = "RawMaterials"
    CONSUMABLES = "Consumables"
    EQUIPMENT = "Equipment"
    FORMULAS = "Formulas"


class ParameterCategory(str, Enum):
    """Whether a [`Parameter`][albert.resources.parameters.Parameter]'s value is a plain scalar or an entity reference.

    Set by the platform and read-only. It determines how a parameter's value is
    interpreted when a setpoint is assigned to it inside a
    [`Workflow`][albert.resources.workflows.Workflow].

    Attributes
    ----------
    NORMAL : str
        A "normal" parameter whose value is a plain scalar (e.g. a number or text),
        such as Temperature or Spin Speed.
    SPECIAL : str
        A "special" parameter whose value references another entity (e.g. Equipment,
        a Consumable, or a Template). The setpoint value is that entity's ID rather
        than a plain scalar.
    """

    NORMAL = "Normal"
    SPECIAL = "Special"


class Parameter(BaseResource):
    """The definition of a single experimental condition or input variable.

    A Parameter (ID format ``PRM...``) names an "indirect variable" such as
    Temperature, Spin Speed, or Instrument. The Parameter itself only defines the
    variable; its actual value and unit are fixed to a setpoint later, inside a
    [`Workflow`][albert.resources.workflows.Workflow]. Parameters are the building
    blocks of Parameter Groups
    ([`ParameterGroup`][albert.resources.parameter_groups.ParameterGroup]) and form the
    parameter side of Data Templates
    ([`DataTemplate`][albert.resources.data_templates.DataTemplate]).

    Manage parameters through
    [`ParameterCollection`][albert.collections.parameters.ParameterCollection]
    (``client.parameters``).

    !!! example
        ```python
        from albert import Albert
        from albert.resources.parameters import Parameter
        client = Albert()
        param = client.parameters.create(parameter=Parameter(name="Temperature"))
        param.id
        # 'PRM9999999'
        ```"""

    name: str
    """The name of the parameter. Names must be unique."""

    id: str | None = Field(alias="albertId", default=None)
    """The Albert ID of the parameter (format ``PRM...``). Set when the parameter is retrieved from or created in Albert."""

    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    """Optional user-defined metadata keyed by field name."""

    # Read-only fields
    category: ParameterCategory | None = Field(default=None, exclude=True, frozen=True)
    """Whether the parameter is ``Normal`` (scalar value) or ``Special`` (entity reference). Set by the platform and read-only."""

    rank: int | None = Field(default=None, exclude=True, frozen=True)
    """The rank of the returned parameter. Read-only."""

    required: bool | None = Field(default=None, exclude=True)
    """Whether this parameter must be filled in within a Parameter Group."""


class ParameterSearchItemLink(BaseAlbertModel):
    """A lightweight data template or parameter group reference in a parameter search result."""

    id: str | None = None
    """The Albert ID of the linked resource."""

    name: str | None = None
    """The display name of the linked resource."""

    status: Status | None = None
    """The lifecycle status of the linked resource."""


class ParameterSearchItem(BaseAlbertModel, HydrationMixin[Parameter]):
    """A lightweight, partially populated parameter from search results.

    Returned by
    [`search`][albert.collections.parameters.ParameterCollection.search]. When ``id`` is present,
    call ``hydrate()`` to fetch the fully populated
    [`Parameter`][albert.resources.parameters.Parameter]. Results without an ``id`` cannot be hydrated.
    """

    model_config = ConfigDict(extra="allow")

    id: ParameterId | None = Field(
        default=None,
        alias="albertId",
        validation_alias=AliasChoices("albertId", "id"),
    )
    """The Albert ID of the parameter (format ``PRM...``). ``None`` when omitted from the result."""

    name: str | None = None
    """The name of the parameter."""

    status: Status | None = None
    """The lifecycle status of the parameter."""

    created_by: str | None = Field(default=None, alias="createdBy")
    """The ID of the user who created the parameter."""

    created_by_name: str | None = Field(default=None, alias="createdByName")
    """The display name of the user who created the parameter."""

    created_at: str | None = Field(default=None, alias="createdAt")
    """ISO 8601 timestamp of when the parameter was created."""

    updated_at: str | None = Field(default=None, alias="updatedAt")
    """ISO 8601 timestamp of when the parameter was last updated."""

    metadata: dict[str, Any] | None = Field(
        default=None,
        alias="Metadata",
        validation_alias=AliasChoices("Metadata", "metadata"),
    )
    """Custom metadata attached to the parameter."""

    parameter_groups: list[ParameterSearchItemLink] | None = Field(
        default=None,
        alias="parameterGroups",
        validation_alias=AliasChoices("parameterGroups", "ParameterGroups"),
    )
    """Parameter groups linked to the parameter."""

    data_templates: list[ParameterSearchItemLink] | None = Field(
        default=None,
        alias="dataTemplates",
        validation_alias=AliasChoices("dataTemplates", "DataTemplates"),
    )
    """Data templates linked to the parameter."""
