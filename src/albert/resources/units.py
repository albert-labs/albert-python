from enum import Enum

from pydantic import Field

from albert.resources.base import BaseResource


class UnitCategory(str, Enum):
    """
    UnitCategory is an enumeration of possible unit categories.

    Attributes
    ----------
    LENGTH : str
        Represents length units.
    VOLUME : str
        Represents volume units.
    LIQUID_VOLUME : str
        Represents liquid volume units.
    ANGLES : str
        Represents angle units.
    TIME : str
        Represents time units.
    FREQUENCY : str
        Represents frequency units.
    MASS : str
        Represents mass units.
    CURRENT : str
        Represents electric current units.
    TEMPERATURE : str
        Represents temperature units.
    AMOUNT : str
        Represents amount of substance units.
    LUMINOSITY : str
        Represents luminous intensity units.
    FORCE : str
        Represents force units.
    ENERGY : str
        Represents energy units.
    POWER : str
        Represents power units.
    PRESSURE : str
        Represents pressure units.
    ELECTRICITY_AND_MAGNETISM : str
        Represents electricity and magnetism units.
    OTHER : str
        Represents other units.
    WEIGHT : str
        Represents weight units.
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
    """
    Unit is a Pydantic model representing a unit entity.

    Attributes
    ----------
    id : str | None
        The Albert ID of the unit. Set when the unit is retrieved from Albert.
    name : str
        The name of the unit.
    symbol : str | None
        The symbol of the unit.
    synonyms : List[str] | None
        The list of synonyms for the unit.
    category : UnitCategory
        The category of the unit.
    verified : bool | None
        Whether the unit is verified.
    status : Status | None
        The status of the unit. Allowed values are `active`, and `inactive`
    """

    id: str | None = Field(None, alias="albertId")
    name: str
    symbol: str | None = Field(None)
    synonyms: list[str] | None = Field(default_factory=list, alias="Synonyms")
    category: UnitCategory | None = Field(None)

    # Read-only fields
    verified: bool | None = Field(default=False, exclude=True, frozen=True)
