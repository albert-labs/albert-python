from typing import Any, Literal

from pydantic import Field

from albert.core.base import BaseAlbertModel


class ToxicityInfo(BaseAlbertModel):
    """
    ToxicityInfo is a Pydantic model representing toxicity information."""

    result: str | None = None
    """The result of the toxicity test."""
    roe: str | None = None
    """The reference exposure level."""
    unit: str | None = None
    """The unit of the toxicity test."""
    method: str | None = None
    """The method of the toxicity test."""
    value: float | None = None
    """The value of the toxicity test."""
    species: str | None = None
    """The species of the toxicity test."""
    sex: str | None = None
    """The sex of the toxicity test."""
    exposure_time: str | None = Field(None, alias="exposureTime")
    """The exposure time of the toxicity test."""
    type: str | None = None
    """The type of the toxicity test."""
    value_type: str | None = Field(None, alias="valueType")
    """The value type of the toxicity test."""
    temperature: str | None = None
    """The temperature of the toxicity test."""


class BioAccumulativeInfo(BaseAlbertModel):
    """
    BioAccumulativeInfo is a Pydantic model representing bioaccumulative information."""

    bcf_value: str | None = Field(None, alias="bcfValue")
    """The bioaccumulative factor value."""
    temperature: str | None = None
    """The temperature of the bioaccumulative test."""
    exposure_time: str | None = Field(None, alias="exposureTime")
    """The exposure time of the bioaccumulative test."""
    method: str | None = None
    """The method of the bioaccumulative test."""
    species: str | None = None
    """The species of the bioaccumulative test."""


class BoilingPointValue(BaseAlbertModel):
    """
    BoilingPointValue is a Pydantic model representing a boiling point value."""

    min_value: str | None = Field(None, alias="minValue")
    """The minimum boiling point value."""
    max_value: str | None = Field(None, alias="maxValue")
    """The maximum boiling point value."""
    unit: str | None = None
    """The unit of the boiling point value."""


class BoilingPointSource(BaseAlbertModel):
    """
    BoilingPointSource is a Pydantic model representing a boiling point source."""

    note_code: str | None = Field(None, alias="noteCode")
    """The note code of the boiling point source."""
    note: str | None = None
    """The note of the boiling point source."""
    note_field: str | None = Field(None, alias="noteField")
    """The note field of the boiling point source."""


class BoilingPointInfo(BaseAlbertModel):
    """
    BoilingPointInfo is a Pydantic model representing boiling point information."""

    source: list[BoilingPointSource] | None = None
    """The source of the boiling point information."""
    values: list[BoilingPointValue] | None = None
    """The values of the boiling point information."""


class DegradabilityInfo(BaseAlbertModel):
    """
    DegradabilityInfo is a Pydantic model representing information about the degradability of a substance."""

    result: str | None = None
    """The result of the degradability test."""
    unit: str | None = None
    """The unit of measurement for the degradability test."""
    exposure_time: str | None = Field(None, alias="exposureTime")
    """The exposure time of the degradability test."""
    method: str | None = None
    """The method used for the degradability test."""
    test_type: str | None = Field(None, alias="testType")
    """The type of the degradability test."""
    degradability: str | None = None
    """The degradability classification."""
    value: str | None = None
    """The value of the degradability test."""


class DNELInfo(BaseAlbertModel):
    """
    DNELInfo is a Pydantic model representing the Derived No Effect Level (DNEL) information."""

    roe: str | None = None
    """The reference exposure level."""
    health_effect: str | None = Field(None, alias="healthEffect")
    """The health effect associated with the exposure."""
    exposure_time: str | None = Field(None, alias="exposureTime")
    """The exposure time for the DNEL."""
    application_area: str | None = Field(None, alias="applicationArea")
    """The area of application for the DNEL."""
    value: str | None = None
    """The DNEL value."""
    remarks: str | None = None
    """Any additional remarks regarding the DNEL."""


