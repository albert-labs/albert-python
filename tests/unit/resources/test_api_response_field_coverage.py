"""Guard that models keep the API response fields their consumers depend on.

``BaseAlbertModel`` does not set an ``extra`` policy, so Pydantic defaults to
``extra="ignore"`` and any field a model fails to declare is dropped at validation
and is not recoverable from ``model_extra``. These tests pin the fields that were
silently lost, using payload fragments recorded from the live API.
"""

import pytest

from albert.resources.product_design import (
    CasLevelSubstance,
    UnpackedCasInfo,
    UnpackedProductDesign,
)
from albert.resources.projects import Project, ProjectClass, TaskConfig
from albert.resources.substance import SubstanceInfo
from albert.resources.substance_v4 import SubstanceV4Info, SubstanceV4SearchItem

# Recorded from GET /api/v3/productdesign/DESIGN/unpack?formulaId=INVP603-004
CAS_LEVEL_SUBSTANCE_PAYLOAD = {
    "casPrimaryKeyId": "CAS39928",
    "casID": "68585-34-2",
    "amount": 0.24642857,
    "min": 0.19714286,
    "aggregatedFunc": [],
    "target": 0,
    "albertId": "INVA42942",
    "substanceId": "1f11f9e7-a897-6a80-9724-8f1c8e925e4b",
}


def test_cas_level_substance_keeps_substance_id():
    """The Regulatory DB key must survive validation, not be dropped as an extra."""
    substance = CasLevelSubstance.model_validate(CAS_LEVEL_SUBSTANCE_PAYLOAD)

    assert substance.substance_id == "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"
    assert substance.cas_id == "68585-34-2"
    assert substance.albert_id == "INVA42942"
    assert substance.min == pytest.approx(0.19714286)
    assert substance.target == pytest.approx(0)


def test_unpacked_product_design_exposes_substance_ids():
    """substance_id survives through the top-level unpack response model."""
    unpacked = UnpackedProductDesign.model_validate(
        {"casLevelSubstances": [CAS_LEVEL_SUBSTANCE_PAYLOAD]}
    )

    assert unpacked.cas_level_substances is not None
    assert unpacked.cas_level_substances[0].substance_id == (
        "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"
    )


def test_unpacked_cas_info_keeps_substance_id():
    cas_info = UnpackedCasInfo.model_validate(
        {"id": "CAS39928", "substanceId": "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"}
    )

    assert cas_info.substance_id == "1f11f9e7-a897-6a80-9724-8f1c8e925e4b"


def test_substance_v4_info_declares_wgk():
    """``SubstanceV4Info`` must expose WGK as a typed field, matching its search sibling.

    Only ``region="DE"`` returns the field; the models must agree on the attribute
    name so callers do not need to know which endpoint produced the record.
    """
    info = SubstanceV4Info.model_validate({"casID": "64-18-6", "WGK": "WGK 1"})
    search_item = SubstanceV4SearchItem.model_validate({"casID": "64-18-6", "WGK": "WGK 1"})

    assert info.wgk == "WGK 1"
    assert search_item.wgk == "WGK 1"


def test_substance_v4_info_wgk_absent_outside_german_region():
    """Regions other than DE omit WGK; the model must not invent a value."""
    info = SubstanceV4Info.model_validate({"casID": "64-18-6"})

    assert info.wgk is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pdscl", {"maxValue": 1, "unit": "%"}),
        (
            "prtr",
            {
                "className": "Specified Class 1,Class 1",
                "unit": "%",
                "controlNumber": 411,
                "maxValue": 0.1,
            },
        ),
    ],
)
def test_substance_v4_info_accepts_japanese_object_fields(field, value):
    """``region="JP"`` returns objects for these; typing them as ``str`` raised."""
    info = SubstanceV4Info.model_validate({"casID": "50-00-0", field: value})

    assert getattr(info, field) == value


