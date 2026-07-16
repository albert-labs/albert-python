from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


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

    Attributes
    ----------
    name : str
        The name of the parameter. Names must be unique.
    id : str | None
        The Albert ID of the parameter (format ``PRM...``). Set when the parameter
        is retrieved from or created in Albert.
    metadata : dict[str, MetadataItem] | None
        Optional user-defined metadata keyed by field name.
    category : ParameterCategory | None
        Whether the parameter is ``Normal`` (scalar value) or ``Special`` (entity
        reference). Set by the platform and read-only.
    rank : int | None
        The rank of the returned parameter. Read-only.
    required : bool | None
        Whether this parameter must be filled in within a Parameter Group.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.parameters import Parameter
        client = Albert()
        param = client.parameters.create(parameter=Parameter(name="Temperature"))
        param.id
        # 'PRM1'
        ```
    """

    name: str
    id: str | None = Field(alias="albertId", default=None)
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    # Read-only fields
    category: ParameterCategory | None = Field(default=None, exclude=True, frozen=True)
    rank: int | None = Field(default=None, exclude=True, frozen=True)
    required: bool | None = Field(default=None, exclude=True)
