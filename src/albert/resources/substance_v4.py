from typing import Any, Literal

from pydantic import ConfigDict, Field

from albert.core.base import BaseAlbertModel


class SubstanceV4SearchItem(BaseAlbertModel):
    """A lightweight substance record from a search result.

    Attributes
    ----------
    substance_id : str | None
        The unique substance identifier.
    cas_id : str | None
        The CAS number.
    ec_list_no : str | None
        The EC list number.
    name : str | None
        The substance name.
    hazards : list[dict] | None
        Hazard classifications.
    wgk : str | None
        Water hazard class (WGK).
    classification_type : str | None
        The classification type (e.g. Harmonised C&L, Self Classified).
    """

    substance_id: str | None = Field(None, alias="substanceId")
    cas_id: str | None = Field(None, alias="casID")
    ec_list_no: str | None = Field(None, alias="ecListNo")
    name: str | None = None
    hazards: list[dict] | None = None
    wgk: str | None = Field(None, alias="WGK")
    classification_type: str | None = Field(None, alias="classificationType")


class SubstanceV4Info(BaseAlbertModel):
    """A full substance record.

    Attributes
    ----------
    substance_id : str | None
        The unique substance identifier.
    cas_id : str | None
        The CAS number.
    ec_list_no : str | None
        The EC list number.
    index_no : str | None
        The index number.
    name : list[dict] | None
        The substance name in one or more languages.
    hazards : list[dict] | None
        Hazard classifications.
    specific_concentration_limit : list[dict] | None
        Specific concentration limits.
    oels : bool | None
        Whether occupational exposure limits exist.
    exposure_controls_acgih : list[dict] | None
        ACGIH exposure controls.
    exposure_controls_osha : list[dict] | None
        OSHA exposure controls.
    exposure_controls_aiha : list[dict] | None
        AIHA exposure controls.
    exposure_controls_niosh : list[dict] | None
        NIOSH exposure controls.
    lethal_dose_and_concentrations : list[dict] | None
        Lethal dose and concentration data.
    inhalation_acute_toxicity : float | None
        Inhalation acute toxicity value.
    dermal_acute_toxicity : float | None
        Dermal acute toxicity value.
    oral_acute_toxicity : float | None
        Oral acute toxicity value.
    health_effects : str | None
        Health effects description.
    ntp_carcinogen : str | None
        NTP carcinogen classification.
    iarc_carcinogen : str | None
        IARC carcinogen classification.
    osha_carcinogen : bool | None
        OSHA carcinogen flag.
    classification_type : str | None
        The classification type.
    classification : str | None
        The classification value.
    reach_registration_no : str | None
        REACH registration number.
    source : str | None
        Data source.
    """

    model_config = ConfigDict(extra="allow")

    substance_id: str | None = Field(None, alias="substanceId")
    cas_id: str | None = Field(None, alias="casID")
    ec_list_no: str | None = Field(None, alias="ecListNo")
    index_no: str | None = Field(None, alias="indexNo")
    name: list[dict] | None = None
    hazards: list[dict] | None = None
    specific_concentration_limit: list[dict] | None = Field(
        None, alias="specificConcentrationLimit"
    )
    oels: bool | None = None
    exposure_controls_acgih: list[dict] | None = Field(None, alias="exposureControlsACGIH")
    exposure_controls_osha: list[dict] | None = Field(None, alias="exposureControlsOSHA")
    exposure_controls_aiha: list[dict] | None = Field(None, alias="exposureControlsAIHA")
    exposure_controls_niosh: list[dict] | None = Field(None, alias="exposureControlsNIOSH")
    lethal_dose_and_concentrations: list[dict] | None = Field(
        None, alias="lethalDoseAndConcentrations"
    )
    inhalation_acute_toxicity: float | None = Field(None, alias="inhalationAcuteToxicity")
    dermal_acute_toxicity: float | None = Field(None, alias="dermalAcuteToxicity")
    oral_acute_toxicity: float | None = Field(None, alias="oralAcuteToxicity")
    health_effects: str | None = Field(None, alias="healthEffects")
    ntp_carcinogen: str | None = Field(None, alias="ntpCarcinogen")
    iarc_carcinogen: str | None = Field(None, alias="iarcCarcinogen")
    osha_carcinogen: bool | None = Field(None, alias="oshaCarcinogen")
    classification_type: str | None = Field(None, alias="classificationType")
    classification: str | None = None
    reach_registration_no: str | None = Field(None, alias="reachRegistrationNo")
    source: str | None = None


