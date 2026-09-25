"""Unit tests for InventoryCollection PATCH payload generation and parameter prep.

Allowed under the patch-builder exception in OPINIONS.md: these guard
non-obvious diff behavior in ``_generate_inventory_patch_payload`` (the
company/tags/cas/acls special cases and the formula-override normalization)
and pure parameter-mapping behavior in ``_prepare_parameters``, with no I/O to
fake. ``_apply_inventory_patch_payload`` batching is covered with ``responses``
since it only asserts on the requests the SDK sends.
"""

import responses

from albert.collections.inventory import InventoryCollection
from albert.resources.acls import ACL, AccessControlLevel
from albert.resources.cas import Cas
from albert.resources.companies import Company
from albert.resources.inventory import CasAmount, InventoryCategory, InventoryItem
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocationFilter
from albert.resources.tags import Tag
from albert.resources.users import User
from tests.unit.conftest import UNIT_BASE_URL


def _item(**kwargs) -> InventoryItem:
    defaults = {"id": "INVA1", "category": InventoryCategory.RAW_MATERIALS}
    defaults.update(kwargs)
    return InventoryItem(**defaults)


def _collection(offline_session) -> InventoryCollection:
    return InventoryCollection(session=offline_session)


# --- base scalar attributes pass through _generate_patch_payload unmodified ---


def test_unset_scalar_attribute_emits_no_op(offline_session) -> None:
    """Test that a scalar attribute the caller never set produces no patch operation."""
    existing = _item(alias="Old Alias")
    updated = _item()  # alias never set

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_explicit_none_scalar_attribute_emits_delete(offline_session) -> None:
    """Test that explicitly clearing a scalar attribute emits a delete op."""
    existing = _item(alias="Old Alias")
    updated = _item(alias=None)

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {"attribute": "alias", "operation": "delete", "oldValue": "Old Alias"}
    ]


def test_changed_scalar_attribute_emits_update(offline_session) -> None:
    """Test that a changed scalar attribute emits an update op with the old value."""
    existing = _item(description="old desc")
    updated = _item(description="new desc")

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "attribute": "description",
            "operation": "update",
            "oldValue": "old desc",
            "newValue": "new desc",
        }
    ]


def test_unchanged_scalar_attribute_emits_no_op(offline_session) -> None:
    """Test that an unchanged scalar attribute emits no patch operation."""
    existing = _item(description="same")
    updated = _item(description="same")

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


# --- is_formula_override normalization (FORMULAS category only) ---


def test_is_formula_override_normalization_skipped_for_non_formula_category(
    offline_session,
) -> None:
    """Test that non-FORMULAS items get the plain add op, with no normalization applied."""
    existing = _item(category=InventoryCategory.RAW_MATERIALS)
    updated = _item(category=InventoryCategory.RAW_MATERIALS, is_formula_override=True)

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {"attribute": "isFormulaOverride", "operation": "add", "newValue": True}
    ]


def test_is_formula_override_true_on_formula_becomes_update_from_false(offline_session) -> None:
    """Test that first-time True on a formula is normalized from add to update(False->True)."""
    existing = _item(id="INVF1", category=InventoryCategory.FORMULAS, project_id="PRO1")
    updated = _item(
        id="INVF1",
        category=InventoryCategory.FORMULAS,
        project_id="PRO1",
        is_formula_override=True,
    )

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "attribute": "isFormulaOverride",
            "operation": "update",
            "oldValue": False,
            "newValue": True,
        }
    ]


def test_is_formula_override_false_on_formula_drops_the_add_op(offline_session) -> None:
    """Test that first-time False on a formula is dropped entirely (implicit default)."""
    existing = _item(id="INVF1", category=InventoryCategory.FORMULAS, project_id="PRO1")
    updated = _item(
        id="INVF1",
        category=InventoryCategory.FORMULAS,
        project_id="PRO1",
        is_formula_override=False,
    )

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_is_formula_override_changed_update_op_passes_through_unmodified(offline_session) -> None:
    """Test that an update op (not add) on is_formula_override is left untouched."""
    existing = _item(
        id="INVF1",
        category=InventoryCategory.FORMULAS,
        project_id="PRO1",
        is_formula_override=True,
    )
    updated = _item(
        id="INVF1",
        category=InventoryCategory.FORMULAS,
        project_id="PRO1",
        is_formula_override=False,
    )

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "attribute": "isFormulaOverride",
            "operation": "update",
            "oldValue": True,
            "newValue": False,
        }
    ]