_SUBSTANCE_V4_NEW_FIELDS: list[tuple[str, str, object]] = [
    ("additionalInformation", "additional_information", []),
    ("californiaProp65", "california_prop_65", ["California Proposition 65 (2024)"]),
    ("cerclaRQ", "cercla_rq", 0.1),
    (
        "CFRmarinePollutant",
        "cfr_marine_pollutant",
        {"note": "note_value", "noteCode": "noteCode_value", "noteField": "noteField_value"},
    ),
    (
        "CFRreportableQuantity",
        "cfr_reportable_quantity",
        {"maxValue": "maxValue_value", "unit": "unit_value"},
    ),
    ("classificationAndLabelInventoryStatus", "classification_and_label_inventory_status", []),
    (
        "eaeuPopsProhibitedImportExport",
        "eaeu_pops_prohibited_import_export",
        {"EAEU_HS_Code": "EAEU_HS_Code_value"},
    ),
    (
        "euAllergenicFragrancesToys",
        "eu_allergenic_fragrances_toys",
        {"placeholder": "not yet observed"},
    ),
    (
        "euAllowedColorantsCosmetics",
        "eu_allowed_colorants_cosmetics",
        {"placeholder": "not yet observed"},
    ),
    (
        "euAllowedUvFiltersCosmetics",
        "eu_allowed_uv_filters_cosmetics",
        [
            {
                "Common_Ingredients": "Common_Ingredients_value",
                "Expressed_As": "Expressed_As_value",
                "Function(s)": "Function(s)_value",
                "Maximum_Threshold": "Maximum_Threshold_value",
                "Notes": "Notes_value",
            }
        ],
    ),
    (
        "euAssessmentRegulatoryNeedsSubstance",
        "eu_assessment_regulatory_needs_substance",
        {"placeholder": "not yet observed"},
    ),
    (
        "euBannedRestrictedMercuryCompounds",
        "eu_banned_restricted_mercury_compounds",
        {"placeholder": "not yet observed"},
    ),
    (
        "euDetergentsContentLabelling",
        "eu_detergents_content_labelling",
        {"Cut_off_(%)": "Cut_off_(%)_value"},
    ),
    (
        "euDrugPrecursorsCategory1",
        "eu_drug_precursors_category_1",
        {
            "CN_Code": "CN_Code_value",
            "CN_Designation": "CN_Designation_value",
            "Category": "Category_value",
            "Description": "Description_value",
            "Group": "Group_value",
        },
    ),
    (
        "euDrugPrecursorsCategory2",
        "eu_drug_precursors_category_2",
        {"placeholder": "not yet observed"},
    ),
    (
        "euFlammableContentsAerosols",
        "eu_flammable_contents_aerosols",
        [
            {
                "Classifications": "Classifications_value",
                "Index": "Index_value",
                "Physical_form": "Physical_form_value",
                "Substance_Description": "Substance_Description_value",
            }
        ],
    ),
    (
        "euHazSubstancesActiveImplantableMedicalDevices",
        "eu_haz_substances_active_implantable_medical_devices",
        {"placeholder": "not yet observed"},
    ),
    (
        "euIndicativeOelvs",
        "eu_indicative_oelvs",
        {
            "Expressed_As": "Expressed_As_value",
            "Long-term_Exposure_Limit_(LTEL)_Values_-_LTEL_(mg/m³)": "Long-term_Exposure_Limit_(LTEL)_Values_-_LTEL_(mg/m³)_value",
            "Long-term_Exposure_Limit_(LTEL)_Values_-_LTEL_(ppm)": "Long-term_Exposure_Limit_(LTEL)_Values_-_LTEL_(ppm)_value",
            "Miscellaneous_Notes": "Miscellaneous_Notes_value",
            "Physical_form": "Physical_form_value",
        },
    ),
    (
        "euIppcPollutingSubstances",
        "eu_ippc_polluting_substances",
        [
            {
                "Air": "Air_value",
                "Annex_X_of_Dir_2000/60/EC": "Annex_X_of_Dir_2000/60/EC_value",
                "Table_name": "Table_name_value",
                "Water": "Water_value",
            }
        ],
    ),
    ("euNoLongerPolymersList", "eu_no_longer_polymers_list", {"placeholder": "not yet observed"}),
    (
        "euPotentialPbtVpvbSubstances",
        "eu_potential_pbt_vpvb_substances",
        {
            "Conclusion": "Conclusion_value",
            "Fact_Sheet": "Fact_Sheet_value",
            "List_Number": "List_Number_value",
            "Rapporteur": "Rapporteur_value",
        },
    ),
    (
        "euPpprNotAcceptedCoformulants",
        "eu_pppr_not_accepted_coformulants",
        {"Classification/Other_Properties": "Classification/Other_Properties_value"},
    ),
    (
        "euPrioritySubstancesAdditionalTestingReqs",
        "eu_priority_substances_additional_testing_reqs",
        [
            {
                "Rapporteur": "Rapporteur_value",
                "Testing/information_requirements": "Testing/information_requirements_value",
                "Time_limit_from_the_date_of_entry_into_force_of_this_Regulation": "Time_limit_from_the_date_of_entry_into_force_of_this_Regulation_value",
            }
        ],
    ),
    (
        "euPrioritySubstancesWaterPolicy",
        "eu_priority_substances_water_policy",
        {
            "Identified_as_Priority_Hazardous_Substance": "Identified_as_Priority_Hazardous_Substance_value",
            "Number": "Number_value",
        },
    ),
    (
        "euReachCurrentTestingProposals",
        "eu_reach_current_testing_proposals",
        {"placeholder": "not yet observed"},
    ),
    (
        "euReachDossierEvaluationStatus",
        "eu_reach_dossier_evaluation_status",
        {"placeholder": "not yet observed"},
    ),
    (
        "euReachPreRegisteredSubstances",
        "eu_reach_pre_registered_substances",
        {
            "Description": "Description_value",
            "Envisaged_registration_deadline": "Envisaged_registration_deadline_value",
            "Related_substances": "Related_substances_value",
            "Table_name": "Table_name_value",
        },
    ),
    (
        "euReachPreviousTestingProposals",
        "eu_reach_previous_testing_proposals",
        [
            {
                "Alternatives_to_vertebrate_testing": "Alternatives_to_vertebrate_testing_value",
                "Date_of_publication_to_call_for_available_information": "Date_of_publication_to_call_for_available_information_value",
                "Deadline_for_submitting_information": "Deadline_for_submitting_information_value",
                "ECHA_response_to_3rd_party_contributions": "ECHA_response_to_3rd_party_contributions_value",
                "Hazard_endpoint_for_which_vertebrate_testing_was_proposed": "Hazard_endpoint_for_which_vertebrate_testing_was_proposed_value",
            }
        ],
    ),
    (
        "euReachSvhcAnnexXIV",
        "eu_reach_svhc_annex_xiv",
        {
            "Date_of_inclusion": "Date_of_inclusion_value",
            "Decision": "Decision_value",
            "Description": "Description_value",
            "IUCLID_dataset": "IUCLID_dataset_value",
            "Reason_for_inclusion": "Reason_for_inclusion_value",
        },
    ),
    (
        "euReachUniverseRegisteredSubstances",
        "eu_reach_universe_registered_substances",
        {
            "Brief_Profile_URL": "Brief_Profile_URL_value",
            "Highest_registered_tonnage": "Highest_registered_tonnage_value",
            "Infocard_URL": "Infocard_URL_value",
            "Position_in_the_chemical_universe": "Position_in_the_chemical_universe_value",
            "REACH_Factsheet(s)_URL": "REACH_Factsheet(s)_URL_value",
        },
    ),
    ("exposureControlsOther", "exposure_controls_other", []),
    (
        "exposureControlsOthers",
        "exposure_controls_others",
        [
            {
                "regList": "regList_value",
                "type": "type_value",
                "unit": "unit_value",
                "value": "value_value",
            }
        ],
    ),
    (
        "fireServiceLawList",
        "fire_service_law_list",
        {"class4": "class4_value", "designatedFlamSubstances": "designatedFlamSubstances_value"},
    ),
    ("hasODS", "has_ods", True),
    ("hasPIC", "has_pic", True),
    ("hasPOP", "has_pop", True),
    (
        "ishlCarcinogen",
        "ishl_carcinogen",
        {"ghsCategory": "ghsCategory_value", "maxValue": "maxValue_value", "unit": "unit_value"},
    ),
    ("ishlCscl", "ishl_cscl", {"class2": "class2_value"}),
    (
        "ishlMutagens",
        "ishl_mutagens",
        {"No-Hyperlink": "No-Hyperlink_value", "newValue": "newValue_value"},
    ),
    (
        "ishlOrdinance39",
        "ishl_ordinance_39",
        {"group": "group_value", "maxValue": "maxValue_value"},
    ),
    ("ishlOrganicSolvent", "ishl_organic_solvent", {"class2": "class2_value"}),
    ("ishlRequiredList", "ishl_required_list", {"label": "label_value", "sds": "sds_value"}),
    ("jpChemicalWeapons", "jp_chemical_weapons", {"No-Hyperlink": "No-Hyperlink_value"}),
    (
        "jpCsclBiodegradationBioconcentrationECS",
        "jp_cscl_biodegradation_bioconcentration_ecs",
        [
            {
                "Data": "Data_value",
                "Database_name": "Database_name_value",
                "Duration": "Duration_value",
                "Elimination_phase_duration": "Elimination_phase_duration_value",
                "Endpoint": "Endpoint_value",
            }
        ],
    ),
    (
        "jpCsclClassIISpecifiedSubstances",
        "jp_cscl_class_ii_specified_substances",
        {
            "class_Ⅱ_specified_chemical_substance_name": "class_Ⅱ_specified_chemical_substance_name_value",
            "miti_number": "miti_number_value",
            "no": "no_value",
        },
    ),
    (
        "jpCsclClassISpecifiedSubstances",
        "jp_cscl_class_i_specified_substances",
        {
            "Cabinet_Order_No": "Cabinet_Order_No_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "Class_I_Specified_Chemical_Substance_Name": "Class_I_Specified_Chemical_Substance_Name_value",
            "MITI_Number": "MITI_Number_value",
        },
    ),
    (
        "jpCsclMonitoringChemicalSubstances",
        "jp_cscl_monitoring_chemical_substances",
        {"placeholder": "not yet observed"},
    ),
    (
        "jpDesignatedHazardousSubstancesSoilPollutionControlLaw",
        "jp_designated_hazardous_substances_soil_pollution_control_law",
        {"No-Hyperlink": "No-Hyperlink_value"},
    ),
    (
        "jpEncsTypeIIIMonitoringSubstances",
        "jp_encs_type_iii_monitoring_substances",
        {
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "MITI_Number": "MITI_Number_value",
            "Number": "Number_value",
            "Registration_Number": "Registration_Number_value",
            "Source_Link": "Source_Link_value",
        },
    ),
    (
        "jpEncsTypeIIMonitoringSubstances",
        "jp_encs_type_ii_monitoring_substances",
        {
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "Classification": "Classification_value",
            "Info_Link": "Info_Link_value",
            "MITI_Number": "MITI_Number_value",
            "Number": "Number_value",
        },
    ),
    (
        "jpExplosivesControlLawList",
        "jp_explosives_control_law_list",
        {
            "CHRIP_ID": "CHRIP_ID_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "No-Hyperlink": "No-Hyperlink_value",
        },
    ),
    (
        "jpHarmfulSubstancesInHouseholdProducts",
        "jp_harmful_substances_in_household_products",
        {"No-Hyperlink": "No-Hyperlink_value"},
    ),
    (
        "jpIshlDangerousSubstancesExplosives",
        "jp_ishl_dangerous_substances_explosives",
        {
            "CHRIP_ID": "CHRIP_ID_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "No-Hyperlink": "No-Hyperlink_value",
        },
    ),
    (
        "jpIshlDangerousSubstancesFlammableFpBelow65",
        "jp_ishl_dangerous_substances_flammable_fp_below_65",
        {
            "CAS_Identity": "CAS_Identity_value",
            "CHRIP_ID": "CHRIP_ID_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "No-Hyperlink": "No-Hyperlink_value",
        },
    ),
    (
        "jpIshlDangerousSubstancesFlammableGases",
        "jp_ishl_dangerous_substances_flammable_gases",
        {
            "CHRIP_ID": "CHRIP_ID_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "No-Hyperlink": "No-Hyperlink_value",
        },
    ),
    (
        "jpIshlDangerousSubstancesIgnitable",
        "jp_ishl_dangerous_substances_ignitable",
        {"placeholder": "not yet observed"},
    ),
    (
        "jpIshlDangerousSubstancesOxidizing",
        "jp_ishl_dangerous_substances_oxidizing",
        {
            "CHRIP_ID": "CHRIP_ID_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "No-Hyperlink": "No-Hyperlink_value",
        },
    ),
    (
        "jpIshlProhibitedSubstances",
        "jp_ishl_prohibited_substances",
        {"No-Hyperlink": "No-Hyperlink_value"},
    ),
    (
        "jpIshlSubstancesForManufacturingPermit",
        "jp_ishl_substances_for_manufacturing_permit",
        {"No-Hyperlink": "No-Hyperlink_value"},
    ),
    (
        "jpNotificationExemptedGeneralChemicals",
        "jp_notification_exempted_general_chemicals",
        {"placeholder": "not yet observed"},
    ),
    (
        "jpODS",
        "jp_ods",
        {
            "CHRIP_ID": "CHRIP_ID_value",
            "Cabinet_Order_Name": "Cabinet_Order_Name_value",
            "Cabinet_Order_Number_(Type_of_Substances)": "Cabinet_Order_Number_(Type_of_Substances)_value",
            "Category": "Category_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
        },
    ),
    (
        "jpOilsUnderWaterPollutionControlAct",
        "jp_oils_under_water_pollution_control_act",
        {"placeholder": "not yet observed"},
    ),
    (
        "jpRotterdamPriorInformedConsentProcedureSubstances",
        "jp_rotterdam_prior_informed_consent_procedure_substances",
        {
            "Classification": "Classification_value",
            "Subject to Stockholm Convention": "Subject to Stockholm Convention_value",
            "Title": "Title_value",
        },
    ),
    (
        "jpSkinAndEyeDamagingAbsorbingSubstancesPpeRequirement",
        "jp_skin_and_eye_damaging_absorbing_substances_ppe_requirement",
        {
            "Cut-off value (weight percent) *8": "Cut-off value (weight percent) *8_value",
            "Effective date": "Effective date_value",
            "GHS Classification Name (Japan)": "GHS Classification Name (Japan)_value",
            "Name under Industrial Safety and Health Act *2": "Name under Industrial Safety and Health Act *2_value",
            "Ordinance on Prevention of Specific Chemical Hazards, etc. *7": "Ordinance on Prevention of Specific Chemical Hazards, etc. *7_value",
        },
    ),
    (
        "jpSpecifiedAirPollutantsFactoriesBusinessSites",
        "jp_specified_air_pollutants_factories_business_sites",
        {"No-Hyperlink": "No-Hyperlink_value"},
    ),
    (
        "jpSpecifiedChemicalHealthDamagePrevention",
        "jp_specified_chemical_health_damage_prevention",
        {"Group": "Group_value", "No-Hyperlink": "No-Hyperlink_value"},
    ),
    (
        "jpWaterPollutionContrloActDesignatedSubstances",
        "jp_water_pollution_control_act_designated_substances",
        {
            "CHRIP_ID": "CHRIP_ID_value",
            "Chemical_Substance_Name": "Chemical_Substance_Name_value",
            "No-Hyperlink": "No-Hyperlink_value",
        },
    ),
    ("lve", "lve", True),
    ("number", "number", "50-00-0"),
    ("pbtInfo", "pbt_info", []),
    (
        "pnecInfo",
        "pnec_info",
        [{"envCompartment": "envCompartment_value", "unit": "unit_value", "value": "value_value"}],
    ),
    ("rohsConcentration", "rohs_concentration", 0.1),
    ("rsl", "rsl", {"code": "SAMPLE"}),
    ("sara302", "sara_302", True),
    ("sara313ConcentrationLimit", "sara_313_concentration_limit", 0.1),
    ("snur", "snur", True),
    ("snur_cfr", "snur_cfr", "721.10068"),
    ("svhc", "svhc", True),
    ("tsca12BConcentrationLimit", "tsca_12b_concentration_limit", 0.1),
    ("tsca12BRegulated", "tsca_12b_regulated", True),
]


