from enum import Enum

from pydantic import Field

from albert.resources.base import BaseResource


class CasCategory(str, Enum):
    USER = "User"
    VERISK = "Verisk"
    TSCA_PUBLIC = "TSCA - Public"
    TSCA_PRIVATE = "TSCA - Private"
    NOT_TSCA = "not TSCA"
    EXTERNAL = "CAS linked to External Database"
    UNKNOWN = "Unknown (Trade Secret)"
    CL_INVENTORY_UPLOAD = "CL_Inventory Upload"


class Hazard(BaseResource):
    sub_category: str = Field(None, alias="subCategory")
    h_code: str = Field(None, alias="hCode")
    category: str | float | None = None
    hazard_class: str | None = Field(None, alias="class")
    h_code_text: str = Field(None, alias="hCodeText")


class Cas(BaseResource):
    """
    Cas is a Pydantic model representing a CAS entity.

    Attributes
    ----------
    number : str
        The CAS number.
    name : str | None
        Name of the CAS.
    description : str | None
        The description or name of the CAS.
    notes : str | None
        Notes of the CAS.
    category : CasCategory | None
        The category of the CAS.
    smiles : str | None
        CAS SMILES notation.
    inchi_key : str | None
        InChIKey of the CAS.
    iupac_name : str | None
        IUPAC name of the CAS.
    id : str | None
        The AlbertID of the CAS.
    hazards : List[Hazard] | None
        Hazards associated with the CAS.
    wgk : str | None
        German Water Hazard Class (WGK) number.
    ec_number : str | None
        European Community (EC) number.
    type : str | None
        Type of the CAS.
    classificationType : str | None
        Classification type of the CAS.
    order : str | None
        CAS order.
    """

    number: str
    name: str | None = None
    description: str | None = None
    notes: str | None = None
    category: CasCategory | None = None  # To better define in docstrings
    smiles: str | None = Field(None, alias="casSmiles")
    inchi_key: str | None = Field(None, alias="inchiKey")
    iupac_name: str | None = Field(None, alias="iUpacName")
    id: str | None = Field(None, alias="albertId")
    hazards: list[Hazard] | None = None
    wgk: str | None = None
    ec_number: str | None = Field(None, alias="ecListNo")
    type: str | None = None
    classification_type: str | None = Field(None, alias="classificationType")
    order: str | None = None

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