def test_is_formula_override_unset_on_formula_skips_normalization(offline_session) -> None:
    """Test that an unset is_formula_override on a formula item emits no patch operation."""
    existing = _item(id="INVF1", category=InventoryCategory.FORMULAS, project_id="PRO1")
    updated = _item(id="INVF1", category=InventoryCategory.FORMULAS, project_id="PRO1")

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_is_formula_override_unchanged_on_formula_finds_no_entry_to_normalize(
    offline_session,
) -> None:
    """Test that setting is_formula_override to its existing value normalizes a no-op patch.

    Normalization still runs (is_formula_override is not None), but the base diff
    produced no ``isFormulaOverride`` entry to rewrite, so it falls through untouched.
    """
    existing = _item(
        id="INVF1",
        category=InventoryCategory.FORMULAS,
        project_id="PRO1",
        is_formula_override=True,
    )
    updated = _item(
        id="INVF1",
        category=InventoryCategory.FORMULAS,
        project_id="PRO1",
        is_formula_override=True,
    )

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_is_formula_override_normalization_skips_unrelated_changes(offline_session) -> None:
    """Test that normalization only rewrites the isFormulaOverride entry, leaving others intact."""
    existing = _item(
        id="INVF1", category=InventoryCategory.FORMULAS, project_id="PRO1", description="old"
    )
    updated = _item(
        id="INVF1",
        category=InventoryCategory.FORMULAS,
        project_id="PRO1",
        description="new",
        is_formula_override=True,
    )

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    by_attribute = {op["attribute"]: op for op in payload["data"]}
    assert by_attribute["description"] == {
        "attribute": "description",
        "operation": "update",
        "oldValue": "old",
        "newValue": "new",
    }
    assert by_attribute["isFormulaOverride"] == {
        "attribute": "isFormulaOverride",
        "operation": "update",
        "oldValue": False,
        "newValue": True,
    }


# --- company special case ---


def test_company_unset_emits_no_op(offline_session) -> None:
    """Test that an unset company produces no patch operation."""
    existing = _item(company=Company(id="COM1", name="Acme"))
    updated = _item()  # company never set

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_company_added_emits_add_with_bare_id(offline_session) -> None:
    """Test that assigning a company for the first time emits an add op with a bare id."""
    existing = _item()  # company unset -> None
    updated = _item(company=Company(id="COM1", name="Acme"))

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [{"operation": "add", "attribute": "companyId", "newValue": "COM1"}]


def test_company_cleared_emits_delete_with_entity_id(offline_session) -> None:
    """Test that clearing company emits a delete op keyed by entityId (not oldValue)."""
    existing = _item(company=Company(id="COM1", name="Acme"))
    updated = _item(company=None)

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {"operation": "delete", "attribute": "companyId", "entityId": "COM1"}
    ]


def test_company_changed_emits_update_with_bare_ids(offline_session) -> None:
    """Test that changing company emits an update op with bare old/new ids."""
    existing = _item(company=Company(id="COM1", name="Acme"))
    updated = _item(company=Company(id="COM2", name="Beta"))

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "operation": "update",
            "attribute": "companyId",
            "oldValue": "COM1",
            "newValue": "COM2",
        }
    ]


def test_company_unchanged_emits_no_op(offline_session) -> None:
    """Test that assigning the same company (same id) emits no patch operation."""
    existing = _item(company=Company(id="COM1", name="Acme"))
    updated = _item(company=Company(id="COM1", name="Acme"))

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_company_explicit_none_with_no_existing_company_emits_no_op(offline_session) -> None:
    """Test that clearing company when none was ever set emits no patch operation."""
    existing = _item()  # company never set -> None
    updated = _item(company=None)

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


# --- tags special case ---


def test_tags_unset_emits_no_op(offline_session) -> None:
    """Test that unset tags produce no patch operation."""
    existing = _item(tags=[Tag(id="TAG1", tag="alpha")])
    updated = _item()  # tags never set

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_tags_cleared_to_none_deletes_each_existing_tag(offline_session) -> None:
    """Test that clearing tags to None deletes every existing tag by id."""
    existing = _item(
        tags=[Tag(id="TAG1", tag="alpha"), Tag(id="TAG2", tag="beta")],
    )
    updated = _item(tags=None)

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert {op["oldValue"] for op in payload["data"]} == {"TAG1", "TAG2"}
    assert all(
        op["operation"] == "delete" and op["attribute"] == "tagId" for op in payload["data"]
    )