class SubstanceV4Response(BaseAlbertModel):
    """A collection of substances with any associated retrieval errors.

    Attributes
    ----------
    substances : list[SubstanceV4Info]
        The retrieved substances.
    substance_errors : list[dict] | None
        Errors for any substances that could not be retrieved, if any.
    """

    substances: list[SubstanceV4Info]
    substance_errors: list[dict] | None = Field(None, alias="substanceErrors")


class SubstanceV4Identifier(BaseAlbertModel):
    """An identifier entry for creating a substance.

    Attributes
    ----------
    attribute_name : str
        The identifier type. One of ``casID``, ``ecListNo``, ``ts``.
    value : str
        The identifier value.
    """

    attribute_name: Literal["casID", "ecListNo", "ts"] = Field(..., alias="attributeName")
    value: str


class SubstanceV4Attribute(BaseAlbertModel):
    """An attribute entry for creating a substance.

    Attributes
    ----------
    attribute_name : str
        The attribute name (e.g. ``hazards``, ``name``).
    data : Any
        The attribute data.
    region : str | None
        The region the attribute applies to, if any.
    """

    attribute_name: str = Field(..., alias="attributeName")
    data: Any
    region: str | None = None


class SubstanceV4Create(BaseAlbertModel):
    """Defines a new substance to create.

    Attributes
    ----------
    identifiers : list[SubstanceV4Identifier]
        At least one identifier (casID, ecListNo, or ts).
    attributes : list[SubstanceV4Attribute]
        Attribute data to associate with the substance.
    substance_id : str | None
        Optional explicit substance ID.
    is_global_record : bool
        Whether to create as a global record. Defaults to ``True``.
    category : str | None
        Substance category (e.g. ``User``, ``Verisk``, ``TSCA - Public``).
    metadata : dict | None
        Custom metadata key-value pairs for this substance.
    """

    identifiers: list[SubstanceV4Identifier]
    attributes: list[SubstanceV4Attribute]
    substance_id: str | None = Field(None, alias="substanceId")
    is_global_record: bool = Field(True, alias="isGlobalRecord")
    category: str | None = None
    metadata: dict | None = Field(None, alias="Metadata")


class SubstanceV4CreateResult(BaseAlbertModel):
    """Result of a substance creation request.

    Attributes
    ----------
    created_items : list[SubstanceV4Info]
        Successfully created substances.
    failed_items : list[dict]
        Items that failed to create, with error details.
    existing_items : list[dict]
        Items that already existed.
    """

    created_items: list[SubstanceV4Info] = Field(default_factory=list, alias="createdItems")
    failed_items: list[dict] = Field(default_factory=list, alias="failedItems")
    existing_items: list[dict] = Field(default_factory=list, alias="existingItems")


class SubstanceV4Metadata(BaseAlbertModel):
    """Metadata fields that can be updated on a substance.

    Attributes
    ----------
    notes : str | None
        Free-text notes for the substance.
    description : str | None
        A description of the substance.
    cas_smiles : str | None
        The SMILES string for the substance.
    metadata : dict[str, Any] | None
        Custom metadata key-value pairs configured for the tenant.
    """

    notes: str | None = None
    description: str | None = None
    cas_smiles: str | None = Field(None, alias="casSmiles")
    metadata: dict[str, Any] | None = None