def test_substance_v4_info_declares_new_regulatory_fields_default_to_none():
    """All 80 newly-typed regulatory fields default to ``None`` when absent from the payload."""
    info = SubstanceV4Info.model_validate({"casID": "50-00-0"})

    for _alias, attr, _value in _SUBSTANCE_V4_NEW_FIELDS:
        assert getattr(info, attr) is None, f"{attr} should default to None"


@pytest.mark.parametrize(("alias", "attr", "value"), _SUBSTANCE_V4_NEW_FIELDS)
def test_substance_v4_info_declares_new_regulatory_fields(alias, attr, value):
    """Each of the 80 fields is typed (not dropped as an untyped extra) and round-trips its value."""
    info = SubstanceV4Info.model_validate({"casID": "50-00-0", alias: value})

    assert getattr(info, attr) == value
    assert alias not in (info.model_extra or {})


@pytest.mark.parametrize(
    "alias",
    ["svhc", "lve", "sara302", "snur", "tsca12BRegulated", "hasODS", "hasPIC", "hasPOP"],
)
def test_substance_v4_info_keeps_false_distinct_from_none(alias):
    """An explicit ``False`` (verified non-membership) must not collapse to ``None`` (not provided)."""
    info = SubstanceV4Info.model_validate({"casID": "50-00-0", alias: False})

    field_name = next(attr for a, attr, _ in _SUBSTANCE_V4_NEW_FIELDS if a == alias)
    assert getattr(info, field_name) is False


