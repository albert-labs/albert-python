from enum import Enum
from typing import Any

from pydantic import ConfigDict, Field

from albert.core.base import BaseAlbertModel


class StructureField(str, Enum):
    """A structure attribute that can be requested when looking up structures.

    Pass members (or their string values) as ``required_fields`` on
    [`get_by_ids`][albert.collections.structures.StructureCollection.get_by_ids] to
    narrow which attributes each returned [`Structure`][albert.resources.structures.Structure]
    carries.
    """

    ID = "id"
    COMMON_NAME = "commonName"
    INCHI = "inchi"
    INCHI_KEY = "inchiKey"
    IUPAC_NAMES = "iupacNames"
    SMILES = "smiles"
    SOURCE = "source"
    FORMULA = "formula"
    DATA = "data"
    IMAGE = "image"
    PROPERTIES = "properties"
    DESCRIPTORS = "descriptors"
    PRIMARY_NAME = "primaryName"
    PUBCHEM_CID = "pubchemCid"


class StructureAttributeValue(BaseAlbertModel):
    """A measured structure property value enriched with unit metadata.

    Structure lookups merge measured property values (for example molecular weight
    or density) onto each structure. Each value carries the attribute it belongs
    to and, when known, the unit it is expressed in.
    """

    attribute_id: str | None = Field(default=None, alias="atrId")
    """ID of the attribute this value belongs to (format ``ATR...``)."""

    value: str | float | None = None
    """The measured value, numeric or textual."""

    unit_id: str | None = Field(default=None, alias="unitId")
    """ID of the unit the value is expressed in (format ``UNI...``)."""

    unit_name: str | None = Field(default=None, alias="unitName")
    """Human-readable name of the unit (e.g. ``"Gram Per Mole"``)."""


class Structure(BaseAlbertModel):
    """A chemical structure (a chemical draw block) in the Albert platform.

    A structure holds the identifiers and names of a chemical (SMILES, InChI,
    formula, common names) along with measured property values such as molecular
    weight. Structures are looked up by ID with
    [`StructureCollection`][albert.collections.structures.StructureCollection].

    Which attributes are populated depends on the ``required_fields`` given at
    lookup time; fields that were not requested are ``None``. Measured property
    values (for example ``molecular_weight``) can be present even when not
    requested. Property values beyond the declared ones are kept as extra fields
    rather than dropped.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.structures import StructureField

        client = Albert()
        structures = client.structures.get_by_ids(
            structure_ids=["STT1f139757-997e-62b0-863b-4cbed10437c7"],
            required_fields=[StructureField.SMILES],
        )
        structures[0].smiles
        # 'O'
        ```
    """

    # Measured property values are merged onto each structure by name, and the set
    # of names grows over time, so undeclared keys are kept on the instance.
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    """The structure ID (``STT``-prefixed). Present only when requested via ``required_fields``."""

    smiles: str | None = None
    """The SMILES string of the structure."""

    inchi: str | None = None
    """The International Chemical Identifier (InChI) string."""

    inchi_key: str | None = Field(default=None, alias="inchiKey")
    """The hashed InChIKey of the structure."""

    iupac_names: str | None = Field(default=None, alias="iupacNames")
    """IUPAC name text of the structure."""

    formula: str | None = None
    """The molecular formula of the structure."""

    common_name: list[str] | None = Field(default=None, alias="commonName")
    """Common names the structure is known by."""

    primary_name: str | None = Field(default=None, alias="primaryName")
    """The primary display name of the structure."""

    pubchem_cid: int | None = Field(default=None, alias="pubchemCid")
    """The PubChem compound identifier, when the structure is linked to PubChem."""

    source: str | None = None
    """The source the structure was imported from."""

    image: str | None = None
    """URL of a rendered image of the structure."""

    data: dict[str, Any] | None = None
    """Raw structure data (e.g. the draw block contents)."""

    properties: dict[str, Any] | None = None
    """Patched physical/chemical properties of the structure."""

    descriptors: dict[str, Any] | None = None
    """Computed structure descriptors."""

    density: StructureAttributeValue | None = None
    """Measured density, when available."""

    molecular_weight: StructureAttributeValue | None = Field(default=None, alias="molecularWeight")
    """Measured molecular weight, when available."""

    average_molecular_weight: StructureAttributeValue | None = Field(
        default=None, alias="averageMolecularWeight"
    )
    """Measured average molecular weight, when available."""
