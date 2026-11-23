from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from albert.core.base import BaseAlbertModel


class DescriptorFamily(str, Enum):
    """Feature family a descriptor belongs to.

    A family is a way to ask for a group of descriptors by what they measure.
    ``fingerprints_ml`` is 2214 values per molecule; prefer one fingerprint by
    name. ``shape_3d`` embeds a 3D conformer, which is slower and can fail.
    """

    PHYSICOCHEMICAL = "physicochemical"
    COMPOSITION = "composition"
    FUNCTIONAL_GROUPS = "functional_groups"
    FINGERPRINTS_ML = "fingerprints_ml"
    SHAPE_3D = "shape_3d"


class NumericDescriptorValue(BaseAlbertModel):
    """One numeric descriptor result."""

    type: Literal["numeric"] = "numeric"
    """Value kind. Always ``numeric``."""

    value: float | None
    """The number, or null when the descriptor could not be calculated."""


class NumericListDescriptorValue(BaseAlbertModel):
    """A list of numeric descriptor results, such as a fingerprint."""

    type: Literal["numeric_list"] = "numeric_list"
    """Value kind. Always ``numeric_list``."""

    value: list[float | None]
    """One number per bit or component. An entry is null when it could not be calculated."""


class IntegerDescriptorValue(BaseAlbertModel):
    """One integer descriptor result."""

    type: Literal["integer"] = "integer"
    """Value kind. Always ``integer``."""

    value: int | None
    """The integer, or null when it could not be calculated."""


class IntegerListDescriptorValue(BaseAlbertModel):
    """A list of integer descriptor results."""

    type: Literal["integer_list"] = "integer_list"
    """Value kind. Always ``integer_list``."""

    value: list[int | None]
    """One integer per component. An entry is null when it could not be calculated."""


class BooleanDescriptorValue(BaseAlbertModel):
    """One boolean descriptor result."""

    type: Literal["boolean"] = "boolean"
    """Value kind. Always ``boolean``."""

    value: bool | None
    """The flag, or null when it could not be calculated."""


class StringDescriptorValue(BaseAlbertModel):
    """One string descriptor result."""

    type: Literal["string"] = "string"
    """Value kind. Always ``string``."""

    value: str | None
    """The text, or null when it could not be calculated."""


DescriptorNumber = Annotated[
    NumericDescriptorValue
    | NumericListDescriptorValue
    | IntegerDescriptorValue
    | IntegerListDescriptorValue
    | BooleanDescriptorValue
    | StringDescriptorValue,
    Field(discriminator="type"),
]


class DescriptorInfo(BaseAlbertModel):
    """Catalog entry for one molecular descriptor."""

    name: str
    """Registered descriptor name, used in ``calculate``."""

    dimension: int
    """Number of values this descriptor returns for one molecule."""

    default: bool
    """Whether this descriptor is in the default calculate set."""

    description: str | None
    """What the descriptor measures."""

    families: list[str] = Field(default_factory=list)
    """Feature families this descriptor belongs to. Pass one to ``calculate``."""

    unit: str | None = Field(default=None)
    """Unit shared by every value this descriptor returns."""

    requires_3d: bool = Field(default=False)
    """True when the descriptor embeds a 3D conformer. That is slower and can return null."""


class DescriptorValue(BaseAlbertModel):
    """One calculated descriptor for one molecule."""

    name: str
    """Registered descriptor name."""

    value: DescriptorNumber
    """The calculated value. A null scalar or list component means it could not be calculated."""

    unit: str | None = Field(default=None)
    """Unit of ``value``, the same as the catalog entry for this descriptor."""


class MoleculeDescriptors(BaseAlbertModel):
    """Descriptor values for one molecule."""

    smiles: str
    """The submitted SMILES for this result."""

    descriptors: list[DescriptorValue]
    """One entry per calculated descriptor."""


class DescriptorInfoList(BaseAlbertModel):
    """Catalog response."""

    items: list[DescriptorInfo]
    """The descriptors in the catalog."""


class CalculateDescriptorsResponse(BaseAlbertModel):
    """Calculate response."""

    results: list[MoleculeDescriptors]
    """One entry per input SMILES."""
