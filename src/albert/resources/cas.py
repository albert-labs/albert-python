from __future__ import annotations

from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


class CasCategory(str, Enum):
    USER = "User"
    VERISK = "Verisk"
    TSCA_PUBLIC = "TSCA - Public"
    TSCA_PRIVATE = "TSCA - Private"
    NOT_TSCA = "not TSCA"
    EXTERNAL = "CAS linked to External Database"
    UNKNOWN = "Unknown (Trade Secret)"
    CL_INVENTORY_UPLOAD = "CL_Inventory Upload"


class Hazard(BaseAlbertModel):
    """A single GHS hazard classification associated with a CAS substance.

    Hazards are read from the CAS record; a [`Cas`][albert.resources.cas.Cas] may carry a list of them.

    Attributes
    ----------
    sub_category : str, optional
        Hazard subcategory.
    h_code : str, optional
        GHS hazard statement code (e.g. an ``H``-code such as ``"H301"``).
    category : str or float, optional
        Hazard category.
    hazard_class : str, optional
        Hazard classification.
    h_code_text : str, optional
        Human-readable text for the hazard code.
    """

    sub_category: str | None = Field(None, alias="subCategory", description="Hazard subcategory")
    h_code: str | None = Field(None, alias="hCode", description="Hazard code")
    category: str | float | None = Field(None, description="Hazard category")
    hazard_class: str | None = Field(None, alias="class", description="Hazard classification")
    h_code_text: str | None = Field(None, alias="hCodeText", description="Hazard code text")


class Cas(BaseResource):
    """A CAS entry: a chemical substance identified by its CAS Registry Number.

    A ``Cas`` is Albert's dictionary record for a substance. Raw-material Inventory
    Items reference these entries to declare what they are made of, pairing each
    ``Cas`` with an amount (see [`CasAmount`][albert.resources.inventory.CasAmount]).
    Manage entries through
    [`CasCollection`][albert.collections.cas.CasCollection] (``client.cas``): most fields
    are populated by Albert, so you typically only build a ``Cas`` from a registry
    ``number`` when creating a new entry.

    Attributes
    ----------
    number : str
        The CAS Registry Number (e.g. ``"7727-37-9"``). Required.
    name : str, optional
        Name of the substance.
    description : str, optional
        Free-text description of the CAS. Updatable via
        [`update`][albert.collections.cas.CasCollection.update].
    notes : str, optional
        Free-text notes about the CAS. Updatable.
    category : CasCategory, optional
        The source/classification of the entry (e.g. user-created, TSCA listing).
        See [`CasCategory`][albert.resources.cas.CasCategory].
    smiles : str, optional
        SMILES structure notation for the substance. Updatable. Serialized as
        ``casSmiles``.
    inchi_key : str, optional
        InChIKey hash of the chemical structure.
    iupac_name : str, optional
        IUPAC systematic name.
    id : str, optional
        The Albert CAS ID (format ``CAS...``, e.g. ``"CAS1"``). Assigned by Albert
        on creation. Serialized as ``albertId``.
    hazards : list[Hazard], optional
        GHS hazard classifications for the substance. See [`Hazard`][albert.resources.cas.Hazard].
    wgk : str, optional
        German Water Hazard Class (Wassergefährdungsklasse) number.
    ec_number : str, optional
        European Community (EC) number. Serialized as ``ecListNo``.
    type : str, optional
        Internal classification-type reference for the CAS.
    classification_type : str, optional
        Classification type of the CAS.
    order : str, optional
        CAS order value.
    metadata : dict[str, MetadataItem]
        Custom metadata keyed by field. Updatable.

    !!! example
        ```python
        from albert.resources.cas import Cas
        # Build a CAS entry to register a new substance
        cas = Cas(number="7727-37-9")
        ```
    """

    number: str = Field(..., description="The CAS number.")
    name: str | None = Field(None, description="Name of the CAS.")
    description: str | None = Field(None, description="The description or name of the CAS.")
    notes: str | None = Field(None, description="Notes related to the CAS.")
    category: CasCategory | None = Field(None, description="The category of the CAS.")
    smiles: str | None = Field(None, alias="casSmiles", description="CAS SMILES notation.")
    inchi_key: str | None = Field(None, alias="inchiKey", description="InChIKey of the CAS.")
    iupac_name: str | None = Field(None, alias="iUpacName", description="IUPAC name of the CAS.")
    id: str | None = Field(None, alias="albertId", description="The AlbertID of the CAS.")
    hazards: list[Hazard] | None = Field(None, description="Hazards associated with the CAS.")
    wgk: str | None = Field(None, description="German Water Hazard Class (WGK) number.")
    ec_number: str | None = Field(
        None, alias="ecListNo", description="European Community (EC) number."
    )
    type: str | None = Field(None, description="Internal classification_type reference.")
    classification_type: str | None = Field(
        None, alias="classificationType", description="Classification type of the CAS."
    )
    order: str | None = Field(None, description="CAS order.")
    metadata: dict[str, MetadataItem] = Field(alias="Metadata", default_factory=dict)

    @classmethod
    def from_string(cls, *, number: str) -> Cas:
        """Build a [`Cas`][albert.resources.cas.Cas] from a bare registry number.

        Convenience constructor equivalent to ``Cas(number=number)``, for when you
        only have the registry number and want a ``Cas`` object to pass to
        [`CasCollection`][albert.collections.cas.CasCollection].

        Parameters
        ----------
        number : str
            The CAS Registry Number (e.g. ``"7727-37-9"``).

        Returns
        -------
        Cas
            A ``Cas`` with only ``number`` set.

        !!! example
            ```python
            from albert.resources.cas import Cas
            cas = Cas.from_string(number="7727-37-9")
            ```
        """
        return cls(number=number)
