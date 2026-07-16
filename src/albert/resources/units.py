from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import BaseResource


class UnitCategory(str, Enum):
    """The physical quantity a unit measures.

    Attributes
    ----------
    LENGTH : str
        Length units (e.g. m, cm).
    VOLUME : str
        Volume units (e.g. m³).
    LIQUID_VOLUME : str
        Liquid volume units (e.g. L, mL).
    ANGLES : str
        Angle units (e.g. degrees, radians).
    TIME : str
        Time units (e.g. s, h).
    FREQUENCY : str
        Frequency units (e.g. Hz).
    MASS : str
        Mass units (e.g. g, kg).
    CURRENT : str
        Electric current units (e.g. A).
    TEMPERATURE : str
        Temperature units (e.g. °C, K).
    AMOUNT : str
        Amount of substance units (e.g. mol).
    LUMINOSITY : str
        Luminous intensity units (e.g. cd).
    FORCE : str
        Force units (e.g. N).
    ENERGY : str
        Energy units (e.g. J).
    POWER : str
        Power units (e.g. W).
    PRESSURE : str
        Pressure units (e.g. Pa, bar).
    ELECTRICITY_AND_MAGNETISM : str
        Electricity and magnetism units.
    OTHER : str
        Units that do not fit another category.
    WEIGHT : str
        Weight units.
    AREA : str
        Area units (e.g. m²).
    SURFACE_AREA : str
        Surface area units.
    BINARY : str
        Binary/digital-information units (e.g. bytes).
    CAPACITANCE : str
        Capacitance units (e.g. F).
    SPEED : str
        Speed units (e.g. m/s).
    ELECTRICAL_CONDUCTIVITY : str
        Electrical conductivity units.
    ELECTRICAL_PERMITTIVITY : str
        Electrical permittivity units.
    DENSITY : str
        Density units (e.g. g/mL).
    RESISTANCE : str
        Electrical resistance units (e.g. Ω).
    """

    LENGTH = "Length"
    VOLUME = "Volume"
    LIQUID_VOLUME = "Liquid volume"
    ANGLES = "Angles"
    TIME = "Time"
    FREQUENCY = "Frequency"
    MASS = "Mass"
    CURRENT = "Electric current"
    TEMPERATURE = "Temperature"
    AMOUNT = "Amount of substance"
    LUMINOSITY = "Luminous intensity"
    FORCE = "Force"
    ENERGY = "Energy"
    POWER = "Power"
    PRESSURE = "Pressure"
    ELECTRICITY_AND_MAGNETISM = "Electricity and magnetism"
    OTHER = "Other"
    WEIGHT = "Weight"
    AREA = "Area"
    SURFACE_AREA = "Surface Area"
    BINARY = "Binary"
    CAPACITANCE = "Capacitance"
    SPEED = "Speed"
    ELECTRICAL_CONDUCTIVITY = "Electrical conductivity"
    ELECTRICAL_PERMITTIVITY = "Electrical permitivitty"
    DENSITY = "Density"
    RESISTANCE = "Resistance"


class Unit(BaseResource):
    """A unit of measure (e.g. ``g``, ``mL``, ``°C``).

    Units qualify quantities throughout the platform: inventory amounts,
    parameter values, and property results. Managed through
    [`UnitCollection`][albert.collections.units.UnitCollection] (``client.units``).

    Attributes
    ----------
    id : str or None
        The Albert ID of the unit (format ``UNI...``). Set when the unit is
        retrieved from or created in Albert.
    name : str
        The name of the unit (e.g. ``"gram"``).
    symbol : str or None
        The display symbol for the unit (e.g. ``"g"``).
    synonyms : list[str] or None
        Alternate names or spellings that also refer to this unit.
    category : UnitCategory or None
        The physical quantity the unit measures (e.g. ``Mass``, ``Volume``).
    verified : bool or None
        Whether the unit has been verified in Albert. Read-only.

    !!! example
        ```python
        from albert.resources.units import Unit, UnitCategory
        unit = Unit(name="milliliter", symbol="mL", category=UnitCategory.LIQUID_VOLUME)
        ```
    """

    id: str | None = Field(None, alias="albertId")
    name: str
    symbol: str | None = Field(None)
    synonyms: list[str] | None = Field(default_factory=list, alias="Synonyms")
    category: UnitCategory | None = Field(None)

    # Read-only fields
    verified: bool | None = Field(default=False, exclude=True, frozen=True)
