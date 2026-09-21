from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource
from albert.resources.units_v4 import UnitFamilyV4Ref


class UnitFamilyV4Type(str, Enum):
    """Whether the units in a family convert between each other.

    Attributes
    ----------
    CONVERTIBLE : str
        The family has an SI basis and its units convert to one another.
    NON_CONVERTIBLE : str
        The family groups units with no SI mapping (for example counts).
    """

    CONVERTIBLE = "Convertible"
    NON_CONVERTIBLE = "Non-Convertible"


class UnitFamilyV4Origin(str, Enum):
    """Who manages a unit family definition.

    Attributes
    ----------
    ALBERT_MANAGED : str
        A global family maintained by Albert and shared across tenants.
    CUSTOM : str
        A family created by the tenant.
    """

    ALBERT_MANAGED = "Albert Managed"
    CUSTOM = "Custom"


class UnitFamilyV4(BaseResource):
    """A unit family in the v4 units API (🧪 Beta).

    A unit family groups related units (for example ``Mass`` holds ``kg``, ``g`` and
    ``lb``). Convertible families have an SI basis that Albert resolves from
    ``ref_unit`` or ``unit_expression`` on create. Managed through
    [`UnitFamilyV4Collection`][albert.collections.unit_families_v4.UnitFamilyV4Collection]
    (``client.unit_families_v4``).

    !!! example
        ```python
        from albert.resources.unit_families_v4 import UnitFamilyV4, UnitFamilyV4Type

        # Convertible: the SI unit and dimension are resolved from ref_unit
        mass = UnitFamilyV4(name="Mass", type=UnitFamilyV4Type.CONVERTIBLE, ref_unit="kg")

        # Non-convertible: no SI basis
        count = UnitFamilyV4(name="Count", type=UnitFamilyV4Type.NON_CONVERTIBLE)
        ```"""

    id: str | None = None
    """The unit family ID. Set when the family is retrieved from or created in Albert."""

    name: str
    """The unit family name (for example ``"Mass"``). Unique within the tenant."""

    description: str | None = None
    """A description of the unit family."""

    type: UnitFamilyV4Type
    """Whether the family is convertible (has an SI basis) or non-convertible."""

    ref_unit: str | None = Field(default=None, alias="refUnit")
    """The symbol of a global unit that defines the SI basis (convertible families only).
    Provide this or ``unit_expression`` on create. Not returned on read."""

    unit_expression: str | None = Field(default=None, alias="unitExpression")
    """A unit expression that defines the SI basis (for example ``"kg*m/s^2"``), convertible
    families only. Provide this or ``ref_unit`` on create. Not returned on read."""

    si_unit: str | None = Field(default=None, alias="siUnit")
    """The SI base unit symbol (for example ``"kg"``). Resolved by Albert for convertible families. Read-only."""

    dimension: str | None = None
    """The physical dimension (for example ``"Mass"``). Resolved by Albert for convertible families. Read-only."""

    origin: UnitFamilyV4Origin | None = None
    """Who manages the family definition. Read-only."""

    units: list[str] | None = None
    """Symbols of all units linked to this family. Read-only."""

    same_si_basis_families: list[UnitFamilyV4Ref] | None = Field(
        default=None, alias="sameSiBasisFamilies"
    )
    """Other unit families that share the same SI unit. Read-only."""


class UnitFamilyV4SearchItem(BaseResource):
    """A unit family record from a search result.

    Search results omit the computed ``units`` and ``same_si_basis_families`` fields.
    Use [`get_by_id`][albert.collections.unit_families_v4.UnitFamilyV4Collection.get_by_id]
    for the fully populated family.
    """

    id: str
    """The unit family ID."""

    name: str
    """The unit family name."""

    description: str | None = None
    """A description of the unit family."""

    type: UnitFamilyV4Type
    """Whether the family is convertible or non-convertible."""

    si_unit: str | None = Field(default=None, alias="siUnit")
    """The SI base unit symbol, if the family is convertible."""

    dimension: str | None = None
    """The physical dimension, if the family is convertible."""

    origin: UnitFamilyV4Origin | None = None
    """Who manages the family definition."""


class UnitFamilyV4Lookup(BaseAlbertModel):
    """The result of checking whether a unit family name is already in use."""

    exists: bool
    """Whether a unit family with the exact name exists."""

    similar_matches: list[UnitFamilyV4Ref] = Field(default_factory=list, alias="similarMatches")
    """Unit families whose name matches the value, ignoring case."""