class LethalDoseConcentration(BaseAlbertModel):
    """
    LethalDoseConcentration is a Pydantic model representing lethal dose and concentration information."""

    duration: str | None = None
    """The duration of the exposure."""
    unit: str | None = None
    """The unit of measurement for the lethal dose."""
    type: str | None = None
    """The type of the lethal dose."""
    species: str | None = None
    """The species tested."""
    value: float | None = None
    """The lethal dose value."""
    sex: str | None = None
    """The sex of the species tested."""
    exposure_time: str | None = Field(None, alias="exposureTime")
    """The exposure time for the lethal dose test."""
    method: str | None = None
    """The method used for the lethal dose test."""
    test_atmosphere: str | None = Field(None, alias="testAtmosphere")
    """The atmosphere in which the test was conducted."""


class ExposureControl(BaseAlbertModel):
    """
    ExposureControl is a Pydantic model representing exposure control measures."""

    type: str | None = None
    """The type of exposure control."""
    value: float | None = None
    """The value associated with the exposure control."""
    unit: str | None = None
    """The unit of measurement for the exposure control."""


class Hazard(BaseAlbertModel):
    """
    Hazard is a Pydantic model representing hazard information."""

    h_code: str | None = Field(None, alias="hCode")
    """The hazard code."""
    category: int | str | None = None
    """The category of the hazard."""
    class_: str | None = Field(None, alias="class")
    """The class of the hazard."""
    sub_category: str | None = Field(None, alias="subCategory")
    """The sub-category of the hazard."""


class SubstanceName(BaseAlbertModel):
    """
    SubstanceName is a Pydantic model representing the name of a substance."""

    name: str | None = None
    """The name of the substance."""
    language_code: str | None = None
    """The language code for the substance name."""
    cloaked_name: str | None = Field(None, alias="cloakedName")
    """The cloaked name of the substance, if applicable."""


class SpecificConcentration(BaseAlbertModel):
    """
    SpecificConcentration is a Pydantic model representing specific concentration information."""

    specific_conc: str | None = None
    """The specific concentration value."""
    sub_category: str | None = Field(None, alias="subCategory")
    """The sub-category of the specific concentration."""
    category: int | None = None
    """The category of the specific concentration."""
    h_code: str | None = Field(None, alias="hCode")
    """The hazard code associated with the specific concentration."""
    class_: str | None = Field(None, alias="class")
    """The class of the specific concentration."""


class MolecularWeightValue(BaseAlbertModel):
    """
    MolecularWeightValue is a Pydantic model representing a molecular weight value."""

    min_value: str | None = Field(None, alias="minValue")
    """The minimum molecular weight value."""
    max_value: str | None = Field(None, alias="maxValue")
    """The maximum molecular weight value."""
    unit: str | None = None
    """The unit of measurement for the molecular weight."""


class MolecularWeight(BaseAlbertModel):
    """
    MolecularWeight is a Pydantic model representing molecular weight information."""

    values: list[MolecularWeightValue] | None = None
    """The list of molecular weight values."""


class RSLSanitizer(BaseAlbertModel):
    """
    RSLSanitizer is a Pydantic model representing sanitizer information."""

    value: float | None = None
    """The value of the sanitizer."""
    unit: str | None = None
    """The unit of measurement for the sanitizer."""


class RSL(BaseAlbertModel):
    """
    RSL is a Pydantic model representing the Restricted substances list (RSL) information."""

    sanitizer: RSLSanitizer | None = None
    """The sanitizer information associated with the RSL."""


class SkinCorrosionInfo(BaseAlbertModel):
    """
    SkinCorrosionInfo is a Pydantic model representing skin corrosion information."""

    result: str | None = None
    """The result of the skin corrosion test."""
    roe: str | None = None
    """The reference exposure level."""
    unit: str | None = None
    """The unit of measurement for the skin corrosion test."""
    method: str | None = None
    """The method used for the skin corrosion test."""
    value: float | None = None
    """The value of the skin corrosion test."""
    species: str | None = None
    """The species tested for skin corrosion."""


class SeriousEyeDamageInfo(BaseAlbertModel):
    """
    SeriousEyeDamageInfo is a Pydantic model representing serious eye damage information."""

    result: str | None = None
    """The result of the serious eye damage test."""
    roe: str | None = None
    """The reference exposure level."""
    unit: str | None = None
    """The unit of measurement for the serious eye damage test."""
    method: str | None = None
    """The method used for the serious eye damage test."""
    value: float | None = None
    """The value of the serious eye damage test."""
    species: str | None = None
    """The species tested for serious eye damage."""