def test_tags_added_from_empty_uses_entity_id_shape(offline_session) -> None:
    """Test that adding tags to a previously tag-less item wraps each op with entityId."""
    existing = _item(tags=[])
    updated = _item(tags=[Tag(id="TAG1", tag="alpha")])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "operation": "add",
            "attribute": "tagId",
            "newValue": "TAG1",
            "entityId": "TAG1",
        }
    ]


def test_tags_mixed_add_and_delete_uses_bare_id_shape(offline_session) -> None:
    """Test a mixed tag diff (existing non-empty) emits per-id add/delete without entityId."""
    existing = _item(tags=[Tag(id="TAG1", tag="alpha"), Tag(id="TAG2", tag="beta")])
    updated = _item(tags=[Tag(id="TAG1", tag="alpha"), Tag(id="TAG3", tag="gamma")])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    add_ops = [op for op in payload["data"] if op["operation"] == "add"]
    del_ops = [op for op in payload["data"] if op["operation"] == "delete"]
    assert add_ops == [{"operation": "add", "attribute": "tagId", "newValue": "TAG3"}]
    assert del_ops == [{"operation": "delete", "attribute": "tagId", "oldValue": "TAG2"}]


def test_tags_unchanged_emits_no_op(offline_session) -> None:
    """Test that an unchanged tag list emits no patch operation."""
    existing = _item(tags=[Tag(id="TAG1", tag="alpha")])
    updated = _item(tags=[Tag(id="TAG1", tag="alpha")])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


# --- cas special case (delegated to _build_cas_patch_operations; wiring only) ---


def test_cas_unset_emits_no_op(offline_session) -> None:
    """Test that unset cas amounts produce no patch operation."""
    existing = _item(cas=[CasAmount(id="CAS1", min=1.0, max=2.0)])
    updated = _item()  # cas never set

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_cas_new_entry_emits_add_operation(offline_session) -> None:
    """Test that adding a new CAS entry wires through to a casId add op."""
    existing = _item(cas=[])
    updated = _item(cas=[CasAmount(id="CAS1", min=1.0, max=2.0)])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {"operation": "add", "attribute": "casId", "newValue": "CAS1", "min": 1.0, "max": 2.0}
    ]


def test_cas_removed_entry_emits_delete_operation(offline_session) -> None:
    """Test that removing a CAS entry wires through to a casId delete op."""
    existing = _item(cas=[CasAmount(id="CAS1", min=1.0, max=2.0)])
    updated = _item(cas=[])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [{"operation": "delete", "attribute": "casId", "oldValue": "CAS1"}]


def test_cas_changed_min_emits_scalar_update_operation(offline_session) -> None:
    """Test that changing an existing CAS entry's min wires through to a scalar update op."""
    existing = _item(cas=[CasAmount(id="CAS1", min=1.0, max=2.0)])
    updated = _item(cas=[CasAmount(id="CAS1", min=1.5, max=2.0)])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "attribute": "min",
            "entityId": "CAS1",
            "operation": "update",
            "oldValue": 1.0,
            "newValue": 1.5,
        }
    ]


# --- acls special case ---


def test_acls_unset_emits_no_op(offline_session) -> None:
    """Test that unset acls produce no patch operation."""
    existing = _item(acls=[ACL(id="USR1", fgc=AccessControlLevel.INVENTORY_VIEWER)])
    updated = _item()  # acls never set

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


def test_acls_added_from_empty_emits_single_add_op(offline_session) -> None:
    """Test that assigning acls from empty emits one add op with the full dumped entries."""
    existing = _item(acls=[])
    updated = _item(acls=[ACL(id="USR1", fgc=AccessControlLevel.INVENTORY_VIEWER)])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "attribute": "ACL",
            "operation": "add",
            "newValue": [{"id": "USR1", "fgc": "InventoryViewer"}],
        }
    ]


def test_acls_cleared_emits_single_delete_op(offline_session) -> None:
    """Test that clearing acls emits one delete op with the full dumped entries."""
    existing = _item(acls=[ACL(id="USR1", fgc=AccessControlLevel.INVENTORY_VIEWER)])
    updated = _item(acls=[])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "attribute": "ACL",
            "operation": "delete",
            "oldValue": [{"id": "USR1", "fgc": "InventoryViewer"}],
        }
    ]


