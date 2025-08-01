from typing import Any, Literal

from pydantic import Field

from albert.core.base import BaseAlbertModel


class ToxicityInfo(BaseAlbertModel):
    """
    ToxicityInfo is a Pydantic model representing toxicity information.

    Attributes
    ----------
    result : str | None
        The result of the toxicity test.
    roe : str | None
        The reference exposure level.
    unit : str | None
        The unit of the toxicity test.
    method: str | None
        The method of the toxicity test.
    value: float | None
        The value of the toxicity test.
    species: str | None
        The species of the toxicity test.
    sex: str | None
        The sex of the toxicity test.
    exposure_time: str | None
        The exposure time of the toxicity test.
    type: str | None
        The type of the toxicity test.
    value_type: str | None
        The value type of the toxicity test.
    temperature: str | None
        The temperature of the toxicity test.
    """

    result: str | None = None
    roe: str | None = None
    unit: str | None = None
    method: str | None = None
    value: float | None = None
    species: str | None = None
    sex: str | None = None
    exposure_time: str | None = Field(None, alias="exposureTime")
    type: str | None = None
    value_type: str | None = Field(None, alias="valueType")
    temperature: str | None = None


class BioAccumulativeInfo(BaseAlbertModel):
    """
    BioAccumulativeInfo is a Pydantic model representing bioaccumulative information.

    Attributes
    ----------
    bcf_value : str | None
        The bioaccumulative factor value.
    temperature : str | None
        The temperature of the bioaccumulative test.
    exposure_time : str | None
        The exposure time of the bioaccumulative test.
    method : str | None
        The method of the bioaccumulative test.
    species : str | None
        The species of the bioaccumulative test.
    """

    bcf_value: str | None = Field(None, alias="bcfValue")
    temperature: str | None = None
    exposure_time: str | None = Field(None, alias="exposureTime")
    method: str | None = None
    species: str | None = None


class BoilingPointValue(BaseAlbertModel):
    """
    BoilingPointValue is a Pydantic model representing a boiling point value.

    Attributes
    ----------
    min_value : str | None
        The minimum boiling point value.
    max_value : str | None
        The maximum boiling point value.
    unit : str | None
        The unit of the boiling point value.
    """

    min_value: str | None = Field(None, alias="minValue")
    max_value: str | None = Field(None, alias="maxValue")
    unit: str | None = None


class BoilingPointSource(BaseAlbertModel):
    """
    BoilingPointSource is a Pydantic model representing a boiling point source.

    Attributes
    ----------
    note_code : str | None
        The note code of the boiling point source.
    note : str | None
        The note of the boiling point source.
    note_field : str | None
        The note field of the boiling point source.
    """

    note_code: str | None = Field(None, alias="noteCode")
    note: str | None = None
    note_field: str | None = Field(None, alias="noteField")


class BoilingPointInfo(BaseAlbertModel):
    """
    BoilingPointInfo is a Pydantic model representing boiling point information.

    Attributes
    ----------
    source : list[BoilingPointSource] | None
        The source of the boiling point information.
    values : list[BoilingPointValue] | None
        The values of the boiling point information.
    """

    source: list[BoilingPointSource] | None = None
    values: list[BoilingPointValue] | None = None


class DegradabilityInfo(BaseAlbertModel):
    """
    DegradabilityInfo is a Pydantic model representing information about the degradability of a substance.

    Attributes
    ----------
    result : str | None
        The result of the degradability test.
    unit : str | None
        The unit of measurement for the degradability test.
    exposure_time : str | None
        The exposure time of the degradability test.
    method : str | None
        The method used for the degradability test.
    test_type : str | None
        The type of the degradability test.
    degradability : str | None
        The degradability classification.
    value : str | None
        The value of the degradability test.
    """

    result: str | None = None
    unit: str | None = None
    exposure_time: str | None = Field(None, alias="exposureTime")
    method: str | None = None
    test_type: str | None = Field(None, alias="testType")
    degradability: str | None = None
    value: str | None = None


