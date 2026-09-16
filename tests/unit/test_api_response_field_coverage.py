"""Guard that models keep the API response fields their consumers depend on.

``BaseAlbertModel`` does not set an ``extra`` policy, so Pydantic defaults to
``extra="ignore"`` and any field a model fails to declare is dropped at validation
and is not recoverable from ``model_extra``. These tests pin the fields that were
silently lost, using payload fragments recorded from the live API.
"""

import pytest

from albert.resources.activities import Activity, ActivityActor, ActivitySearchItem
from albert.resources.product_design import (
    CasLevelSubstance,
    UnpackedCasInfo,
    UnpackedProductDesign,
)
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


ACTIVITY_SEARCH_ITEM_PAYLOAD = {
    "action": "created",
    "name": "api-activity",
    "PK": "TEN0#INVA1111",
    "class": "shared",
    "loggedAt": "2023-05-11",
    "operationId": "getInventory",
    "objectId": "INVMO2806-010",
    "objectType": "INV",
    "activityId": "DAT111#122323232323232",
    "user": {
        "name": "vikash",
        "id": "USR111",
        "role": "innovator",
        "class": "admin",
    },
    "actor": {
        "details": {
            "mode": "obo",
            "client_id": "client-uuid-123",
            "act": {
                "sub": "invent-ask-albert",
                "name": "invent-ask-albert/product-obo",
            },
        },
        "metadata": {"traceId": "abc-123"},
    },
}


def test_activity_search_item_exposes_actor_details():
    """``ActivitySearchItem`` must expose actor details when present on S2S activity events."""
    item = ActivitySearchItem.model_validate(ACTIVITY_SEARCH_ITEM_PAYLOAD)

    assert item.actor is not None
    assert isinstance(item.actor, ActivityActor)
    assert item.actor.details is not None
    assert item.actor.details.mode == "obo"
    assert item.actor.details.client_id == "client-uuid-123"
    assert item.actor.details.act is not None
    assert item.actor.details.act.sub == "invent-ask-albert"
    assert item.actor.details.act.name == "invent-ask-albert/product-obo"
    assert item.actor.metadata == {"traceId": "abc-123"}


def test_activity_search_item_actor_client_id_alias():
    """``ActivityActorDetails`` accepts either client_id or clientId."""
    payload = {
        "actor": {
            "details": {
                "mode": "obo",
                "clientId": "client-uuid-456",
            }
        }
    }
    item = ActivitySearchItem.model_validate(payload)

    assert item.actor is not None
    assert item.actor.details is not None
    assert item.actor.details.client_id == "client-uuid-456"


def test_activity_search_item_actor_absent():
    """``actor`` is None when absent in activity search results."""
    item = ActivitySearchItem.model_validate({"activityId": "ACT1"})

    assert item.actor is None


def test_activity_exposes_actor():
    """``Activity`` resource keeps actor details returned by get_all feed."""
    activity = Activity.model_validate(
        {
            "albertId": "COM2358",
            "activityId": "COM2358",
            "action": "created",
            "actor": {
                "details": {
                    "mode": "obo",
                    "client_id": "client-uuid-789",
                }
            },
        }
    )

    assert activity.actor is not None
    assert activity.actor.details is not None
    assert activity.actor.details.client_id == "client-uuid-789"
