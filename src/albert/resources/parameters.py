from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


class SpecialParameterType(str, Enum):
    """The specific entity type referenced by a Special
    [`Parameter`][albert.resources.parameters.Parameter].

    Not returned by the platform parameter API (use Zeus reports RET48/RET52 to
    read the subtype from experiment data). Writable on
    [`ParameterValue`][albert.resources.parameter_groups.ParameterValue] and
    [`TargetParameter`][albert.resources.targets.TargetParameter].

    Each member implies an id-namespace for the value column in experiment reports
    (RET48/RET52): ``RAW_MATERIALS`` values carry ``INVA...`` ids, ``CONSUMABLES``
    carry ``INVB...`` ids, and ``EQUIPMENT`` carry ``INVC...`` ids.

    Attributes
    ----------
    RAW_MATERIALS : str
        A raw material entity. Values appear as ``INVA...`` ids in report columns.
    CONSUMABLES : str
        A consumable entity. Values appear as ``INVB...`` ids in report columns.
    EQUIPMENT : str
        An equipment entity. Values appear as ``INVC...`` ids in report columns.
    """

    RAW_MATERIALS = "RawMaterials"
    CONSUMABLES = "Consumables"
    EQUIPMENT = "Equipment"


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