class RespiratorySkinSensInfo(BaseAlbertModel):
    """
    RespiratorySkinSensInfo is a Pydantic model representing respiratory and skin sensitization information."""

    result: str | None = None
    """The result of the respiratory skin sensitization test."""
    roe: str | None = None
    """The reference exposure level."""
    method: str | None = None
    """The method used for the respiratory skin sensitization test."""
    species: str | None = None
    """The species tested for respiratory skin sensitization."""


class SubstanceInfo(BaseAlbertModel):
    """Regulatory, hazard, and property profile of a chemical substance.

    Bundles the compliance data Albert holds for a single chemical, keyed by its
    CAS number: GHS hazard classifications, toxicity and ecotoxicity study data,
    occupational exposure limits, physical properties, and membership on
    regulatory lists across many jurisdictions (US federal and state
    right-to-know lists, EU REACH annexes and candidate lists, and national
    inventories). Fields are largely optional because coverage varies by
    chemical and region.

    This is read-only reference data retrieved by CAS number through
    [`SubstanceCollection`][albert.collections.substance.SubstanceCollection]
    (``client.substances``); it is not constructed directly. Many list-valued
    fields hold repeated study records (e.g. one entry per toxicity study)."""

    type: Literal["Substance"] = "Substance"
    acute_dermal_tox_info: list[ToxicityInfo] | None = Field(None, alias="acuteDermalToxInfo")
    """Information about acute dermal toxicity."""
    acute_inhalation_tox_info: list[ToxicityInfo] | None = Field(
        None, alias="acuteInhalationToxInfo"
    )
    """Information about acute inhalation toxicity."""
    acute_oral_tox_info: list[ToxicityInfo] | None = Field(None, alias="acuteOralToxInfo")
    """Information about acute oral toxicity."""
    acute_tox_info: list[ToxicityInfo] | None = Field(None, alias="acuteToxInfo")
    """General acute toxicity information."""
    bio_accumulative_info: list[BioAccumulativeInfo] | None = Field(
        None, alias="bioAccumulativeInfo"
    )
    """Information about bioaccumulation."""
    boilingpoint_info: list[BoilingPointInfo] | None = Field(None, alias="boilingpointInfo")
    """Information about boiling points."""
    cas_id: str = Field(..., alias="casID")
    """The CAS number of the substance."""
    classification: str | None = None
    """The classification of the substance."""
    classification_type: str | None = Field(default=None, alias="classificationType")
    """The type of classification."""
    degradability_info: list[DegradabilityInfo] | None = Field(None, alias="degradabilityInfo")
    """Information about degradability."""
    dnel_info: list[DNELInfo] | None = Field(None, alias="dnelInfo")
    """Information about the Derived No Effect Level (DNEL)."""
    ec_list_no: str | None = Field(default=None, alias="ecListNo")
    """The EC list number."""
    exposure_controls_acgih: list[ExposureControl] | None = Field(
        None, alias="exposureControlsACGIH"
    )
    """ACGIH exposure controls."""
    hazards: list[Hazard] | None = None
    """List of hazards associated with the substance."""
    iarc_carcinogen: str | None = Field(None, alias="iarcCarcinogen")
    """IARC carcinogen classification."""
    ntp_carcinogen: str | None = Field(None, alias="ntpCarcinogen")
    """NTP carcinogen classification."""
    osha_carcinogen: bool | None = Field(None, alias="oshaCarcinogen")
    """OSHA carcinogen classification."""
    health_effects: str | None = Field(None, alias="healthEffects")
    """Information about health effects."""
    name: list[SubstanceName] | None = None
    """Names of the substance."""
    page_number: int | None = Field(None, alias="pageNumber")
    """Page number for reference."""
    aicis_notified: bool | None = Field(None, alias="aicisNotified")
    """Indicates if AICIS has been notified."""
    approved_legal_entities: Any | None = Field(None, alias="approvedLegalEntities")
    """Approved legal entities for the substance."""
    aspiration_tox_info: list[Any] | None = Field(None, alias="aspirationToxInfo")
    """Information about aspiration toxicity."""
    basel_conv_list: bool | None = Field(None, alias="baselConvList")
    """Indicates if the substance is on the Basel Convention list."""
    bei_info: list[Any] | None = Field(None, alias="beiInfo")
    """Information related to BEI."""
    caa_cfr_40: bool | None = Field(None, alias="caaCFR40")
    """Indicates compliance with CAA CFR 40."""
    caa_hpa: bool | None = Field(None, alias="caaHPA")
    """Indicates compliance with CAA HPA."""
    canada_inventory_status: str | None = Field(None, alias="canadaInventoryStatus")
    """Status in the Canadian inventory."""
    carcinogen_info: list[Any] | None = Field(None, alias="carcinogenInfo")
    """Information about carcinogenicity."""
    chemical_category: list[str] | None = Field(None, alias="chemicalCategory")
    """Categories of the chemical."""
    dermal_acute_toxicity: float | None = Field(None, alias="dermalAcuteToxicity")
    """Acute dermal toxicity value."""
    inhalation_acute_toxicity: float | None = Field(None, alias="inhalationAcuteToxicity")
    """Acute inhalation toxicity value."""
    oral_acute_toxicity: float | None = Field(None, alias="oralAcuteToxicity")
    """Acute oral toxicity value."""
    lethal_dose_and_concentrations: list[LethalDoseConcentration] | None = Field(
        None, alias="lethalDoseAndConcentrations"
    )
    """Information about lethal doses and concentrations."""
    m_factor: int | None = Field(None, alias="mFactor")
    """M factor for acute toxicity."""
    m_factor_chronic: int | None = Field(None, alias="mFactorChronic")
    """M factor for chronic toxicity."""
    molecular_weight: list[MolecularWeight] | None = Field(None, alias="molecularWeight")
    """Molecular weight information."""
    rsl: RSL | None = Field(None, alias="rsl")
    """Restricted substances list information for the substance."""
    specific_conc_eu: list[SpecificConcentration] | None = Field(None, alias="specificConcEU")
    """Specific concentration information for the EU."""
    specific_conc_source: str | None = Field(None, alias="specificConcSource")
    """Source of specific concentration information."""
    sustainability_status_lbc: str | None = Field(None, alias="sustainabilityStatusLBC")
    """Sustainability status under LBC."""
    tsca_8b: bool | None = Field(None, alias="tsca8B")
    """Indicates compliance with TSCA 8(b)."""
    cdsa_list: bool | None = Field(None, alias="cdsaList")
    """Indicates if the substance is on the CDSA list."""
    cn_csd_c_regulations: bool | None = Field(None, alias="cnCSDCRegulations")
    """Compliance with CN CSDC regulations."""
    cn_pcod_list: bool | None = Field(None, alias="cnPCODList")
    """Indicates if the substance is on the CN PCOD list."""
    cn_priority_list: bool | None = Field(None, alias="cnPriorityList")
    """Indicates if the substance is on the CN priority list."""
    ec_notified: str | None = Field(None, alias="ecNotified")
    """Notification status in the EC."""
    eu_annex_14_substances_list: bool | None = Field(None, alias="euAnnex14SubstancesList")
    """Indicates if the substance is on the EU Annex 14 list."""
    eu_annex_17_restrictions_list: bool | None = Field(None, alias="euAnnex17RestrictionsList")
    """Indicates if the substance is on the EU Annex 17 restrictions list."""
    eu_annex_17_substances_list: bool | None = Field(None, alias="euAnnex17SubstancesList")
    """Indicates if the substance is on the EU Annex 17 substances list."""
    eu_candidate_list: bool | None = Field(None, alias="euCandidateList")
    """Indicates if the substance is on the EU candidate list."""
    eu_dang_chem_annex_1_part_1_list: bool | None = Field(None, alias="euDangChemAnnex1Part1List")
    """Indicates if the substance is on the EU dangerous chemicals Annex 1 Part 1 list."""
    eu_dang_chem_annex_1_part_2_list: bool | None = Field(None, alias="euDangChemAnnex1Part2List")
    """Indicates if the substance is on the EU dangerous chemicals Annex 1 Part 2 list."""
    eu_dang_chem_annex_1_part_3_list: bool | None = Field(None, alias="euDangChemAnnex1Part3List")
    """Indicates if the substance is on the EU dangerous chemicals Annex 1 Part 3 list."""
    eu_dang_chem_annex_5_list: bool | None = Field(None, alias="euDangChemAnnex5List")
    """Indicates if the substance is on the EU dangerous chemicals Annex 5 list."""
    eu_directive_ec_list: bool | None = Field(None, alias="euDirectiveEcList")
    """Indicates if the substance is on the EU directive EC list."""
    eu_explosive_precursors_annex_1_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex1List"
    )
    """Indicates if the substance is on the EU explosive precursors Annex 1 list."""
    eu_explosive_precursors_annex_2_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex2List"
    )
    """Indicates if the substance is on the EU explosive precursors Annex 2 list."""
    eu_ozone_depletion_list: bool | None = Field(None, alias="euOzoneDepletionList")
    """Indicates if the substance is on the EU ozone depletion list."""
    eu_pollutant_annex_2_list: bool | None = Field(None, alias="euPollutantAnnex2List")
    """Indicates if the substance is on the EU pollutant Annex 2 list."""
    eu_pop_list: bool | None = Field(None, alias="euPopList")
    """Indicates if the substance is on the EU POP list."""
    export_control_list_phrases: bool | None = Field(None, alias="exportControlListPhrases")
    """Indicates if the substance is on the export control list."""
    green_gas_list: bool | None = Field(None, alias="greenGasList")
    """Indicates if the substance is on the green gas list."""
    iecsc_notified: bool | None = Field(None, alias="iecscNotified")
    """Indicates if the substance is IECSc notified."""
    index_no: str | None = Field(None, alias="indexNo")
    """Index number for the substance."""
    jpencs_notified: bool | None = Field(None, alias="jpencsNotified")
    """Indicates if the substance is JPENCS notified."""
    jpishl_notified: bool | None = Field(None, alias="jpishlNotified")
    """Indicates if the substance is JPISHL notified."""
    koecl_notified: bool | None = Field(None, alias="koeclNotified")
    """Indicates if the substance is KOECL notified."""
    kyoto_protocol: bool | None = Field(None, alias="kyotoProtocol")
    """Indicates compliance with the Kyoto Protocol."""
    massachusetts_rtk: bool | None = Field(None, alias="massachusettsRTK")
    """Indicates if the substance is on the Massachusetts RTK list."""
    montreal_protocol: bool | None = Field(None, alias="montrealProtocol")
    """Indicates compliance with the Montreal Protocol."""
    new_jersey_rtk: bool | None = Field(None, alias="newJerseyRTK")
    """Indicates if the substance is on the New Jersey RTK list."""
    new_york_rtk: bool | None = Field(None, alias="newYorkRTK")
    """Indicates if the substance is on the New York RTK list."""
    nzioc_notified: bool | None = Field(None, alias="nziocNotified")
    """Indicates if the substance is NZIOC notified."""
    pcr_regulated: bool | None = Field(None, alias="pcrRegulated")
    """Indicates if the substance is PCR regulated."""
    pennsylvania_rtk: bool | None = Field(None, alias="pennsylvaniaRTK")
    """Indicates if the substance is on the Pennsylvania RTK list."""
    peroxide_function_groups: int | None = Field(None, alias="peroxideFunctionGroups")
    """Number of peroxide function groups."""
    piccs_notified: bool | None = Field(None, alias="piccsNotified")
    """Indicates if the substance is PICCS notified."""
    rhode_island_rtk: bool | None = Field(None, alias="rhodeIslandRTK")
    """Indicates if the substance is on the Rhode Island RTK list."""
    rotterdam_conv_list: bool | None = Field(None, alias="rotterdamConvList")
    """Indicates if the substance is on the Rotterdam Convention list."""
    sdwa: bool | None = Field(None, alias="sdwa")
    """Indicates compliance with the SDWA."""
    source: str | None = Field(None, alias="source")
    """Source of the substance information."""
    specific_concentration_limit: str | None = Field(None, alias="specificConcentrationLimit")
    """Specific concentration limit for the substance."""
    stockholm_conv_list: bool | None = Field(None, alias="stockholmConvList")
    """Indicates if the substance is on the Stockholm Convention list."""
    stot_affected_organs: str | None = Field(None, alias="stotAffectedOrgans")
    """Organs affected by STOT."""
    stot_route_of_exposure: str | None = Field(None, alias="stotRouteOfExposure")
    """Route of exposure for STOT."""
    tcsi_notified: bool | None = Field(None, alias="tcsiNotified")
    """Indicates if the substance is TCSI notified."""
    trade_secret: bool | None = Field(None, alias="tradeSecret")
    """Whether the substance is marked as a trade secret."""
    tw_ghs_clas_list: bool | None = Field(None, alias="twGHSClasList")
    """Indicates if the substance is on the TW GHS classification list."""
    tw_handle_priority_chem: bool | None = Field(None, alias="twHandlePriorityChem")
    """Indicates if the substance is a priority chemical."""
    tw_handle_toxic_chem: bool | None = Field(None, alias="twHandleToxicChem")
    """Indicates if the substance is a toxic chemical."""
    tw_ind_waste_standards: bool | None = Field(None, alias="twIndWasteStandards")
    """Indicates compliance with TW industrial waste standards."""
    vinic_notified: bool | None = Field(None, alias="vinicNotified")
    """Indicates if the substance is VINIC notified."""
    exposure_controls_osha: list[ExposureControl] | None = Field(
        None, alias="exposureControlsOSHA"
    )
    """OSHA exposure controls."""
    exposure_controls_aiha: list[ExposureControl] | None = Field(
        None, alias="exposureControlsAIHA"
    )
    """AIHA exposure controls."""
    exposure_controls_niosh: list[ExposureControl] | None = Field(
        None, alias="exposureControlsNIOSH"
    )
    """NIOSH exposure controls."""
    snur: bool | dict | None = None
    """Significant new use rule information."""
    tsca_12b_concentration_limit: float | None = Field(None, alias="tsca12BConcentrationLimit")
    """TSCA 12(b) concentration limit."""
    cercla_rq: float | None = Field(None, alias="cerclaRQ")
    """CERCLA reportable quantity."""
    california_prop_65: list[str] | None = Field(None, alias="californiaProp65")
    """Information related to California Prop 65."""
    sara_302: bool | None = Field(None, alias="sara302")
    """Indicates compliance with SARA 302."""
    sara_313_concentration_limit: float | None = Field(None, alias="sara313ConcentrationLimit")
    """SARA 313 concentration limit."""
    cfr_marine_pollutant: dict | None = Field(None, alias="CFRmarinePollutant")
    """Information about marine pollutants under CFR."""
    cfr_reportable_quantity: dict | None = Field(None, alias="CFRreportableQuantity")
    """Information about reportable quantities under CFR."""
    rohs_concentration: float | None = Field(None, alias="rohsConcentration")
    """ROHS concentration limit."""
    skin_corrosion_info: list[SkinCorrosionInfo] | None = Field(None, alias="skinCorrosionInfo")
    """Information about skin corrosion."""
    serious_eye_damage_info: list[SeriousEyeDamageInfo] | None = Field(
        None, alias="seriousEyeDamageInfo"
    )
    """Information about serious eye damage."""
    respiratory_skin_sens_info: list[RespiratorySkinSensInfo] | None = Field(
        None, alias="respiratorySkinSensInfo"
    )
    """Information about respiratory skin sensitization."""
    is_known: bool = Field(default=True, alias="isCas")
    """Indicates if the substance is known (i.e. has known regulatory or hazard information in the database) (note this is an alias for the isCas field which behaves in a non intuitive way in the API so we have opted to use is_known for usability instead)"""


class SubstanceResponse(BaseAlbertModel):
    """Raw API response wrapping the substances returned for a lookup.

    Returned internally by
    [`SubstanceCollection`][albert.collections.substance.SubstanceCollection], which unwraps the
    ``substances`` list for callers; you typically will not use this directly."""

    substances: list[SubstanceInfo]
    """The substances found for the requested CAS numbers."""
    substance_errors: list[dict[str, Any]] | None = Field(None, alias="substanceErrors")
    """Errors for CAS numbers that could not be resolved, if any."""
