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

    number: str | None = None
    """Duplicate of the CAS number as the API returns it under a separate ``number`` key."""

    ec_list_no: str | None = Field(None, alias="ecListNo")
    """The EC list number."""

    index_no: str | None = Field(None, alias="indexNo")
    """The index number."""

    name: list[dict] | None = None
    """The substance name in one or more languages."""

    hazards: list[dict] | None = None
    """Hazard classifications."""

    wgk: str | None = Field(None, alias="WGK")
    """Water hazard class (WGK).

    Only returned when the request is scoped to the German region
    (``region="DE"``); other regions omit it."""

    has_ods: bool | None = Field(None, alias="hasODS")
    """Whether the substance is classified as an ozone-depleting substance (ODS), as recorded for the German (DE) region.

    Only returned for ``region="DE"``; other regions omit it."""

    has_pic: bool | None = Field(None, alias="hasPIC")
    """Whether the substance is subject to the Rotterdam Convention Prior Informed Consent (PIC) procedure, as recorded for the German (DE) region.

    Only returned for ``region="DE"``; other regions omit it."""

    has_pop: bool | None = Field(None, alias="hasPOP")
    """Whether the substance is a Stockholm Convention persistent organic pollutant (POP), as recorded for the German (DE) region.

    Only returned for ``region="DE"``; other regions omit it."""

    rsl: dict[str, Any] | None = None
    """Restricted Substances List (RSL) classification details, as recorded for the German (DE) region.

    Only returned for ``region="DE"``; other regions omit it."""

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

    exposure_controls_other: list[Any] | None = Field(None, alias="exposureControlsOther")
    """Other US exposure control measures not captured by the ACGIH, OSHA, AIHA or NIOSH fields.

    Only returned for ``region="US"``; other regions omit it."""

    exposure_controls_others: list[dict[str, Any]] | None = Field(
        None, alias="exposureControlsOthers"
    )
    """Other exposure control limits, with keys ``regList``, ``type``, ``unit`` and ``value``.

    Only returned for ``region="EU"`` and ``region="JP"``; other regions omit it."""

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

    additional_information: list[Any] | None = Field(None, alias="additionalInformation")
    """Additional free-form regulatory information entries.

    Only returned for ``region="EU"`` and ``region="JP"``; other regions omit it."""

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

    pbt_info: list[Any] | None = Field(None, alias="pbtInfo")
    """Persistent, bioaccumulative and toxic (PBT) substance assessment entries.

    Only returned for ``region="EU"`` and ``region="JP"``; other regions omit it."""

    pnec_info: list[dict[str, Any]] | None = Field(None, alias="pnecInfo")
    """Predicted no-effect concentration (PNEC) entries, with keys ``envCompartment``, ``unit`` and ``value``.

    Only returned for ``region="EU"`` and ``region="JP"``; other regions omit it."""

    soil_mobility_info: list[dict] | None = Field(None, alias="soilMobilityInfo")
    """Soil mobility information."""

    peroxide_function_groups: int | None = Field(None, alias="peroxideFunctionGroups")
    """Number of peroxide function groups."""

    structures: list[dict] | None = None
    """Chemical structure representations."""

    oel_info: list[dict] | None = Field(None, alias="oelInfo")
    """Occupational exposure limit information."""

    eu_indicative_oelvs: dict[str, Any] | None = Field(None, alias="euIndicativeOelvs")
    """EU indicative occupational exposure limit values (OELVs) table, with keys ``Expressed_As``, ``Long-term_Exposure_Limit_(LTEL)_Values_-_LTEL_(mg/m³)``, ``Long-term_Exposure_Limit_(LTEL)_Values_-_LTEL_(ppm)``, ``Miscellaneous_Notes`` and ``Physical_form``.

    Returned for every region."""

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

    eu_allergenic_fragrances_toys: Any | None = Field(None, alias="euAllergenicFragrancesToys")
    """EU allergenic fragrances in toys and childcare articles restriction entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_allowed_colorants_cosmetics: Any | None = Field(None, alias="euAllowedColorantsCosmetics")
    """EU allowed colorants in cosmetics entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_allowed_uv_filters_cosmetics: list[dict[str, Any]] | None = Field(
        None, alias="euAllowedUvFiltersCosmetics"
    )
    """EU allowed UV filters in cosmetics table, with keys ``Common_Ingredients``, ``Expressed_As``, ``Function(s)``, ``Maximum_Threshold`` and ``Notes``.

    Returned for every region."""

    eu_assessment_regulatory_needs_substance: Any | None = Field(
        None, alias="euAssessmentRegulatoryNeedsSubstance"
    )
    """EU assessment of regulatory needs for the substance entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_banned_restricted_mercury_compounds: Any | None = Field(
        None, alias="euBannedRestrictedMercuryCompounds"
    )
    """EU banned or restricted mercury compounds entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_detergents_content_labelling: dict[str, Any] | None = Field(
        None, alias="euDetergentsContentLabelling"
    )
    """EU Detergents Regulation content labelling threshold, with key ``Cut_off_(%)``.

    Returned for every region."""

    eu_drug_precursors_category_1: dict[str, Any] | None = Field(
        None, alias="euDrugPrecursorsCategory1"
    )
    """EU drug precursors Category 1 (Regulation 273/2004) entry, with keys ``CN_Code``, ``CN_Designation``, ``Category``, ``Description`` and ``Group``.

    Returned for every region."""

    eu_drug_precursors_category_2: Any | None = Field(None, alias="euDrugPrecursorsCategory2")
    """EU drug precursors Category 2 entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_flammable_contents_aerosols: list[dict[str, Any]] | None = Field(
        None, alias="euFlammableContentsAerosols"
    )
    """EU Aerosol Dispensers Directive flammable contents table, with keys ``Classifications``, ``Index``, ``Physical_form`` and ``Substance_Description``.

    Returned for every region."""

    eu_haz_substances_active_implantable_medical_devices: Any | None = Field(
        None, alias="euHazSubstancesActiveImplantableMedicalDevices"
    )
    """EU hazardous substances in active implantable medical devices entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_ippc_polluting_substances: list[dict[str, Any]] | None = Field(
        None, alias="euIppcPollutingSubstances"
    )
    """EU Integrated Pollution Prevention and Control (IPPC) polluting substances table, with keys ``Air``, ``Annex_X_of_Dir_2000/60/EC``, ``Table_name`` and ``Water``.

    Returned for every region."""

    eu_no_longer_polymers_list: Any | None = Field(None, alias="euNoLongerPolymersList")
    """EU list of substances no longer considered polymers entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_potential_pbt_vpvb_substances: dict[str, Any] | None = Field(
        None, alias="euPotentialPbtVpvbSubstances"
    )
    """EU potential PBT/vPvB (persistent, bioaccumulative, toxic / very persistent, very bioaccumulative) substances entry, with keys ``Conclusion``, ``Fact_Sheet``, ``List_Number`` and ``Rapporteur``.

    Returned for every region."""

    eu_pppr_not_accepted_coformulants: dict[str, Any] | None = Field(
        None, alias="euPpprNotAcceptedCoformulants"
    )
    """EU Plant Protection Products Regulation (PPPR) not-accepted co-formulants entry, with key ``Classification/Other_Properties``.

    Returned for every region."""

    eu_priority_substances_additional_testing_reqs: list[dict[str, Any]] | None = Field(
        None, alias="euPrioritySubstancesAdditionalTestingReqs"
    )
    """EU Water Framework Directive priority substances additional testing requirements table, with keys ``Rapporteur``, ``Testing/information_requirements`` and ``Time_limit_from_the_date_of_entry_into_force_of_this_Regulation``.

    Returned for every region."""

    eu_priority_substances_water_policy: dict[str, Any] | None = Field(
        None, alias="euPrioritySubstancesWaterPolicy"
    )
    """EU priority substances in the field of water policy entry, with keys ``Identified_as_Priority_Hazardous_Substance`` and ``Number``.

    Returned for every region."""

    eu_reach_current_testing_proposals: Any | None = Field(
        None, alias="euReachCurrentTestingProposals"
    )
    """EU REACH current testing proposals entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_reach_dossier_evaluation_status: Any | None = Field(
        None, alias="euReachDossierEvaluationStatus"
    )
    """EU REACH dossier evaluation status entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    eu_reach_pre_registered_substances: dict[str, Any] | None = Field(
        None, alias="euReachPreRegisteredSubstances"
    )
    """EU REACH pre-registered substances entry, with keys ``Description``, ``Envisaged_registration_deadline``, ``Related_substances`` and ``Table_name``.

    Returned for every region."""

    eu_reach_previous_testing_proposals: list[dict[str, Any]] | None = Field(
        None, alias="euReachPreviousTestingProposals"
    )
    """EU REACH previous testing proposals table, with keys ``Alternatives_to_vertebrate_testing``, ``Date_of_publication_to_call_for_available_information``, ``Deadline_for_submitting_information``, ``ECHA_response_to_3rd_party_contributions`` and ``Hazard_endpoint_for_which_vertebrate_testing_was_proposed``.

    Returned for every region."""

    eu_reach_svhc_annex_xiv: dict[str, Any] | None = Field(None, alias="euReachSvhcAnnexXIV")
    """EU REACH SVHC Annex XIV (authorisation list) entry, with keys ``Date_of_inclusion``, ``Decision``, ``Description``, ``IUCLID_dataset`` and ``Reason_for_inclusion``.

    Returned for every region."""

    eu_reach_universe_registered_substances: dict[str, Any] | None = Field(
        None, alias="euReachUniverseRegisteredSubstances"
    )
    """EU REACH universe of registered substances entry, with keys ``Brief_Profile_URL``, ``Highest_registered_tonnage``, ``Infocard_URL``, ``Position_in_the_chemical_universe`` and ``REACH_Factsheet(s)_URL``.

    Returned for every region."""

    svhc: bool | None = None
    """Whether the substance is on the EU REACH SVHC candidate list (explicit ``False`` means verified non-membership; ``None`` means not provided).

    Only returned for ``region="EU"`` and ``region="JP"``; other regions omit it."""

    eaeu_pops_prohibited_import_export: dict[str, Any] | None = Field(
        None, alias="eaeuPopsProhibitedImportExport"
    )
    """Eurasian Economic Union (EAEU) persistent organic pollutants prohibited from import/export, with key ``EAEU_HS_Code``.

    Returned for every region."""

    classification_and_label_inventory_status: list[Any] | None = Field(
        None, alias="classificationAndLabelInventoryStatus"
    )
    """EU CLP Classification and Labelling (C&L) Inventory notification status entries.

    Only returned for ``region="DE"``; other regions omit it."""

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

    california_prop_65: list[str] | None = Field(None, alias="californiaProp65")
    """California Proposition 65 list entries the substance appears on.

    Only returned for ``region="US"``; other regions omit it."""

    cercla_rq: float | None = Field(None, alias="cerclaRQ")
    """CERCLA (Superfund) reportable quantity (RQ), in pounds.

    Only returned for ``region="US"``; other regions omit it."""

    cfr_marine_pollutant: dict[str, Any] | None = Field(None, alias="CFRmarinePollutant")
    """US DOT 49 CFR marine pollutant designation, with keys ``note``, ``noteCode`` and ``noteField``.

    Only returned for ``region="US"``; other regions omit it."""

    cfr_reportable_quantity: dict[str, Any] | None = Field(None, alias="CFRreportableQuantity")
    """US CFR reportable quantity threshold, with keys ``maxValue`` and ``unit``.

    Only returned for ``region="US"``; other regions omit it."""

    rohs_concentration: float | None = Field(None, alias="rohsConcentration")
    """EU RoHS Directive maximum concentration threshold (percent by weight).

    Only returned for ``region="EU"`` and ``region="JP"``; other regions omit it."""

    sara_302: bool | None = Field(None, alias="sara302")
    """Whether the substance is an EPCRA (SARA Title III) Section 302 extremely hazardous substance (explicit ``False`` means verified non-membership; ``None`` means not provided).

    Only returned for ``region="US"``; other regions omit it."""

    sara_313_concentration_limit: float | None = Field(None, alias="sara313ConcentrationLimit")
    """EPCRA (SARA Title III) Section 313 de minimis concentration limit (percent).

    Only returned for ``region="US"``; other regions omit it."""

    snur: bool | None = None
    """Whether the substance is subject to a TSCA Significant New Use Rule (SNUR) (explicit ``False`` means verified non-membership; ``None`` means not provided).

    Only returned for ``region="US"``; other regions omit it."""

    snur_cfr: str | None = None
    """The CFR citation for the substance's TSCA Significant New Use Rule (SNUR).

    Only returned for ``region="US"``; other regions omit it."""

    tsca_12b_concentration_limit: float | None = Field(None, alias="tsca12BConcentrationLimit")
    """TSCA Section 12(b) export notification concentration limit (percent).

    Only returned for ``region="US"``; other regions omit it."""

    tsca_12b_regulated: bool | None = Field(None, alias="tsca12BRegulated")
    """Whether the substance is regulated under TSCA Section 12(b) (export notification) (explicit ``False`` means verified non-membership; ``None`` means not provided).

    Only returned for ``region="US"``; other regions omit it."""

    lve: bool | None = None
    """Whether the substance qualifies as a TSCA Low Volume Exemption (LVE) substance (explicit ``False`` means verified non-membership; ``None`` means not provided).

    Only returned for ``region="US"``; other regions omit it."""

    pdscl: dict | None = None
    """PDSCL classification, with keys ``maxValue`` and ``unit``.

    Returned when the request is scoped to the Japanese region (``region="JP"``)."""

    prtr: dict | None = None
    """PRTR classification, with keys ``className``, ``controlNumber``, ``maxValue`` and ``unit``.

    Returned when the request is scoped to the Japanese region (``region="JP"``)."""

    jp_chemical_weapons: dict[str, Any] | None = Field(None, alias="jpChemicalWeapons")
    """Japan Chemical Weapons Prohibition Act listing, with key ``No-Hyperlink``.

    Returned for every region."""

    jp_cscl_biodegradation_bioconcentration_ecs: list[dict[str, Any]] | None = Field(
        None, alias="jpCsclBiodegradationBioconcentrationECS"
    )
    """Japan CSCL (Chemical Substances Control Law) biodegradation and bioconcentration test data (ECS), with keys ``Data``, ``Database_name``, ``Duration``, ``Elimination_phase_duration`` and ``Endpoint``.

    Returned for every region."""

    jp_cscl_class_i_specified_substances: dict[str, Any] | None = Field(
        None, alias="jpCsclClassISpecifiedSubstances"
    )
    """Japan CSCL Class I Specified Chemical Substances entry, with keys ``Cabinet_Order_No``, ``Chemical_Substance_Name``, ``Class_I_Specified_Chemical_Substance_Name`` and ``MITI_Number``.

    Returned for every region."""

    jp_cscl_class_ii_specified_substances: dict[str, Any] | None = Field(
        None, alias="jpCsclClassIISpecifiedSubstances"
    )
    """Japan CSCL Class II Specified Chemical Substances entry, with keys ``class_Ⅱ_specified_chemical_substance_name``, ``miti_number`` and ``no``.

    Returned for every region."""

    jp_cscl_monitoring_chemical_substances: Any | None = Field(
        None, alias="jpCsclMonitoringChemicalSubstances"
    )
    """Japan CSCL monitoring chemical substances entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    jp_designated_hazardous_substances_soil_pollution_control_law: dict[str, Any] | None = Field(
        None, alias="jpDesignatedHazardousSubstancesSoilPollutionControlLaw"
    )
    """Japan Soil Pollution Control Law designated hazardous substances entry, with key ``No-Hyperlink``.

    Returned for every region."""

    jp_encs_type_ii_monitoring_substances: dict[str, Any] | None = Field(
        None, alias="jpEncsTypeIIMonitoringSubstances"
    )
    """Japan ENCS Type II Monitoring Substances entry, with keys ``Chemical_Substance_Name``, ``Classification``, ``Info_Link``, ``MITI_Number`` and ``Number``.

    Returned for every region."""

    jp_encs_type_iii_monitoring_substances: dict[str, Any] | None = Field(
        None, alias="jpEncsTypeIIIMonitoringSubstances"
    )
    """Japan ENCS Type III Monitoring Substances entry, with keys ``Chemical_Substance_Name``, ``MITI_Number``, ``Number``, ``Registration_Number`` and ``Source_Link``.

    Returned for every region."""

    jp_explosives_control_law_list: dict[str, Any] | None = Field(
        None, alias="jpExplosivesControlLawList"
    )
    """Japan Explosives Control Law listing, with keys ``CHRIP_ID``, ``Chemical_Substance_Name`` and ``No-Hyperlink``.

    Returned for every region."""

    jp_harmful_substances_in_household_products: dict[str, Any] | None = Field(
        None, alias="jpHarmfulSubstancesInHouseholdProducts"
    )
    """Japan Act on Control of Household Products Containing Harmful Substances listing, with key ``No-Hyperlink``.

    Returned for every region."""

    jp_ishl_dangerous_substances_explosives: dict[str, Any] | None = Field(
        None, alias="jpIshlDangerousSubstancesExplosives"
    )
    """Japan ISHL dangerous substances (explosives) listing, with keys ``CHRIP_ID``, ``Chemical_Substance_Name`` and ``No-Hyperlink``.

    Returned for every region."""

    jp_ishl_dangerous_substances_flammable_fp_below_65: dict[str, Any] | None = Field(
        None, alias="jpIshlDangerousSubstancesFlammableFpBelow65"
    )
    """Japan ISHL dangerous substances (flammable, flash point below 65°C) listing, with keys ``CAS_Identity``, ``CHRIP_ID``, ``Chemical_Substance_Name`` and ``No-Hyperlink``.

    Returned for every region."""

    jp_ishl_dangerous_substances_flammable_gases: dict[str, Any] | None = Field(
        None, alias="jpIshlDangerousSubstancesFlammableGases"
    )
    """Japan ISHL dangerous substances (flammable gases) listing, with keys ``CHRIP_ID``, ``Chemical_Substance_Name`` and ``No-Hyperlink``.

    Returned for every region."""

    jp_ishl_dangerous_substances_ignitable: Any | None = Field(
        None, alias="jpIshlDangerousSubstancesIgnitable"
    )
    """Japan ISHL dangerous substances (ignitable) entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    jp_ishl_dangerous_substances_oxidizing: dict[str, Any] | None = Field(
        None, alias="jpIshlDangerousSubstancesOxidizing"
    )
    """Japan ISHL dangerous substances (oxidizing) listing, with keys ``CHRIP_ID``, ``Chemical_Substance_Name`` and ``No-Hyperlink``.

    Returned for every region."""

    jp_ishl_prohibited_substances: dict[str, Any] | None = Field(
        None, alias="jpIshlProhibitedSubstances"
    )
    """Japan ISHL prohibited substances listing, with key ``No-Hyperlink``.

    Returned for every region."""

    jp_ishl_substances_for_manufacturing_permit: dict[str, Any] | None = Field(
        None, alias="jpIshlSubstancesForManufacturingPermit"
    )
    """Japan ISHL substances requiring a manufacturing permit listing, with key ``No-Hyperlink``.

    Returned for every region."""

    jp_notification_exempted_general_chemicals: Any | None = Field(
        None, alias="jpNotificationExemptedGeneralChemicals"
    )
    """Japan notification-exempted general chemicals entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    jp_ods: dict[str, Any] | None = Field(None, alias="jpODS")
    """Japan ozone-depleting substances (ODS) listing, with keys ``CHRIP_ID``, ``Cabinet_Order_Name``, ``Cabinet_Order_Number_(Type_of_Substances)``, ``Category`` and ``Chemical_Substance_Name``.

    Returned for every region."""

    jp_oils_under_water_pollution_control_act: Any | None = Field(
        None, alias="jpOilsUnderWaterPollutionControlAct"
    )
    """Japan oils under the Water Pollution Control Act entry.

    Shape not yet observed in live responses (always ``null`` so far); typed as ``Any`` until confirmed."""

    jp_rotterdam_prior_informed_consent_procedure_substances: dict[str, Any] | None = Field(
        None, alias="jpRotterdamPriorInformedConsentProcedureSubstances"
    )
    """Japan Rotterdam Convention Prior Informed Consent (PIC) procedure substances entry, with keys ``Classification``, ``Subject to Stockholm Convention`` and ``Title``.

    Returned for every region."""

    jp_skin_and_eye_damaging_absorbing_substances_ppe_requirement: dict[str, Any] | None = Field(
        None, alias="jpSkinAndEyeDamagingAbsorbingSubstancesPpeRequirement"
    )
    """Japan ISHL skin/eye-damaging and absorbing substances personal protective equipment (PPE) requirement entry, with keys ``Cut-off value (weight percent) *8``, ``Effective date``, ``GHS Classification Name (Japan)``, ``Name under Industrial Safety and Health Act *2`` and ``Ordinance on Prevention of Specific Chemical Hazards, etc. *7``.

    Returned for every region."""

    jp_specified_air_pollutants_factories_business_sites: dict[str, Any] | None = Field(
        None, alias="jpSpecifiedAirPollutantsFactoriesBusinessSites"
    )
    """Japan specified air pollutants from factories and business sites listing, with key ``No-Hyperlink``.

    Returned for every region."""

    jp_specified_chemical_health_damage_prevention: dict[str, Any] | None = Field(
        None, alias="jpSpecifiedChemicalHealthDamagePrevention"
    )
    """Japan specified chemical substances health damage prevention listing, with keys ``Group`` and ``No-Hyperlink``.

    Returned for every region."""

    jp_water_pollution_control_act_designated_substances: dict[str, Any] | None = Field(
        None, alias="jpWaterPollutionContrloActDesignatedSubstances"
    )
    """Japan Water Pollution Control Act designated substances listing, with keys ``CHRIP_ID``, ``Chemical_Substance_Name`` and ``No-Hyperlink``.

    The wire key carries an upstream API typo (``Contrlo`` instead of ``Control``); preserved verbatim in the alias so payloads round-trip correctly.

    Returned for every region."""

    ishl_carcinogen: dict[str, Any] | None = Field(None, alias="ishlCarcinogen")
    """Japan ISHL Ordinance 39 carcinogen entry, with keys ``ghsCategory``, ``maxValue`` and ``unit``.

    Only returned for ``region="JP"``; other regions omit it."""

    ishl_cscl: dict[str, Any] | None = Field(None, alias="ishlCscl")
    """Japan ISHL CSCL classification entry, with key ``class2``.

    Only returned for ``region="JP"``; other regions omit it."""

    ishl_mutagens: dict[str, Any] | None = Field(None, alias="ishlMutagens")
    """Japan ISHL mutagens entry, with keys ``No-Hyperlink`` and ``newValue``.

    Only returned for ``region="JP"``; other regions omit it."""

    ishl_ordinance_39: dict[str, Any] | None = Field(None, alias="ishlOrdinance39")
    """Japan ISHL Ordinance 39 (notifiable substances) entry with keys ``group`` and ``maxValue``.

    Only returned for ``region="JP"``; other regions omit it."""

    ishl_organic_solvent: dict[str, Any] | None = Field(None, alias="ishlOrganicSolvent")
    """Japan ISHL organic solvent classification entry, with key ``class2``.

    Only returned for ``region="JP"``; other regions omit it."""

    ishl_required_list: dict[str, Any] | None = Field(None, alias="ishlRequiredList")
    """Japan ISHL required labeling/SDS list entry, with keys ``label`` and ``sds``.

    Only returned for ``region="JP"``; other regions omit it."""

    fire_service_law_list: dict[str, Any] | None = Field(None, alias="fireServiceLawList")
    """Japan Fire Service Law hazardous materials classification entry, with keys ``class4`` and ``designatedFlamSubstances``.

    Only returned for ``region="JP"``; other regions omit it."""

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
