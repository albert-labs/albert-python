from enum import Enum

from pydantic import AliasChoices, Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class UnitV4Type(str, Enum):
    """Whether a unit can be converted to other units in its family.

    Attributes
    ----------
    CONVERTIBLE : str
        The unit has an SI mapping and converts to other units sharing that SI basis.
    NON_CONVERTIBLE : str
        The unit has no SI mapping (for example ``batch`` or ``piece``).
    """

    CONVERTIBLE = "Convertible"
    NON_CONVERTIBLE = "Non-Convertible"


class UnitV4Origin(str, Enum):
    """Who manages a unit definition.

    Attributes
    ----------
    ALBERT_MANAGED : str
        A global unit maintained by Albert and shared across tenants.
    CUSTOM : str
        A unit created by the tenant.
    CUSTOM_LEGACY : str
        A tenant unit carried over from the previous units API that has not yet been
        set up with a type and SI mapping.
    """

    ALBERT_MANAGED = "Albert Managed"
    CUSTOM = "Custom"
    CUSTOM_LEGACY = "Custom (Legacy)"


class UnitFamilyV4Ref(BaseAlbertModel):
    """A reference to a unit family from a unit.

    !!! example
        ```python
        from albert.resources.units_v4 import UnitFamilyV4Ref
        family = UnitFamilyV4Ref(id="UNF1")
        ```"""

    id: str = Field(validation_alias=AliasChoices("id", "familyId"))
    """The unit family ID. Units endpoints return it as ``familyId``; both keys are accepted."""

    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "familyName"))
    """The unit family name. Populated on records returned from Albert (as ``familyName``);
    optional when referencing a family by ID on create."""


class UnitV4Ref(BaseAlbertModel):
    """A lightweight reference to a unit, as returned by
    [`lookup`][albert.collections.units_v4.UnitV4Collection.lookup]."""

    id: str
    """The unit ID."""

    name: str
    """The unit name."""

    symbol: str
    """The unit symbol."""


class UnitV4(BaseResource):
    """A unit of measure in the v4 units API (🧪 Beta).

    Units are grouped into unit families (for example ``Mass`` or ``Length``).
    Convertible units carry an SI mapping that Albert resolves from ``ref_unit`` or
    ``ref_unit_exp`` on create; non-convertible units are linked to families directly.
    Managed through [`UnitV4Collection`][albert.collections.units_v4.UnitV4Collection]
    (``client.units_v4``).

    !!! example
        ```python
        from albert.resources.units_v4 import UnitV4, UnitV4Type

        # Convertible: SI unit, SI value and families are resolved from ref_unit
        grams = UnitV4(name="Grams", symbol="g", type=UnitV4Type.CONVERTIBLE, ref_unit="g")

        # Non-convertible: link families explicitly
        batch = UnitV4(
            name="Batch",
            symbol="batch",
            type=UnitV4Type.NON_CONVERTIBLE,
            unit_families=[UnitFamilyV4Ref(id="UNF3")],
        )
        ```"""

    id: str | None = None
    """The unit ID. Set when the unit is retrieved from or created in Albert."""

    name: str
    """The unit name (for example ``"Grams"``)."""

    description: str | None = None
    """A description of the unit."""

    type: UnitV4Type | None = None
    """Whether the unit is convertible (has an SI mapping) or non-convertible. Required on
    create; absent on Custom (Legacy) units until they are set up via
    [`update`][albert.collections.units_v4.UnitV4Collection.update]."""

    symbol: str
    """The unit symbol (for example ``"g"``). Unique within the tenant."""

    synonyms: list[str] | None = None
    """Alternate names or spellings that also refer to this unit."""

    si_unit: str | None = Field(default=None, alias="siUnit")
    """The SI base unit symbol (for example ``"kg"``). Resolved by Albert for convertible units. Read-only."""

    si_value: str | None = Field(default=None, alias="siValue")
    """The conversion factor from this unit to ``si_unit``. Resolved by Albert for convertible units. Read-only."""

    ref_unit: str | None = Field(default=None, alias="refUnit")
    """The symbol of a global unit this unit is defined relative to (convertible units only).
    Provide this or ``ref_unit_exp`` on create."""

    ref_unit_exp: str | None = Field(default=None, alias="refUnitExp")
    """A unit expression this unit is defined by (for example ``"1000*g"``), convertible units only.
    Provide this or ``ref_unit`` on create."""

    ref_unit_value: str | None = Field(default=None, alias="refUnitValue")
    """The conversion factor from this unit to ``ref_unit`` (convertible units only)."""

    origin: UnitV4Origin | None = None
    """Who manages the unit definition. Read-only."""

    unit_families: list[UnitFamilyV4Ref] | None = Field(default=None, alias="unitFamilies")
    """The unit families this unit belongs to. Resolved by Albert for convertible units;
    provide the family IDs for non-convertible units."""


class UnitV4Lookup(BaseAlbertModel):
    """The result of checking whether a unit name or symbol is already in use."""

    exists: bool
    """Whether a unit with the exact value exists."""

    similar_matches: list[UnitV4Ref] = Field(default_factory=list, alias="similarMatches")
    """Units whose symbol or name matches the value, ignoring case."""


class UnitV4Compatible(BaseAlbertModel):
    """The SI mapping and compatible unit families resolved for a unit symbol or expression.

    Returned by
    [`get_compatible`][albert.collections.units_v4.UnitV4Collection.get_compatible];
    use it to preview the fields Albert will populate before creating a convertible unit.
    """

    ref_unit: str | None = Field(default=None, alias="refUnit")
    """The symbol of the resolved reference unit."""

    si_unit: str | None = Field(default=None, alias="siUnit")
    """The SI base unit symbol."""

    si_value: str | None = Field(default=None, alias="siValue")
    """The conversion factor to the SI base unit."""

    ref_unit_value: str | None = Field(default=None, alias="refUnitValue")
    """The coefficient extracted from the expression. Only present for expression-based lookups."""

    dimension: str | None = None
    """The physical dimension (for example ``"Mass"``)."""

    unit_families: list[UnitFamilyV4Ref] = Field(default_factory=list, alias="unitFamilies")
    """Unit families that share the resolved SI unit."""