def test_substance_v4_info_water_pollution_alias_keeps_upstream_typo():
    """The upstream API's ``Contrlo`` typo must be preserved verbatim in the wire alias."""
    payload_value = {"CHRIP_ID": "1-2-3", "Chemical_Substance_Name": "Test", "No-Hyperlink": "x"}
    info = SubstanceV4Info.model_validate(
        {
            "casID": "50-00-0",
            "jpWaterPollutionContrloActDesignatedSubstances": payload_value,
        }
    )

    assert info.jp_water_pollution_control_act_designated_substances == payload_value

    dumped = info.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["jpWaterPollutionContrloActDesignatedSubstances"] == payload_value


def test_substance_v4_info_recorded_payload_keys_leave_no_extras():
    """A payload built from all 80 new aliases plus a few pre-existing fields should have zero extras."""
    payload = {alias: value for alias, _attr, value in _SUBSTANCE_V4_NEW_FIELDS}
    payload["casID"] = "50-00-0"
    payload["WGK"] = "WGK 1"
    payload["substanceId"] = "SUB123"

    info = SubstanceV4Info.model_validate(payload)

    assert not info.model_extra


# Recorded from GET /api/v3/projects/{id}; TaskConfig entries arrive under the
# "TaskConfig" key with "dataTemplateId" and string "hidden" values.
PROJECT_TASK_CONFIG_PAYLOAD = {
    "dataTemplateId": "DAT123",
    "workflowId": "WFL123",
    "defaultTaskName": "Characterization",
    "target": "standard",
    "hidden": "true",
}


