from typing import Any, Literal

from pydantic import ConfigDict, Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.types import MetadataItem


class SubstanceV4SearchItem(BaseAlbertModel):
    """A lightweight substance record from a search result."""

    model_config = ConfigDict(extra="allow")

    substance_id: str | None = Field(None, alias="substanceId")
    """The unique substance identifier."""

    cas_id: str | None = Field(None, alias="casID")
    """The CAS number."""

    ec_list_no: str | None = Field(None, alias="ecListNo")
    """The EC list number."""

    name: str | None = None
    """The substance name."""

    hazards: list[dict] | None = None
    """Hazard classifications."""

    wgk: str | None = Field(None, alias="WGK")
    """Water hazard class (WGK)."""

    classification_type: str | None = Field(None, alias="classificationType")
    """The classification type (e.g. Harmonised C&L, Self Classified)."""


class SubstanceV4Info(BaseAlbertModel):
    """A full substance record."""

    model_config = ConfigDict(extra="allow")

    substance_id: str | None = Field(None, alias="substanceId")
    """The unique substance identifier."""

    cas_id: str | None = Field(None, alias="casID")
    """The CAS number."""

    ec_list_no: str | None = Field(None, alias="ecListNo")
    """The EC list number."""

    index_no: str | None = Field(None, alias="indexNo")
    """The index number."""

    name: list[dict] | None = None
    """The substance name in one or more languages."""

    hazards: list[dict] | None = None
    """Hazard classifications."""

    specific_concentration_limit: list[dict] | None = Field(
        None, alias="specificConcentrationLimit"
    )
    """Specific concentration limits."""

    oels: bool | None = None
    """Whether occupational exposure limits exist."""

    exposure_controls_acgih: list[dict] | None = Field(None, alias="exposureControlsACGIH")
    """ACGIH exposure controls."""

    exposure_controls_osha: list[dict] | None = Field(None, alias="exposureControlsOSHA")
    """OSHA exposure controls."""

    exposure_controls_aiha: list[dict] | None = Field(None, alias="exposureControlsAIHA")
    """AIHA exposure controls."""

    exposure_controls_niosh: list[dict] | None = Field(None, alias="exposureControlsNIOSH")
    """NIOSH exposure controls."""

    lethal_dose_and_concentrations: list[dict] | None = Field(
        None, alias="lethalDoseAndConcentrations"
    )
    """Lethal dose and concentration data."""

    inhalation_acute_toxicity: float | None = Field(None, alias="inhalationAcuteToxicity")
    """Inhalation acute toxicity value."""

    dermal_acute_toxicity: float | None = Field(None, alias="dermalAcuteToxicity")
    """Dermal acute toxicity value."""

    oral_acute_toxicity: float | None = Field(None, alias="oralAcuteToxicity")
    """Oral acute toxicity value."""

    health_effects: str | None = Field(None, alias="healthEffects")
    """Health effects description."""

    ntp_carcinogen: str | None = Field(None, alias="ntpCarcinogen")
    """NTP carcinogen classification."""

    iarc_carcinogen: str | None = Field(None, alias="iarcCarcinogen")
    """IARC carcinogen classification."""

    osha_carcinogen: bool | None = Field(None, alias="oshaCarcinogen")
    """OSHA carcinogen flag."""

    classification_type: str | None = Field(None, alias="classificationType")
    """The classification type."""

    classification: str | None = None
    """The classification value."""

    reach_registration_no: str | None = Field(None, alias="reachRegistrationNo")
    """REACH registration number."""

    source: str | None = None
    """Data source."""

    is_cas: bool = Field(default=True, alias="isCas")
    """Whether the substance is a known regulatory CAS record. ``False`` indicates an auto-created or trade-secret placeholder."""

    notes: str | None = None
    """Free-text notes for the substance."""

    description: str | None = None
    """A description of the substance."""

    cas_smiles: str | None = Field(None, alias="casSmiles")
    """The SMILES string for the substance."""

    inchi_key: str | None = Field(None, alias="inchiKey")
    """The InChI key for the substance."""

    iupac_name: str | None = Field(None, alias="iUpacName")
    """The IUPAC name for the substance."""

    cactus_status: str | None = Field(None, alias="cactusStatus")
    """The Cactus status for the substance."""

    metadata: dict[str, Any] | None = None
    """Tenant custom metadata. Scalar fields are plain strings or numbers. List-type fields return a list of ``MetadataItem`` objects with ``name`` and ``id``."""

    acute_dermal_tox_info: list[dict] | None = Field(None, alias="acuteDermalToxInfo")
    """Acute dermal toxicity information."""

    acute_inhalation_tox_info: list[dict] | None = Field(None, alias="acuteInhalationToxInfo")
    """Acute inhalation toxicity information."""

    acute_oral_tox_info: list[dict] | None = Field(None, alias="acuteOralToxInfo")
    """Acute oral toxicity information."""

    acute_tox_info: list[dict] | None = Field(None, alias="acuteToxInfo")
    """General acute toxicity information."""

    chronic_tox_info: list[dict] | None = Field(None, alias="chronicToxInfo")
    """Chronic toxicity information."""

    aspiration_tox_info: list[dict] | None = Field(None, alias="aspirationToxInfo")
    """Aspiration toxicity information."""

    neuro_tox_info: list[dict] | None = Field(None, alias="neuroToxInfo")
    """Neurotoxicity information."""

    reproductive_tox_info: list[dict] | None = Field(None, alias="reproductiveToxInfo")
    """Reproductive toxicity information."""

    carcinogen_info: list[dict] | None = Field(None, alias="carcinogenInfo")
    """Carcinogenicity information."""

    germ_cell_mutagen_info: list[dict] | None = Field(None, alias="germCellMutagenInfo")
    """Germ cell mutagenicity information."""

    skin_corrosion_info: list[dict] | None = Field(None, alias="skinCorrosionInfo")
    """Skin corrosion information."""

    serious_eye_damage_info: list[dict] | None = Field(None, alias="seriousEyeDamageInfo")
    """Serious eye damage information."""

    respiratory_skin_sens_info: list[dict] | None = Field(None, alias="respiratorySkinSensInfo")
    """Respiratory and skin sensitization information."""

    stot_info: list[dict] | None = Field(None, alias="stotInfo")
    """Specific target organ toxicity information."""

    stot_affected_organs: str | None = Field(None, alias="stotAffectedOrgans")
    """Organs affected by specific target organ toxicity."""

    stot_route_of_exposure: str | None = Field(None, alias="stotRouteOfExposure")
    """Route of exposure for specific target organ toxicity."""

    boilingpoint_info: list[dict] | None = Field(None, alias="boilingpointInfo")
    """Boiling point information."""

    flashpoint_info: list[dict] | None = Field(None, alias="flashpointInfo")
    """Flash point information."""

    molecular_weight: list[dict] | None = Field(None, alias="molecularWeight")
    """Molecular weight information."""

    bio_accumulative_info: list[dict] | None = Field(None, alias="bioAccumulativeInfo")
    """Bioaccumulation information."""

    degradability_info: list[dict] | None = Field(None, alias="degradabilityInfo")
    """Degradability information."""

    soil_mobility_info: list[dict] | None = Field(None, alias="soilMobilityInfo")
    """Soil mobility information."""

    peroxide_function_groups: int | None = Field(None, alias="peroxideFunctionGroups")
    """Number of peroxide function groups."""

    structures: list[dict] | None = None
    """Chemical structure representations."""

    oel_info: list[dict] | None = Field(None, alias="oelInfo")
    """Occupational exposure limit information."""

    bei_info: list[dict] | None = Field(None, alias="beiInfo")
    """Biological exposure index information."""

    dnel_info: list[dict] | None = Field(None, alias="dnelInfo")
    """Derived no-effect level information."""

    m_factor: int | None = Field(None, alias="mFactor")
    """Acute toxicity M-factor."""

    m_factor_chronic: int | None = Field(None, alias="mFactorChronic")
    """Chronic toxicity M-factor."""

    specific_conc_eu: list[dict] | None = Field(None, alias="specificConcEU")
    """EU-specific concentration limits."""

    specific_conc_source: str | None = Field(None, alias="specificConcSource")
    """Source of specific concentration limit information."""

    aicis_notified: bool | None = Field(None, alias="aicisNotified")
    """Whether the substance is AICIS notified."""

    iecsc_notified: bool | None = Field(None, alias="iecscNotified")
    """Whether the substance is IECSC notified."""

    jpencs_notified: bool | None = Field(None, alias="jpencsNotified")
    """Whether the substance is JPENCS notified."""

    jpishl_notified: bool | None = Field(None, alias="jpishlNotified")
    """Whether the substance is JPISHL notified."""

    koecl_notified: bool | None = Field(None, alias="koeclNotified")
    """Whether the substance is KOECL notified."""

    nzioc_notified: bool | None = Field(None, alias="nziocNotified")
    """Whether the substance is NZIOC notified."""

    piccs_notified: bool | None = Field(None, alias="piccsNotified")
    """Whether the substance is PICCS notified."""

    tcsi_notified: bool | None = Field(None, alias="tcsiNotified")
    """Whether the substance is TCSI notified."""

    vinic_notified: bool | None = Field(None, alias="vinicNotified")
    """Whether the substance is VINIC notified."""

    encs_notified_list: dict[str, Any] | None = Field(None, alias="encsNotifiedList")
    """ENCS notification details."""

    ishl_notified_list: dict[str, Any] | None = Field(None, alias="ishlNotifiedList")
    """ISHL notification details."""

    ec_notified: str | None = Field(None, alias="ecNotified")
    """EC notification status."""

    canada_inventory_status: str | None = Field(None, alias="canadaInventoryStatus")
    """Canadian inventory status."""

    trade_secret: bool | None = Field(None, alias="tradeSecret")
    """Whether the substance is a trade secret."""

    eu_annex14_substances_list: bool | None = Field(None, alias="euAnnex14SubstancesList")
    """Whether the substance is on the EU Annex XIV list."""

    eu_annex17_restrictions_list: bool | None = Field(None, alias="euAnnex17RestrictionsList")
    """Whether the substance is on the EU Annex XVII restrictions list."""

    eu_annex17_substances_list: bool | None = Field(None, alias="euAnnex17SubstancesList")
    """Whether the substance is on the EU Annex XVII substances list."""

    eu_candidate_list: bool | None = Field(None, alias="euCandidateList")
    """Whether the substance is on the EU SVHC candidate list."""

    eu_dang_chem_annex1_part1_list: bool | None = Field(None, alias="euDangChemAnnex1Part1List")
    """Whether the substance is on the EU dangerous chemicals Annex 1 Part 1 list."""

    eu_dang_chem_annex1_part2_list: bool | None = Field(None, alias="euDangChemAnnex1Part2List")
    """Whether the substance is on the EU dangerous chemicals Annex 1 Part 2 list."""

    eu_dang_chem_annex1_part3_list: bool | None = Field(None, alias="euDangChemAnnex1Part3List")
    """Whether the substance is on the EU dangerous chemicals Annex 1 Part 3 list."""

    eu_dang_chem_annex5_list: bool | None = Field(None, alias="euDangChemAnnex5List")
    """Whether the substance is on the EU dangerous chemicals Annex 5 list."""

    eu_directive_ec_list: bool | None = Field(None, alias="euDirectiveEcList")
    """Whether the substance is on the EU directive EC list."""

    eu_explosive_precursors_annex1_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex1List"
    )
    """Whether the substance is on the EU explosive precursors Annex 1 list."""

    eu_explosive_precursors_annex2_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex2List"
    )
    """Whether the substance is on the EU explosive precursors Annex 2 list."""

    eu_ozone_depletion_list: bool | None = Field(None, alias="euOzoneDepletionList")
    """Whether the substance is on the EU ozone depletion list."""

    eu_pollutant_annex2_list: bool | None = Field(None, alias="euPollutantAnnex2List")
    """Whether the substance is on the EU pollutant Annex 2 list."""

    eu_pop_list: bool | None = Field(None, alias="euPopList")
    """Whether the substance is on the EU POP list."""

    caa_cfr40: bool | None = Field(None, alias="caaCFR40")
    """Whether the substance is listed under CAA CFR 40."""

    caa_hpa: bool | None = Field(None, alias="caaHPA")
    """Whether the substance is listed under CAA HPA."""

    massachusetts_rtk: bool | None = Field(None, alias="massachusettsRTK")
    """Whether the substance is on the Massachusetts RTK list."""

    new_jersey_rtk: bool | None = Field(None, alias="newJerseyRTK")
    """Whether the substance is on the New Jersey RTK list."""

    new_york_rtk: bool | None = Field(None, alias="newYorkRTK")
    """Whether the substance is on the New York RTK list."""

    pennsylvania_rtk: bool | None = Field(None, alias="pennsylvaniaRTK")
    """Whether the substance is on the Pennsylvania RTK list."""

    rhode_island_rtk: bool | None = Field(None, alias="rhodeIslandRTK")
    """Whether the substance is on the Rhode Island RTK list."""

    sdwa: bool | None = None
    """Whether the substance is listed under the SDWA."""

    tsca8b: bool | None = Field(None, alias="tsca8B")
    """Whether the substance is listed under TSCA 8(b)."""

    pcr_regulated: bool | None = Field(None, alias="pcrRegulated")
    """Whether the substance is PCR regulated."""

    pdscl: str | None = None
    """PDSCL classification."""

    prtr: str | None = None
    """PRTR classification."""

    page_number: int | None = Field(None, alias="pageNumber")
    """Reference page number."""

    cn_csdc_regulations: bool | None = Field(None, alias="cnCSDCRegulations")
    """Whether the substance is subject to CN CSDC regulations."""

    cn_pcod_list: bool | None = Field(None, alias="cnPCODList")
    """Whether the substance is on the CN PCOD list."""

    cn_priority_list: bool | None = Field(None, alias="cnPriorityList")
    """Whether the substance is on the CN priority list."""

    tw_ghs_clas_list: bool | None = Field(None, alias="twGHSClasList")
    """Whether the substance is on the Taiwan GHS classification list."""

    tw_handle_priority_chem: bool | None = Field(None, alias="twHandlePriorityChem")
    """Whether the substance is a Taiwan priority chemical."""

    tw_handle_toxic_chem: bool | None = Field(None, alias="twHandleToxicChem")
    """Whether the substance is a Taiwan toxic chemical."""

    tw_ind_waste_standards: bool | None = Field(None, alias="twIndWasteStandards")
    """Whether the substance is subject to Taiwan industrial waste standards."""

    basel_conv_list: bool | None = Field(None, alias="baselConvList")
    """Whether the substance is on the Basel Convention list."""

    rotterdam_conv_list: bool | None = Field(None, alias="rotterdamConvList")
    """Whether the substance is on the Rotterdam Convention list."""

    stockholm_conv_list: bool | None = Field(None, alias="stockholmConvList")
    """Whether the substance is on the Stockholm Convention list."""

    kyoto_protocol: bool | None = Field(None, alias="kyotoProtocol")
    """Whether the substance is subject to the Kyoto Protocol."""

    montreal_protocol: bool | None = Field(None, alias="montrealProtocol")
    """Whether the substance is subject to the Montreal Protocol."""

    green_gas_list: bool | None = Field(None, alias="greenGasList")
    """Whether the substance is on the green gas list."""

    export_control_list_phrases: bool | None = Field(None, alias="exportControlListPhrases")
    """Whether the substance has export control list phrases."""

    cdsa_list: bool | None = Field(None, alias="cdsaList")
    """Whether the substance is on the CDSA list."""

    chemical_category: list[str] | None = Field(None, alias="chemicalCategory")
    """Chemical categories for the substance."""

    custom_phrases: list[dict] | None = Field(None, alias="customPhrases")
    """Custom phrases for the substance."""

    substance_phrases: list[dict] | None = Field(None, alias="substancePhrases")
    """Substance phrases."""

    sustainability_status_lbc: str | None = Field(None, alias="sustainabilityStatusLBC")
    """Living Building Challenge sustainability status."""

    approved_legal_entities: Any | None = Field(None, alias="approvedLegalEntities")
    """Approved legal entities for the substance."""

    pictograms: list[dict] | None = None
    """GHS hazard pictograms."""