class DNELInfo(BaseAlbertModel):
    """
    DNELInfo is a Pydantic model representing the Derived No Effect Level (DNEL) information.

    Attributes
    ----------
    roe : str | None
        The reference exposure level.
    health_effect : str | None
        The health effect associated with the exposure.
    exposure_time : str | None
        The exposure time for the DNEL.
    application_area : str | None
        The area of application for the DNEL.
    value : str | None
        The DNEL value.
    remarks : str | None
        Any additional remarks regarding the DNEL.
    """

    roe: str | None = None
    health_effect: str | None = Field(None, alias="healthEffect")
    exposure_time: str | None = Field(None, alias="exposureTime")
    application_area: str | None = Field(None, alias="applicationArea")
    value: str | None = None
    remarks: str | None = None


class LethalDoseConcentration(BaseAlbertModel):
    """
    LethalDoseConcentration is a Pydantic model representing lethal dose and concentration information.

    Attributes
    ----------
    duration : str | None
        The duration of the exposure.
    unit : str | None
        The unit of measurement for the lethal dose.
    type : str | None
        The type of the lethal dose.
    species : str | None
        The species tested.
    value : float | None
        The lethal dose value.
    sex : str | None
        The sex of the species tested.
    exposure_time : str | None
        The exposure time for the lethal dose test.
    method : str | None
        The method used for the lethal dose test.
    test_atmosphere : str | None
        The atmosphere in which the test was conducted.
    """

    duration: str | None = None
    unit: str | None = None
    type: str | None = None
    species: str | None = None
    value: float | None = None
    sex: str | None = None
    exposure_time: str | None = Field(None, alias="exposureTime")
    method: str | None = None
    test_atmosphere: str | None = Field(None, alias="testAtmosphere")


class ExposureControl(BaseAlbertModel):
    """
    ExposureControl is a Pydantic model representing exposure control measures.

    Attributes
    ----------
    type : str | None
        The type of exposure control.
    value : float | None
        The value associated with the exposure control.
    unit : str | None
        The unit of measurement for the exposure control.
    """

    type: str | None = None
    value: float | None = None
    unit: str | None = None


class Hazard(BaseAlbertModel):
    """
    Hazard is a Pydantic model representing hazard information.

    Attributes
    ----------
    h_code : str | None
        The hazard code.
    category : str | None
        The category of the hazard.
    class_ : str | None
        The class of the hazard.
    sub_category : str | None
        The sub-category of the hazard.
    """

    h_code: str | None = Field(None, alias="hCode")
    category: int | str | None = None
    class_: str | None = Field(None, alias="class")
    sub_category: str | None = Field(None, alias="subCategory")


class SubstanceName(BaseAlbertModel):
    """
    SubstanceName is a Pydantic model representing the name of a substance.

    Attributes
    ----------
    name : str | None
        The name of the substance.
    language_code : str | None
        The language code for the substance name.
    cloaked_name : str | None
        The cloaked name of the substance, if applicable.
    """

    name: str | None = None
    language_code: str | None = None
    cloaked_name: str | None = Field(None, alias="cloakedName")


class SpecificConcentration(BaseAlbertModel):
    """
    SpecificConcentration is a Pydantic model representing specific concentration information.

    Attributes
    ----------
    specific_conc : str | None
        The specific concentration value.
    sub_category : str | None
        The sub-category of the specific concentration.
    category : int | None
        The category of the specific concentration.
    h_code : str | None
        The hazard code associated with the specific concentration.
    class_ : str | None
        The class of the specific concentration.
    """

    specific_conc: str | None = None
    sub_category: str | None = Field(None, alias="subCategory")
    category: int | None = None
    h_code: str | None = Field(None, alias="hCode")
    class_: str | None = Field(None, alias="class")


class MolecularWeightValue(BaseAlbertModel):
    """
    MolecularWeightValue is a Pydantic model representing a molecular weight value.

    Attributes
    ----------
    min_value : str | None
        The minimum molecular weight value.
    max_value : str | None
        The maximum molecular weight value.
    unit : str | None
        The unit of measurement for the molecular weight.
    """

    min_value: str | None = Field(None, alias="minValue")
    max_value: str | None = Field(None, alias="maxValue")
    unit: str | None = None


class MolecularWeight(BaseAlbertModel):
    """
    MolecularWeight is a Pydantic model representing molecular weight information.

    Attributes
    ----------
    values : list[MolecularWeightValue] | None
        The list of molecular weight values.
    """

    values: list[MolecularWeightValue] | None = None


class RSLSanitizer(BaseAlbertModel):
    """
    RSLSanitizer is a Pydantic model representing sanitizer information.

    Attributes
    ----------
    value : float | None
        The value of the sanitizer.
    unit : str | None
        The unit of measurement for the sanitizer.
    """

    value: float | None = None
    unit: str | None = None