def test_acls_fgc_changed_emits_per_id_update(offline_session) -> None:
    """Test that changing an existing acl entry's fgc emits a per-id fgc update op."""
    existing = _item(acls=[ACL(id="USR1", fgc=AccessControlLevel.INVENTORY_VIEWER)])
    updated = _item(acls=[ACL(id="USR1", fgc=AccessControlLevel.INVENTORY_OWNER)])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == [
        {
            "attribute": "fgc",
            "id": "USR1",
            "operation": "update",
            "oldValue": "InventoryViewer",
            "newValue": "InventoryOwner",
        }
    ]


def test_acls_unchanged_emits_no_op(offline_session) -> None:
    """Test that identical acl entries emit no patch operation."""
    existing = _item(acls=[ACL(id="USR1", fgc=AccessControlLevel.INVENTORY_VIEWER)])
    updated = _item(acls=[ACL(id="USR1", fgc=AccessControlLevel.INVENTORY_VIEWER)])

    payload = _collection(offline_session)._generate_inventory_patch_payload(
        existing=existing, updated=updated
    )

    assert payload["data"] == []


# --- _prepare_parameters ---


def test_prepare_parameters_defaults_are_all_none(offline_session) -> None:
    """Test that calling with no filters returns every param key set to None."""
    params = _collection(offline_session)._prepare_parameters()

    expected_keys = {
        "text",
        "order",
        "sortBy",
        "category",
        "tags",
        "manufacturer",
        "cas",
        "location",
        "storageLocation",
        "lotOwner",
        "createdBy",
        "sheetId",
        "projectId",
        "offset",
        "fromCreatedAt",
        "toCreatedAt",
        "updatedBy",
        "fromUpdatedAt",
        "toUpdatedAt",
        "albertId",
        "attributeId",
        "casSmile",
        "collaboratorPopUp",
        "containsField",
        "containsText",
        "createdById",
        "details",
        "dropDownText",
        "dropDownTextProp",
        "dupDetection",
        "facetField",
        "facetText",
        "fromExpirationDate",
        "fromLotCreatedAt",
        "fromOnHand",
        "gsloGroup",
        "idh",
        "isPopUp",
        "lotCreatedBy",
        "materialCategory",
        "packSize",
        "pictogramName",
        "result",
        "rsn",
        "sourceField",
        "status",
        "subCategory",
        "synthesisProductCreated",
        "toExpirationDate",
        "toLotCreatedAt",
        "toOnHand",
    }

    assert set(params) == expected_keys
    assert params == dict.fromkeys(expected_keys)


def test_prepare_parameters_wraps_single_instances_into_lists(offline_session) -> None:
    """Test that a single cas/category/company/location/storage_location/lot_owner is wrapped."""
    params = _collection(offline_session)._prepare_parameters(
        cas=Cas(number="7727-37-9"),
        category=InventoryCategory.RAW_MATERIALS,
        company=Company(name="Acme"),
        location=Location(name="Boston Lab", latitude=0, longitude=0, address="1 Main St"),
        storage_location=StorageLocationFilter(name="Freezer A"),
        lot_owner=User(name="Jane Doe", id="USR1"),
    )

    assert params["cas"] == ["7727-37-9"]
    assert params["category"] == [InventoryCategory.RAW_MATERIALS]
    assert params["manufacturer"] == ["Acme"]
    assert params["location"] == ["Boston Lab"]
    assert params["storageLocation"] == ["Freezer A"]
    assert params["lotOwner"] == ["Jane Doe"]


def test_prepare_parameters_resolves_created_by_user_objects(offline_session) -> None:
    """Test that created_by resolves User objects to their name, falling back to id."""
    params = _collection(offline_session)._prepare_parameters(
        created_by=[
            User(name="Jane Doe", id="USR2"),
            User.model_construct(id="USR3", name=None),
        ],
    )

    assert params["createdBy"] == ["Jane Doe", "USR3"]


def test_prepare_parameters_resolves_created_by_strings(offline_session) -> None:
    """Test that a list of created_by strings passes through as-is."""
    params = _collection(offline_session)._prepare_parameters(created_by=["USR1", "USR2"])

    assert params["createdBy"] == ["USR1", "USR2"]


def test_prepare_parameters_filters_empty_string_created_by(offline_session) -> None:
    """Test that an empty-string created_by entry is dropped, not passed through as ''."""
    params = _collection(offline_session)._prepare_parameters(created_by=["", "USR1"])

    assert params["createdBy"] == ["USR1"]