class SubstanceV4Response(BaseAlbertModel):
    """A collection of substances with any associated retrieval errors."""

    substances: list[SubstanceV4Info]
    """The retrieved substances."""

    substance_errors: list[dict] | None = Field(None, alias="substanceErrors")
    """Errors for any substances that could not be retrieved, if any."""


class SubstanceV4Identifier(BaseAlbertModel):
    """An identifier entry for creating a substance."""

    attribute_name: Literal["casID", "ecListNo", "ts"] = Field(..., alias="attributeName")
    """The identifier type. One of ``casID``, ``ecListNo``, ``ts``."""

    value: str
    """The identifier value."""


class SubstanceV4Attribute(BaseAlbertModel):
    """An attribute entry for creating a substance."""

    attribute_name: str = Field(..., alias="attributeName")
    """The attribute name (e.g. ``hazards``, ``name``). Note that this name must exactly match one of the allowed Substance Attribute Names, and in the future will reference an attribute ID"""

    data: Any
    """The attribute data."""

    region: str | None = None
    """The region the attribute applies to, if any."""


class SubstanceV4Create(BaseAlbertModel):
    """Defines a new substance to create."""

    identifiers: list[SubstanceV4Identifier]
    """At least one identifier (casID, ecListNo, or ts)."""

    attributes: list[SubstanceV4Attribute]
    """Attribute data to associate with the substance."""

    substance_id: str | None = Field(None, alias="substanceId")
    """Optional explicit substance ID."""

    is_global_record: bool = Field(True, alias="isGlobalRecord")
    """Whether to create as a global record. Defaults to ``True``."""

    category: str | None = None
    """Substance category (e.g. ``User``, ``Verisk``, ``TSCA - Public``)."""

    notes: str | None = None
    """Free-text notes for the substance."""

    description: str | None = None
    """A description of the substance."""

    cas_smiles: str | None = Field(None, alias="casSmiles")
    """The SMILES string for the substance."""

    inchi_key: str | None = Field(None, alias="inchiKey")
    """The InChI key for the substance."""

    iupac_name: str | None = Field(None, alias="iUpacName")
    """The IUPAC name for the substance."""

    cactus_status: str | None = Field(None, alias="cactusStatus")
    """The Cactus status for the substance."""

    metadata: dict[str, MetadataItem] | None = Field(None, alias="Metadata")
    """Custom tenant metadata. Scalar fields take a plain string. Single-select list fields take a bare list ID string (e.g. ``"LST1253"``). Multi-select List-type fields take an ``EntityLink`` or ``list[EntityLink]``."""