class RSL(BaseAlbertModel):
    """
    RSL is a Pydantic model representing the regulatory substance list (RSL) information.

    Attributes
    ----------
    sanitizer : RSLSanitizer | None
        The sanitizer information associated with the RSL.
    """

    sanitizer: RSLSanitizer | None = None


class SkinCorrosionInfo(BaseAlbertModel):
    """
    SkinCorrosionInfo is a Pydantic model representing skin corrosion information.

    Attributes
    ----------
    result : str | None
        The result of the skin corrosion test.
    roe : str | None
        The reference exposure level.
    unit : str | None
        The unit of measurement for the skin corrosion test.
    method : str | None
        The method used for the skin corrosion test.
    value : float | None
        The value of the skin corrosion test.
    species : str | None
        The species tested for skin corrosion.
    """

    result: str | None = None
    roe: str | None = None
    unit: str | None = None
    method: str | None = None
    value: float | None = None
    species: str | None = None


class SeriousEyeDamageInfo(BaseAlbertModel):
    """
    SeriousEyeDamageInfo is a Pydantic model representing serious eye damage information.

    Attributes
    ----------
    result : str | None
        The result of the serious eye damage test.
    roe : str | None
        The reference exposure level.
    unit : str | None
        The unit of measurement for the serious eye damage test.
    method : str | None
        The method used for the serious eye damage test.
    value : float | None
        The value of the serious eye damage test.
    species : str | None
        The species tested for serious eye damage.
    """

    result: str | None = None
    roe: str | None = None
    unit: str | None = None
    method: str | None = None
    value: float | None = None
    species: str | None = None


class RespiratorySkinSensInfo(BaseAlbertModel):
    """
    RespiratorySkinSensInfo is a Pydantic model representing respiratory and skin sensitization information.

    Attributes
    ----------
    result : str | None
        The result of the respiratory skin sensitization test.
    roe : str | None
        The reference exposure level.
    method : str | None
        The method used for the respiratory skin sensitization test.
    species : str | None
        The species tested for respiratory skin sensitization.
    """

    result: str | None = None
    roe: str | None = None
    method: str | None = None
    species: str | None = None