def test_prepare_parameters_created_by_all_empty_returns_none(offline_session) -> None:
    """Test that created_by resolving to no usable values returns None, not an empty list."""
    params = _collection(offline_session)._prepare_parameters(created_by=[""])

    assert params["createdBy"] is None


def test_prepare_parameters_lot_created_by_drops_unnamed_userless_entries(offline_session) -> None:
    """Test that a User with neither name nor id is dropped, and others are kept."""
    params = _collection(offline_session)._prepare_parameters(
        lot_created_by=[
            User.model_construct(id=None, name=None),
            User(name="Jane Doe", id="USR2"),
        ],
    )

    assert params["lotCreatedBy"] == ["Jane Doe"]


def test_prepare_parameters_wraps_single_string_list_filters(offline_session) -> None:
    """Test that a bare string filter is wrapped into a single-item list via ensure_list."""
    params = _collection(offline_session)._prepare_parameters(albert_id="INVA1")

    assert params["albertId"] == ["INVA1"]


def test_prepare_parameters_leaves_list_filters_untouched(offline_session) -> None:
    """Test that a list filter is passed through unwrapped."""
    params = _collection(offline_session)._prepare_parameters(albert_id=["INVA1", "INVA2"])

    assert params["albertId"] == ["INVA1", "INVA2"]


# --- _apply_inventory_patch_payload batching ---


@responses.activate
def test_apply_batches_metadata_changes_into_one_trailing_request(offline_session) -> None:
    """Test that Metadata.* changes are batched into a single trailing PATCH request."""
    url = "/api/v3/inventories/INVA1"
    responses.patch(f"{UNIT_BASE_URL}{url}", json={})

    patch_payload = {
        "data": [
            {"attribute": "alias", "operation": "update", "oldValue": "a", "newValue": "b"},
            {"attribute": "Metadata.field1", "operation": "add", "newValue": "x"},
            {"attribute": "description", "operation": "add", "newValue": "d"},
            {"attribute": "Metadata.field2", "operation": "add", "newValue": "y"},
        ]
    }

    _collection(offline_session)._apply_inventory_patch_payload(
        url=url, patch_payload=patch_payload
    )

    assert len(responses.calls) == 3
    import json as _json

    bodies = [_json.loads(c.request.body) for c in responses.calls]
    assert bodies[0] == {"data": [patch_payload["data"][0]]}
    assert bodies[1] == {"data": [patch_payload["data"][2]]}
    assert bodies[2] == {"data": [patch_payload["data"][1], patch_payload["data"][3]]}


@responses.activate
def test_apply_sends_no_trailing_batch_when_no_metadata_changes(offline_session) -> None:
    """Test that no extra request is sent when there are no Metadata.* changes."""
    url = "/api/v3/inventories/INVA1"
    responses.patch(f"{UNIT_BASE_URL}{url}", json={})

    patch_payload = {
        "data": [
            {"attribute": "alias", "operation": "update", "oldValue": "a", "newValue": "b"},
            {"attribute": "description", "operation": "add", "newValue": "d"},
        ]
    }

    _collection(offline_session)._apply_inventory_patch_payload(
        url=url, patch_payload=patch_payload
    )

    assert len(responses.calls) == 2


@responses.activate
def test_apply_sends_single_batch_when_only_metadata_changes(offline_session) -> None:
    """Test that an all-metadata patch payload is sent as a single batched request."""
    url = "/api/v3/inventories/INVA1"
    responses.patch(f"{UNIT_BASE_URL}{url}", json={})

    patch_payload = {
        "data": [
            {"attribute": "Metadata.field1", "operation": "add", "newValue": "x"},
            {"attribute": "Metadata.field2", "operation": "add", "newValue": "y"},
        ]
    }

    _collection(offline_session)._apply_inventory_patch_payload(
        url=url, patch_payload=patch_payload
    )

    assert len(responses.calls) == 1
    import json as _json

    assert _json.loads(responses.calls[0].request.body) == patch_payload


@responses.activate
def test_apply_sends_nothing_when_no_changes(offline_session) -> None:
    """Test that an empty patch payload sends no requests at all."""
    url = "/api/v3/inventories/INVA1"

    _collection(offline_session)._apply_inventory_patch_payload(
        url=url, patch_payload={"data": []}
    )

    assert len(responses.calls) == 0