class SubstanceV4CreateResult(BaseAlbertModel):
    """Result of a substance creation request."""

    created_items: list[SubstanceV4Info] = Field(default_factory=list, alias="createdItems")
    """Successfully created substances."""

    failed_items: list[dict] = Field(default_factory=list, alias="failedItems")
    """Items that failed to create, with error details."""

    existing_items: list[dict] = Field(default_factory=list, alias="existingItems")
    """Items that already existed."""


class SubstanceV4Metadata(BaseAlbertModel):
    """Metadata fields that can be updated on a substance."""

    notes: str | None = None
    """Free-text notes for the substance."""

    description: str | None = None
    """A description of the substance."""

    cas_smiles: str | None = Field(None, alias="casSmiles")
    """The SMILES string for the substance."""

    inchi_key: str | None = Field(None, alias="inchiKey")
    """The InChI key for the substance."""

    iupac_name: str | None = Field(None, alias="iUpacName")
    """The IUPAC name for the substance."""

    cactus_status: str | None = Field(None, alias="cactusStatus")
    """The Cactus status for the substance."""

    metadata: dict[str, MetadataItem] | None = None
    """Custom tenant metadata. Scalar fields take a plain string. Single-select list fields take a bare list ID string (e.g. ``"LST1253"``). Multi-select list fields take a list of ``MetadataItem`` objects with ``id`` and ``value``."""