class SubstanceInfo(BaseAlbertModel):
    """
    SubstanceInfo is a Pydantic model representing information about a chemical substance.

    Attributes
    ----------
    acute_dermal_tox_info : list[ToxicityInfo] | None
        Information about acute dermal toxicity.
    acute_inhalation_tox_info : list[ToxicityInfo] | None
        Information about acute inhalation toxicity.
    acute_oral_tox_info : list[ToxicityInfo] | None
        Information about acute oral toxicity.
    acute_tox_info : list[ToxicityInfo] | None
        General acute toxicity information.
    bio_accumulative_info : list[BioAccumulativeInfo] | None
        Information about bioaccumulation.
    boiling_point_info : list[BoilingPointInfo] | None
        Information about boiling points.
    cas_id : str
        The CAS ID of the substance.
    classification : str | None
        The classification of the substance.
    classification_type : str
        The type of classification.
    degradability_info : list[DegradabilityInfo] | None
        Information about degradability.
    dnel_info : list[DNELInfo] | None
        Information about the Derived No Effect Level (DNEL).
    ec_list_no : str
        The EC list number.
    exposure_controls_acgih : list[ExposureControl] | None
        ACGIH exposure controls.
    hazards : list[Hazard] | None
        List of hazards associated with the substance.
    iarc_carcinogen : str | None
        IARC carcinogen classification.
    ntp_carcinogen : str | None
        NTP carcinogen classification.
    osha_carcinogen : bool | None
        OSHA carcinogen classification.
    health_effects : str | None
        Information about health effects.
    name : list[SubstanceName] | None
        Names of the substance.
    page_number : int | None
        Page number for reference.
    aicis_notified : bool | None
        Indicates if AICIS has been notified.
    approved_legal_entities : Any | None
        Approved legal entities for the substance.
    aspiration_tox_info : list[Any] | None
        Information about aspiration toxicity.
    basel_conv_list : bool | None
        Indicates if the substance is on the Basel Convention list.
    bei_info : list[Any] | None
        Information related to BEI.
    caa_cfr40 : bool | None
        Indicates compliance with CAA CFR 40.
    caa_hpa : bool | None
        Indicates compliance with CAA HPA.
    canada_inventory_status : str | None
        Status in the Canadian inventory.
    carcinogen_info : list[Any] | None
        Information about carcinogenicity.
    chemical_category : list[str] | None
        Categories of the chemical.
    dermal_acute_toxicity : float | None
        Acute dermal toxicity value.
    inhalation_acute_toxicity : float | None
        Acute inhalation toxicity value.
    oral_acute_toxicity : float | None
        Acute oral toxicity value.
    lethal_dose_and_concentrations : list[LethalDoseConcentration] | None
        Information about lethal doses and concentrations.
    m_factor : int | None
        M factor for acute toxicity.
    m_factor_chronic : int | None
        M factor for chronic toxicity.
    molecular_weight : list[MolecularWeight] | None
        Molecular weight information.
    rsl : RSL | None
        Risk-based screening level.
    specific_conc_eu : list[SpecificConcentration] | None
        Specific concentration information for the EU.
    specific_conc_source : str | None
        Source of specific concentration information.
    sustainability_status_lbc : str | None
        Sustainability status under LBC.
    tsca_8b : bool | None
        Indicates compliance with TSCA 8(b).
    cdsa_list : bool | None
        Indicates if the substance is on the CDSA list.
    cn_csdc_regulations : bool | None
        Compliance with CN CSDC regulations.
    cn_pcod_list : bool | None
        Indicates if the substance is on the CN PCOD list.
    cn_priority_list : bool | None
        Indicates if the substance is on the CN priority list.
    ec_notified : str | None
        Notification status in the EC.
    eu_annex_14_substances_list : bool | None
        Indicates if the substance is on the EU Annex 14 list.
    eu_annex_17_restrictions_list : bool | None
        Indicates if the substance is on the EU Annex 17 restrictions list.
    eu_annex_17_substances_list : bool | None
        Indicates if the substance is on the EU Annex 17 substances list.
    eu_candidate_list : bool | None
        Indicates if the substance is on the EU candidate list.
    eu_dang_chem_annex_1_part_1_list : bool | None
        Indicates if the substance is on the EU dangerous chemicals Annex 1 Part 1 list.
    eu_dang_chem_annex_1_part_2_list : bool | None
        Indicates if the substance is on the EU dangerous chemicals Annex 1 Part 2 list.
    eu_dang_chem_annex_1_part_3_list : bool | None
        Indicates if the substance is on the EU dangerous chemicals Annex 1 Part 3 list.
    eu_dang_chem_annex_5_list : bool | None
        Indicates if the substance is on the EU dangerous chemicals Annex 5 list.
    eu_directive_ec_list : bool | None
        Indicates if the substance is on the EU directive EC list.
    eu_explosive_precursors_annex_1_list : bool | None
        Indicates if the substance is on the EU explosive precursors Annex 1 list.
    eu_explosive_precursors_annex_2_list : bool | None
        Indicates if the substance is on the EU explosive precursors Annex 2 list.
    eu_ozone_depletion_list : bool | None
        Indicates if the substance is on the EU ozone depletion list.
    eu_pollutant_annex_2_list : bool | None
        Indicates if the substance is on the EU pollutant Annex 2 list.
    eu_pop_list : bool | None
        Indicates if the substance is on the EU POP list.
    export_control_list_phrases : bool | None
        Indicates if the substance is on the export control list.
    green_gas_list : bool | None
        Indicates if the substance is on the green gas list.
    iecsc_notified : bool | None
        Indicates if the substance is IECSc notified.
    index_no : str | None
        Index number for the substance.
    jpencs_notified : bool | None
        Indicates if the substance is JPENCS notified.
    jpishl_notified : bool | None
        Indicates if the substance is JPISHL notified.
    koecl_notified : bool | None
        Indicates if the substance is KOECL notified.
    kyoto_protocol : bool | None
        Indicates compliance with the Kyoto Protocol.
    massachusetts_rtk : bool | None
        Indicates if the substance is on the Massachusetts RTK list.
    montreal_protocol : bool | None
        Indicates compliance with the Montreal Protocol.
    new_jersey_rtk : bool | None
        Indicates if the substance is on the New Jersey RTK list.
    new_york_rtk : bool | None
        Indicates if the substance is on the New York RTK list.
    nzioc_notified : bool | None
        Indicates if the substance is NZIOC notified.
    pcr_regulated : bool | None
        Indicates if the substance is PCR regulated.
    pennsylvania_rtk : bool | None
        Indicates if the substance is on the Pennsylvania RTK list.
    peroxide_function_groups : int | None
        Number of peroxide function groups.
    piccs_notified : bool | None
        Indicates if the substance is PICCS notified.
    rhode_island_rtk : bool | None
        Indicates if the substance is on the Rhode Island RTK list.
    rotterdam_conv_list : bool | None
        Indicates if the substance is on the Rotterdam Convention list.
    sdwa : bool | None
        Indicates compliance with the SDWA.
    source : str | None
        Source of the substance information.
    specific_concentration_limit : str | None
        Specific concentration limit for the substance.
    stockholm_conv_list : bool | None
        Indicates if the substance is on the Stockholm Convention list.
    stot_affected_organs : str | None
        Organs affected by STOT.
    stot_route_of_exposure : str | None
        Route of exposure for STOT.
    tcsi_notified : bool | None
        Indicates if the substance is TCSI notified.
    trade_secret : str | None
        Information about trade secrets.
    tw_ghs_clas_list : bool | None
        Indicates if the substance is on the TW GHS classification list.
    tw_handle_priority_chem : bool | None
        Indicates if the substance is a priority chemical.
    tw_handle_toxic_chem : bool | None
        Indicates if the substance is a toxic chemical.
    tw_ind_waste_standards : bool | None
        Indicates compliance with TW industrial waste standards.
    vinic_notified : bool | None
        Indicates if the substance is VINIC notified.
    exposure_controls_osha : list[ExposureControl] | None
        OSHA exposure controls.
    exposure_controls_aiha : list[ExposureControl] | None
        AIHA exposure controls.
    exposure_controls_niosh : list[ExposureControl] | None
        NIOSH exposure controls.
    snur : bool | dict | None
        Significant new use rule information.
    tsca_12b_concentration_limit : float | None
        TSCA 12(b) concentration limit.
    cercla_rq : float | None
        CERCLA reportable quantity.
    california_prop_65 : list[str] | None
        Information related to California Prop 65.
    sara_302 : bool | None
        Indicates compliance with SARA 302.
    sara_313_concentration_limit : float | None
        SARA 313 concentration limit.
    cfr_marine_pollutant : dict | None
        Information about marine pollutants under CFR.
    cfr_reportable_quantity : dict | None
        Information about reportable quantities under CFR.
    rohs_concentration : float | None
        ROHS concentration limit.
    skin_corrosion_info : list[SkinCorrosionInfo] | None
        Information about skin corrosion.
    serious_eye_damage_info : list[SeriousEyeDamageInfo] | None
        Information about serious eye damage.
    respiratory_skin_sens_info : list[RespiratorySkinSensInfo] | None
        Information about respiratory skin sensitization.
    is_known : bool
        Indicates if the substance is known (i.e. has known regulatory or hazard information in the database)
        (note this is an alias for the isCas field which behaves in a non intuitive way in the API so we have opted to use is_known for usability instead)
    """

    type: Literal["Substance"] = "Substance"
    acute_dermal_tox_info: list[ToxicityInfo] | None = Field(None, alias="acuteDermalToxInfo")
    acute_inhalation_tox_info: list[ToxicityInfo] | None = Field(
        None, alias="acuteInhalationToxInfo"
    )
    acute_oral_tox_info: list[ToxicityInfo] | None = Field(None, alias="acuteOralToxInfo")
    acute_tox_info: list[ToxicityInfo] | None = Field(None, alias="acuteToxInfo")
    bio_accumulative_info: list[BioAccumulativeInfo] | None = Field(
        None, alias="bioAccumulativeInfo"
    )
    boilingpoint_info: list[BoilingPointInfo] | None = Field(None, alias="boilingpointInfo")
    cas_id: str = Field(..., alias="casID")
    classification: str | None = None
    classification_type: str | None = Field(default=None, alias="classificationType")
    degradability_info: list[DegradabilityInfo] | None = Field(None, alias="degradabilityInfo")
    dnel_info: list[DNELInfo] | None = Field(None, alias="dnelInfo")
    ec_list_no: str | None = Field(default=None, alias="ecListNo")
    exposure_controls_acgih: list[ExposureControl] | None = Field(
        None, alias="exposureControlsACGIH"
    )
    hazards: list[Hazard] | None = None
    iarc_carcinogen: str | None = Field(None, alias="iarcCarcinogen")
    ntp_carcinogen: str | None = Field(None, alias="ntpCarcinogen")
    osha_carcinogen: bool | None = Field(None, alias="oshaCarcinogen")
    health_effects: str | None = Field(None, alias="healthEffects")
    name: list[SubstanceName] | None = None
    page_number: int | None = Field(None, alias="pageNumber")
    aicis_notified: bool | None = Field(None, alias="aicisNotified")
    approved_legal_entities: Any | None = Field(None, alias="approvedLegalEntities")
    aspiration_tox_info: list[Any] | None = Field(None, alias="aspirationToxInfo")
    basel_conv_list: bool | None = Field(None, alias="baselConvList")
    bei_info: list[Any] | None = Field(None, alias="beiInfo")
    caa_cfr_40: bool | None = Field(None, alias="caaCFR40")
    caa_hpa: bool | None = Field(None, alias="caaHPA")
    canada_inventory_status: str | None = Field(None, alias="canadaInventoryStatus")
    carcinogen_info: list[Any] | None = Field(None, alias="carcinogenInfo")
    chemical_category: list[str] | None = Field(None, alias="chemicalCategory")
    dermal_acute_toxicity: float | None = Field(None, alias="dermalAcuteToxicity")
    inhalation_acute_toxicity: float | None = Field(None, alias="inhalationAcuteToxicity")
    oral_acute_toxicity: float | None = Field(None, alias="oralAcuteToxicity")
    lethal_dose_and_concentrations: list[LethalDoseConcentration] | None = Field(
        None, alias="lethalDoseAndConcentrations"
    )
    m_factor: int | None = Field(None, alias="mFactor")
    m_factor_chronic: int | None = Field(None, alias="mFactorChronic")
    molecular_weight: list[MolecularWeight] | None = Field(None, alias="molecularWeight")
    rsl: RSL | None = Field(None, alias="rsl")
    specific_conc_eu: list[SpecificConcentration] | None = Field(None, alias="specificConcEU")
    specific_conc_source: str | None = Field(None, alias="specificConcSource")
    sustainability_status_lbc: str | None = Field(None, alias="sustainabilityStatusLBC")
    tsca_8b: bool | None = Field(None, alias="tsca8B")
    cdsa_list: bool | None = Field(None, alias="cdsaList")
    cn_csd_c_regulations: bool | None = Field(None, alias="cnCSDCRegulations")
    cn_pcod_list: bool | None = Field(None, alias="cnPCODList")
    cn_priority_list: bool | None = Field(None, alias="cnPriorityList")
    ec_notified: str | None = Field(None, alias="ecNotified")
    eu_annex_14_substances_list: bool | None = Field(None, alias="euAnnex14SubstancesList")
    eu_annex_17_restrictions_list: bool | None = Field(None, alias="euAnnex17RestrictionsList")
    eu_annex_17_substances_list: bool | None = Field(None, alias="euAnnex17SubstancesList")
    eu_candidate_list: bool | None = Field(None, alias="euCandidateList")
    eu_dang_chem_annex_1_part_1_list: bool | None = Field(None, alias="euDangChemAnnex1Part1List")
    eu_dang_chem_annex_1_part_2_list: bool | None = Field(None, alias="euDangChemAnnex1Part2List")
    eu_dang_chem_annex_1_part_3_list: bool | None = Field(None, alias="euDangChemAnnex1Part3List")
    eu_dang_chem_annex_5_list: bool | None = Field(None, alias="euDangChemAnnex5List")
    eu_directive_ec_list: bool | None = Field(None, alias="euDirectiveEcList")
    eu_explosive_precursors_annex_1_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex1List"
    )
    eu_explosive_precursors_annex_2_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex2List"
    )
    eu_ozone_depletion_list: bool | None = Field(None, alias="euOzoneDepletionList")
    eu_pollutant_annex_2_list: bool | None = Field(None, alias="euPollutantAnnex2List")
    eu_pop_list: bool | None = Field(None, alias="euPopList")
    export_control_list_phrases: bool | None = Field(None, alias="exportControlListPhrases")
    green_gas_list: bool | None = Field(None, alias="greenGasList")
    iecsc_notified: bool | None = Field(None, alias="iecscNotified")
    index_no: str | None = Field(None, alias="indexNo")
    jpencs_notified: bool | None = Field(None, alias="jpencsNotified")
    jpishl_notified: bool | None = Field(None, alias="jpishlNotified")
    koecl_notified: bool | None = Field(None, alias="koeclNotified")
    kyoto_protocol: bool | None = Field(None, alias="kyotoProtocol")
    massachusetts_rtk: bool | None = Field(None, alias="massachusettsRTK")
    montreal_protocol: bool | None = Field(None, alias="montrealProtocol")
    new_jersey_rtk: bool | None = Field(None, alias="newJerseyRTK")
    new_york_rtk: bool | None = Field(None, alias="newYorkRTK")
    nzioc_notified: bool | None = Field(None, alias="nziocNotified")
    pcr_regulated: bool | None = Field(None, alias="pcrRegulated")
    pennsylvania_rtk: bool | None = Field(None, alias="pennsylvaniaRTK")
    peroxide_function_groups: int | None = Field(None, alias="peroxideFunctionGroups")
    piccs_notified: bool | None = Field(None, alias="piccsNotified")
    rhode_island_rtk: bool | None = Field(None, alias="rhodeIslandRTK")
    rotterdam_conv_list: bool | None = Field(None, alias="rotterdamConvList")
    sdwa: bool | None = Field(None, alias="sdwa")
    source: str | None = Field(None, alias="source")
    specific_concentration_limit: str | None = Field(None, alias="specificConcentrationLimit")
    stockholm_conv_list: bool | None = Field(None, alias="stockholmConvList")
    stot_affected_organs: str | None = Field(None, alias="stotAffectedOrgans")
    stot_route_of_exposure: str | None = Field(None, alias="stotRouteOfExposure")
    tcsi_notified: bool | None = Field(None, alias="tcsiNotified")
    trade_secret: bool | None = Field(None, alias="tradeSecret")
    tw_ghs_clas_list: bool | None = Field(None, alias="twGHSClasList")
    tw_handle_priority_chem: bool | None = Field(None, alias="twHandlePriorityChem")
    tw_handle_toxic_chem: bool | None = Field(None, alias="twHandleToxicChem")
    tw_ind_waste_standards: bool | None = Field(None, alias="twIndWasteStandards")
    vinic_notified: bool | None = Field(None, alias="vinicNotified")
    exposure_controls_osha: list[ExposureControl] | None = Field(
        None, alias="exposureControlsOSHA"
    )
    exposure_controls_aiha: list[ExposureControl] | None = Field(
        None, alias="exposureControlsAIHA"
    )
    exposure_controls_niosh: list[ExposureControl] | None = Field(
        None, alias="exposureControlsNIOSH"
    )
    snur: bool | dict | None = None
    tsca_12b_concentration_limit: float | None = Field(None, alias="tsca12BConcentrationLimit")
    cercla_rq: float | None = Field(None, alias="cerclaRQ")
    california_prop_65: list[str] | None = Field(None, alias="californiaProp65")
    sara_302: bool | None = Field(None, alias="sara302")
    sara_313_concentration_limit: float | None = Field(None, alias="sara313ConcentrationLimit")
    cfr_marine_pollutant: dict | None = Field(None, alias="CFRmarinePollutant")
    cfr_reportable_quantity: dict | None = Field(None, alias="CFRreportableQuantity")
    rohs_concentration: float | None = Field(None, alias="rohsConcentration")
    skin_corrosion_info: list[SkinCorrosionInfo] | None = Field(None, alias="skinCorrosionInfo")
    serious_eye_damage_info: list[SeriousEyeDamageInfo] | None = Field(
        None, alias="seriousEyeDamageInfo"
    )
    respiratory_skin_sens_info: list[RespiratorySkinSensInfo] | None = Field(
        None, alias="respiratorySkinSensInfo"
    )
    is_known: bool = Field(default=True, alias="isCas")


class SubstanceResponse(BaseAlbertModel):
    """
    SubstanceResponse is a Pydantic model representing the response containing substance information.

    Attributes
    ----------
    substances : list[Substance]
        A list of substances.
    substance_errors : list[Any] | None
        A list of errors related to substances, if any.
    """

    substances: list[SubstanceInfo]
    substance_errors: list[dict[str, Any]] | None = Field(None, alias="substanceErrors")