def test_project_task_config_deserializes_from_wire_names():
    """Test TaskConfig entries on a project survive validation, not dropped as extras."""
    project = Project.model_validate(
        {"description": "p", "TaskConfig": [PROJECT_TASK_CONFIG_PAYLOAD]}
    )

    assert len(project.task_config) == 1
    config = project.task_config[0]
    assert isinstance(config, TaskConfig)
    assert config.data_template_id == "DAT123"
    assert config.workflow_id == "WFL123"
    assert config.default_task_name == "Characterization"
    assert config.hidden == "true"


def test_project_task_config_serializes_to_wire_names():
    """Test TaskConfig dumps under "TaskConfig" with the API's inner field names."""
    project = Project(description="p", task_config=[TaskConfig(**PROJECT_TASK_CONFIG_PAYLOAD)])

    dumped = project.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["TaskConfig"] == [PROJECT_TASK_CONFIG_PAYLOAD]


def test_project_class_supports_restricted():
    """Test the restricted project class parses from API responses."""
    project = Project.model_validate({"description": "p", "class": "restricted"})

    assert project.project_class is ProjectClass.RESTRICTED


def test_project_old_api_params_uses_wire_name():
    """Test oldApiParams maps to old_api_params instead of being dropped."""
    project = Project.model_validate({"description": "p", "oldApiParams": {"moNumber": "42"}})

    assert project.old_api_params == {"moNumber": "42"}


def test_substance_info_tolerates_wider_v3_field_types():
    """``SubstanceInfo`` fields whose v3 payloads are wider than first modeled.

    Per the api-substance-v3 spec, ``specificConcentrationLimit`` is an array of
    objects, ``mFactor``/``mFactorChronic`` may be strings, and the STOT fields
    may be objects; the narrow types raised ValidationError on real responses.
    """
    substance = SubstanceInfo.model_validate(
        {
            "casID": "50-00-0",
            "specificConcentrationLimit": [
                {"class": "Skin Corr.", "hCode": "H314", "category": "1"}
            ],
            "mFactor": "10",
            "mFactorChronic": "1",
            "stotAffectedOrgans": {"organ": "liver"},
            "stotRouteOfExposure": {"route": "oral"},
        }
    )

    assert isinstance(substance.specific_concentration_limit, list)
    assert substance.m_factor == "10"
    assert substance.m_factor_chronic == "1"
    assert substance.stot_affected_organs == {"organ": "liver"}
    assert substance.stot_route_of_exposure == {"route": "oral"}
