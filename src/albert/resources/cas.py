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
    """Represents a chemical hazard."""

    sub_category: str | None = Field(None, alias="subCategory", description="Hazard subcategory")
    h_code: str | None = Field(None, alias="hCode", description="Hazard code")
    category: str | float | None = Field(None, description="Hazard category")
    hazard_class: str | None = Field(None, alias="class", description="Hazard classification")
    h_code_text: str | None = Field(None, alias="hCodeText", description="Hazard code text")


class Cas(BaseResource):
    """Represents a CAS entity."""

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
    type: str | None = Field(None, description="Type of the CAS.")
    classification_type: str | None = Field(
        None, alias="classificationType", description="Classification type of the CAS."
    )
    order: str | None = Field(None, description="CAS order.")
    metadata: dict[str, MetadataItem] = Field(alias="Metadata", default_factory=dict)

    @classmethod
    def from_string(cls, *, number: str) -> "Cas":
        """
        Creates a Cas object from a string.

        Parameters
        ----------
        number : str
            The CAS number.

        Returns
        -------
        Cas
            The Cas object created from the string.
        """
        return cls(number=number)
