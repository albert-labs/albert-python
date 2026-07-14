from typing import Any, Literal

from pydantic import ConfigDict, Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.types import MetadataItem


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

    model_config = ConfigDict(extra="allow")

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
    is_cas : bool
        Whether the substance is a known regulatory CAS record. ``False``
        indicates an auto-created or trade-secret placeholder.
    metadata : dict[str, Any] | None
        Tenant custom metadata. Scalar fields are plain strings or numbers.
        List-type fields return a list of ``MetadataItem`` objects
        with ``name`` and ``id``.
    notes : str | None
        Free-text notes for the substance.
    description : str | None
        A description of the substance.
    cas_smiles : str | None
        The SMILES string for the substance.
    inchi_key : str | None
        The InChI key for the substance.
    iupac_name : str | None
        The IUPAC name for the substance.
    cactus_status : str | None
        The Cactus status for the substance.
    acute_dermal_tox_info : list[dict] | None
        Acute dermal toxicity information.
    acute_inhalation_tox_info : list[dict] | None
        Acute inhalation toxicity information.
    acute_oral_tox_info : list[dict] | None
        Acute oral toxicity information.
    acute_tox_info : list[dict] | None
        General acute toxicity information.
    chronic_tox_info : list[dict] | None
        Chronic toxicity information.
    aspiration_tox_info : list[dict] | None
        Aspiration toxicity information.
    neuro_tox_info : list[dict] | None
        Neurotoxicity information.
    reproductive_tox_info : list[dict] | None
        Reproductive toxicity information.
    carcinogen_info : list[dict] | None
        Carcinogenicity information.
    germ_cell_mutagen_info : list[dict] | None
        Germ cell mutagenicity information.
    skin_corrosion_info : list[dict] | None
        Skin corrosion information.
    serious_eye_damage_info : list[dict] | None
        Serious eye damage information.
    respiratory_skin_sens_info : list[dict] | None
        Respiratory and skin sensitization information.
    stot_info : list[dict] | None
        Specific target organ toxicity information.
    stot_affected_organs : str | None
        Organs affected by specific target organ toxicity.
    stot_route_of_exposure : str | None
        Route of exposure for specific target organ toxicity.
    boilingpoint_info : list[dict] | None
        Boiling point information.
    flashpoint_info : list[dict] | None
        Flash point information.
    molecular_weight : list[dict] | None
        Molecular weight information.
    bio_accumulative_info : list[dict] | None
        Bioaccumulation information.
    degradability_info : list[dict] | None
        Degradability information.
    soil_mobility_info : list[dict] | None
        Soil mobility information.
    peroxide_function_groups : int | None
        Number of peroxide function groups.
    structures : list[dict] | None
        Chemical structure representations.
    oel_info : list[dict] | None
        Occupational exposure limit information.
    bei_info : list[dict] | None
        Biological exposure index information.
    dnel_info : list[dict] | None
        Derived no-effect level information.
    m_factor : int | None
        Acute toxicity M-factor.
    m_factor_chronic : int | None
        Chronic toxicity M-factor.
    specific_conc_eu : list[dict] | None
        EU-specific concentration limits.
    specific_conc_source : str | None
        Source of specific concentration limit information.
    aicis_notified : bool | None
        Whether the substance is AICIS notified.
    iecsc_notified : bool | None
        Whether the substance is IECSC notified.
    jpencs_notified : bool | None
        Whether the substance is JPENCS notified.
    jpishl_notified : bool | None
        Whether the substance is JPISHL notified.
    koecl_notified : bool | None
        Whether the substance is KOECL notified.
    nzioc_notified : bool | None
        Whether the substance is NZIOC notified.
    piccs_notified : bool | None
        Whether the substance is PICCS notified.
    tcsi_notified : bool | None
        Whether the substance is TCSI notified.
    vinic_notified : bool | None
        Whether the substance is VINIC notified.
    encs_notified_list : dict[str, Any] | None
        ENCS notification details.
    ishl_notified_list : dict[str, Any] | None
        ISHL notification details.
    ec_notified : str | None
        EC notification status.
    canada_inventory_status : str | None
        Canadian inventory status.
    trade_secret : bool | None
        Whether the substance is a trade secret.
    eu_annex14_substances_list : bool | None
        Whether the substance is on the EU Annex XIV list.
    eu_annex17_restrictions_list : bool | None
        Whether the substance is on the EU Annex XVII restrictions list.
    eu_annex17_substances_list : bool | None
        Whether the substance is on the EU Annex XVII substances list.
    eu_candidate_list : bool | None
        Whether the substance is on the EU SVHC candidate list.
    eu_dang_chem_annex1_part1_list : bool | None
        Whether the substance is on the EU dangerous chemicals Annex 1 Part 1 list.
    eu_dang_chem_annex1_part2_list : bool | None
        Whether the substance is on the EU dangerous chemicals Annex 1 Part 2 list.
    eu_dang_chem_annex1_part3_list : bool | None
        Whether the substance is on the EU dangerous chemicals Annex 1 Part 3 list.
    eu_dang_chem_annex5_list : bool | None
        Whether the substance is on the EU dangerous chemicals Annex 5 list.
    eu_directive_ec_list : bool | None
        Whether the substance is on the EU directive EC list.
    eu_explosive_precursors_annex1_list : bool | None
        Whether the substance is on the EU explosive precursors Annex 1 list.
    eu_explosive_precursors_annex2_list : bool | None
        Whether the substance is on the EU explosive precursors Annex 2 list.
    eu_ozone_depletion_list : bool | None
        Whether the substance is on the EU ozone depletion list.
    eu_pollutant_annex2_list : bool | None
        Whether the substance is on the EU pollutant Annex 2 list.
    eu_pop_list : bool | None
        Whether the substance is on the EU POP list.
    caa_cfr40 : bool | None
        Whether the substance is listed under CAA CFR 40.
    caa_hpa : bool | None
        Whether the substance is listed under CAA HPA.
    massachusetts_rtk : bool | None
        Whether the substance is on the Massachusetts RTK list.
    new_jersey_rtk : bool | None
        Whether the substance is on the New Jersey RTK list.
    new_york_rtk : bool | None
        Whether the substance is on the New York RTK list.
    pennsylvania_rtk : bool | None
        Whether the substance is on the Pennsylvania RTK list.
    rhode_island_rtk : bool | None
        Whether the substance is on the Rhode Island RTK list.
    sdwa : bool | None
        Whether the substance is listed under the SDWA.
    tsca8b : bool | None
        Whether the substance is listed under TSCA 8(b).
    pcr_regulated : bool | None
        Whether the substance is PCR regulated.
    pdscl : str | None
        PDSCL classification.
    prtr : str | None
        PRTR classification.
    page_number : int | None
        Reference page number.
    cn_csdc_regulations : bool | None
        Whether the substance is subject to CN CSDC regulations.
    cn_pcod_list : bool | None
        Whether the substance is on the CN PCOD list.
    cn_priority_list : bool | None
        Whether the substance is on the CN priority list.
    tw_ghs_clas_list : bool | None
        Whether the substance is on the Taiwan GHS classification list.
    tw_handle_priority_chem : bool | None
        Whether the substance is a Taiwan priority chemical.
    tw_handle_toxic_chem : bool | None
        Whether the substance is a Taiwan toxic chemical.
    tw_ind_waste_standards : bool | None
        Whether the substance is subject to Taiwan industrial waste standards.
    basel_conv_list : bool | None
        Whether the substance is on the Basel Convention list.
    rotterdam_conv_list : bool | None
        Whether the substance is on the Rotterdam Convention list.
    stockholm_conv_list : bool | None
        Whether the substance is on the Stockholm Convention list.
    kyoto_protocol : bool | None
        Whether the substance is subject to the Kyoto Protocol.
    montreal_protocol : bool | None
        Whether the substance is subject to the Montreal Protocol.
    green_gas_list : bool | None
        Whether the substance is on the green gas list.
    export_control_list_phrases : bool | None
        Whether the substance has export control list phrases.
    cdsa_list : bool | None
        Whether the substance is on the CDSA list.
    chemical_category : list[str] | None
        Chemical categories for the substance.
    custom_phrases : list[dict] | None
        Custom phrases for the substance.
    substance_phrases : list[dict] | None
        Substance phrases.
    sustainability_status_lbc : str | None
        Living Building Challenge sustainability status.
    approved_legal_entities : Any | None
        Approved legal entities for the substance.
    pictograms : list[dict] | None
        GHS hazard pictograms.
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
    is_cas: bool = Field(default=True, alias="isCas")
    metadata: dict[str, Any] | None = None
    notes: str | None = None
    description: str | None = None
    cas_smiles: str | None = Field(None, alias="casSmiles")
    inchi_key: str | None = Field(None, alias="inchiKey")
    iupac_name: str | None = Field(None, alias="iUpacName")
    cactus_status: str | None = Field(None, alias="cactusStatus")
    acute_dermal_tox_info: list[dict] | None = Field(None, alias="acuteDermalToxInfo")
    acute_inhalation_tox_info: list[dict] | None = Field(None, alias="acuteInhalationToxInfo")
    acute_oral_tox_info: list[dict] | None = Field(None, alias="acuteOralToxInfo")
    acute_tox_info: list[dict] | None = Field(None, alias="acuteToxInfo")
    chronic_tox_info: list[dict] | None = Field(None, alias="chronicToxInfo")
    aspiration_tox_info: list[dict] | None = Field(None, alias="aspirationToxInfo")
    neuro_tox_info: list[dict] | None = Field(None, alias="neuroToxInfo")
    reproductive_tox_info: list[dict] | None = Field(None, alias="reproductiveToxInfo")
    carcinogen_info: list[dict] | None = Field(None, alias="carcinogenInfo")
    germ_cell_mutagen_info: list[dict] | None = Field(None, alias="germCellMutagenInfo")
    skin_corrosion_info: list[dict] | None = Field(None, alias="skinCorrosionInfo")
    serious_eye_damage_info: list[dict] | None = Field(None, alias="seriousEyeDamageInfo")
    respiratory_skin_sens_info: list[dict] | None = Field(None, alias="respiratorySkinSensInfo")
    stot_info: list[dict] | None = Field(None, alias="stotInfo")
    stot_affected_organs: str | None = Field(None, alias="stotAffectedOrgans")
    stot_route_of_exposure: str | None = Field(None, alias="stotRouteOfExposure")
    boilingpoint_info: list[dict] | None = Field(None, alias="boilingpointInfo")
    flashpoint_info: list[dict] | None = Field(None, alias="flashpointInfo")
    molecular_weight: list[dict] | None = Field(None, alias="molecularWeight")
    bio_accumulative_info: list[dict] | None = Field(None, alias="bioAccumulativeInfo")
    degradability_info: list[dict] | None = Field(None, alias="degradabilityInfo")
    soil_mobility_info: list[dict] | None = Field(None, alias="soilMobilityInfo")
    peroxide_function_groups: int | None = Field(None, alias="peroxideFunctionGroups")
    structures: list[dict] | None = None
    oel_info: list[dict] | None = Field(None, alias="oelInfo")
    bei_info: list[dict] | None = Field(None, alias="beiInfo")
    dnel_info: list[dict] | None = Field(None, alias="dnelInfo")
    m_factor: int | None = Field(None, alias="mFactor")
    m_factor_chronic: int | None = Field(None, alias="mFactorChronic")
    specific_conc_eu: list[dict] | None = Field(None, alias="specificConcEU")
    specific_conc_source: str | None = Field(None, alias="specificConcSource")
    aicis_notified: bool | None = Field(None, alias="aicisNotified")
    iecsc_notified: bool | None = Field(None, alias="iecscNotified")
    jpencs_notified: bool | None = Field(None, alias="jpencsNotified")
    jpishl_notified: bool | None = Field(None, alias="jpishlNotified")
    koecl_notified: bool | None = Field(None, alias="koeclNotified")
    nzioc_notified: bool | None = Field(None, alias="nziocNotified")
    piccs_notified: bool | None = Field(None, alias="piccsNotified")
    tcsi_notified: bool | None = Field(None, alias="tcsiNotified")
    vinic_notified: bool | None = Field(None, alias="vinicNotified")
    encs_notified_list: dict[str, Any] | None = Field(None, alias="encsNotifiedList")
    ishl_notified_list: dict[str, Any] | None = Field(None, alias="ishlNotifiedList")
    ec_notified: str | None = Field(None, alias="ecNotified")
    canada_inventory_status: str | None = Field(None, alias="canadaInventoryStatus")
    trade_secret: bool | None = Field(None, alias="tradeSecret")
    eu_annex14_substances_list: bool | None = Field(None, alias="euAnnex14SubstancesList")
    eu_annex17_restrictions_list: bool | None = Field(None, alias="euAnnex17RestrictionsList")
    eu_annex17_substances_list: bool | None = Field(None, alias="euAnnex17SubstancesList")
    eu_candidate_list: bool | None = Field(None, alias="euCandidateList")
    eu_dang_chem_annex1_part1_list: bool | None = Field(None, alias="euDangChemAnnex1Part1List")
    eu_dang_chem_annex1_part2_list: bool | None = Field(None, alias="euDangChemAnnex1Part2List")
    eu_dang_chem_annex1_part3_list: bool | None = Field(None, alias="euDangChemAnnex1Part3List")
    eu_dang_chem_annex5_list: bool | None = Field(None, alias="euDangChemAnnex5List")
    eu_directive_ec_list: bool | None = Field(None, alias="euDirectiveEcList")
    eu_explosive_precursors_annex1_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex1List"
    )
    eu_explosive_precursors_annex2_list: bool | None = Field(
        None, alias="euExplosivePrecursorsAnnex2List"
    )
    eu_ozone_depletion_list: bool | None = Field(None, alias="euOzoneDepletionList")
    eu_pollutant_annex2_list: bool | None = Field(None, alias="euPollutantAnnex2List")
    eu_pop_list: bool | None = Field(None, alias="euPopList")
    caa_cfr40: bool | None = Field(None, alias="caaCFR40")
    caa_hpa: bool | None = Field(None, alias="caaHPA")
    massachusetts_rtk: bool | None = Field(None, alias="massachusettsRTK")
    new_jersey_rtk: bool | None = Field(None, alias="newJerseyRTK")
    new_york_rtk: bool | None = Field(None, alias="newYorkRTK")
    pennsylvania_rtk: bool | None = Field(None, alias="pennsylvaniaRTK")
    rhode_island_rtk: bool | None = Field(None, alias="rhodeIslandRTK")
    sdwa: bool | None = None
    tsca8b: bool | None = Field(None, alias="tsca8B")
    pcr_regulated: bool | None = Field(None, alias="pcrRegulated")
    pdscl: str | None = None
    prtr: str | None = None
    page_number: int | None = Field(None, alias="pageNumber")
    cn_csdc_regulations: bool | None = Field(None, alias="cnCSDCRegulations")
    cn_pcod_list: bool | None = Field(None, alias="cnPCODList")
    cn_priority_list: bool | None = Field(None, alias="cnPriorityList")
    tw_ghs_clas_list: bool | None = Field(None, alias="twGHSClasList")
    tw_handle_priority_chem: bool | None = Field(None, alias="twHandlePriorityChem")
    tw_handle_toxic_chem: bool | None = Field(None, alias="twHandleToxicChem")
    tw_ind_waste_standards: bool | None = Field(None, alias="twIndWasteStandards")
    basel_conv_list: bool | None = Field(None, alias="baselConvList")
    rotterdam_conv_list: bool | None = Field(None, alias="rotterdamConvList")
    stockholm_conv_list: bool | None = Field(None, alias="stockholmConvList")
    kyoto_protocol: bool | None = Field(None, alias="kyotoProtocol")
    montreal_protocol: bool | None = Field(None, alias="montrealProtocol")
    green_gas_list: bool | None = Field(None, alias="greenGasList")
    export_control_list_phrases: bool | None = Field(None, alias="exportControlListPhrases")
    cdsa_list: bool | None = Field(None, alias="cdsaList")
    chemical_category: list[str] | None = Field(None, alias="chemicalCategory")
    custom_phrases: list[dict] | None = Field(None, alias="customPhrases")
    substance_phrases: list[dict] | None = Field(None, alias="substancePhrases")
    sustainability_status_lbc: str | None = Field(None, alias="sustainabilityStatusLBC")
    approved_legal_entities: Any | None = Field(None, alias="approvedLegalEntities")
    pictograms: list[dict] | None = None


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
    notes : str | None
        Free-text notes for the substance.
    description : str | None
        A description of the substance.
    cas_smiles : str | None
        The SMILES string for the substance.
    inchi_key : str | None
        The InChI key for the substance.
    iupac_name : str | None
        The IUPAC name for the substance.
    cactus_status : str | None
        The Cactus status for the substance.
    metadata : dict[str, MetadataItem] | None
        Custom tenant metadata. Scalar fields take a plain string. Single-select
        list fields take a bare list ID string (e.g. ``"LST1253"``). Multi-select
        List-type fields take an ``EntityLink`` or ``list[EntityLink]``.
    """

    identifiers: list[SubstanceV4Identifier]
    attributes: list[SubstanceV4Attribute]
    substance_id: str | None = Field(None, alias="substanceId")
    is_global_record: bool = Field(True, alias="isGlobalRecord")
    category: str | None = None
    notes: str | None = None
    description: str | None = None
    cas_smiles: str | None = Field(None, alias="casSmiles")
    inchi_key: str | None = Field(None, alias="inchiKey")
    iupac_name: str | None = Field(None, alias="iUpacName")
    cactus_status: str | None = Field(None, alias="cactusStatus")
    metadata: dict[str, MetadataItem] | None = Field(None, alias="Metadata")


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
    inchi_key : str | None
        The InChI key for the substance.
    iupac_name : str | None
        The IUPAC name for the substance.
    cactus_status : str | None
        The Cactus status for the substance.
    metadata : dict[str, MetadataItem] | None
        Custom tenant metadata. Scalar fields take a plain string. Single-select
        list fields take a bare list ID string (e.g. ``"LST1253"``). Multi-select
        list fields take a list of ``MetadataItem`` objects with ``id``
        and ``value``.
    """

    notes: str | None = None
    description: str | None = None
    cas_smiles: str | None = Field(None, alias="casSmiles")
    inchi_key: str | None = Field(None, alias="inchiKey")
    iupac_name: str | None = Field(None, alias="iUpacName")
    cactus_status: str | None = Field(None, alias="cactusStatus")
    metadata: dict[str, MetadataItem] | None = None
