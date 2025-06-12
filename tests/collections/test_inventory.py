import time

import pytest

from albert.albert import Albert
from albert.collections.inventory import InventoryCategory
from albert.exceptions import BadRequestError
from albert.resources.base import SecurityClass
from albert.resources.cas import Cas
from albert.resources.companies import Company
from albert.resources.data_columns import DataColumn
from albert.resources.facet import FacetItem, FacetValue
from albert.resources.identifiers import ensure_inventory_id
from albert.resources.inventory import (
    CasAmount,
    InventoryItem,
    InventorySpec,
    InventorySpecValue,
    InventoryUnitCategory,
)
from albert.resources.tags import Tag
from albert.resources.units import Unit
from albert.resources.workflows import Workflow


def _list_asserts(returned_list):
    for i, u in enumerate(returned_list):
        if i == 50:
            break
        assert isinstance(u, InventoryItem)
        assert isinstance(u.name, str | None)
        assert isinstance(u.id, str)


def test_simple_inventory_list(client: Albert, seeded_inventory):
    inventory = client.inventory.list()
    _list_asserts(inventory)


def test_advanced_inventory_list(
    client: Albert, seeded_inventory: list[InventoryItem], seeded_cas: list[Cas]
):
    test_inv_item = seeded_inventory[1]
    matching_cas = [x for x in seeded_cas if x.id in test_inv_item.cas[0].id][0]
    inventory = client.inventory.list(
        text=test_inv_item.name,
        category=InventoryCategory.CONSUMABLES,
        cas=matching_cas,
        company=test_inv_item.company,
    )
    _list_asserts(inventory)
    for i, x in enumerate(inventory):
        if i == 10:  # just check the first 10 for speed
            break
        assert "ethanol" in x.name.lower()


def test_match_all_conditions(
    client: Albert, seeded_inventory: list[InventoryItem], seeded_tags: list[Tag]
):
    # First test is using OR between conditions
    # this should return our 3 test items
    inventory = client.inventory.list(
        tags=[seeded_tags[0].tag, seeded_tags[1].tag],
    )

    for x in inventory:
        for tag in x.tags:
            assert tag.tag in [seeded_tags[0].tag, seeded_tags[1].tag]
    # This one tests using AND conditions and will return only
    # one item that has both seeded tags
    inventory = client.inventory.list(
        tags=[seeded_tags[0].tag, seeded_tags[1].tag],
        match_all_conditions=True,
    )
    for x in inventory:
        assert len(x.tags) >= 2
        for tag in x.tags:
            assert tag.tag in [seeded_tags[0].tag, seeded_tags[1].tag]


def test_get_by_id(client: Albert, seeded_inventory):
    get_by_id = client.inventory.get_by_id(id=seeded_inventory[1].id)
    assert isinstance(get_by_id, InventoryItem)
    assert seeded_inventory[1].name == get_by_id.name
    assert seeded_inventory[1].id == get_by_id.id

    id_2 = seeded_inventory[0].id.replace("INV", "")
    get_by_id = client.inventory.get_by_id(id=id_2)
    assert isinstance(get_by_id, InventoryItem)
    assert seeded_inventory[0].name == get_by_id.name
    assert seeded_inventory[0].id == get_by_id.id


def test_get_by_ids(client: Albert):
    # Gather 51 unique inventory IDs
    inventory_ids = []
    for x in client.inventory.search():
        inventory_ids.append(x.id)
        if len(inventory_ids) == 51:
            break

    # Assert same length obtained
    items = client.inventory.get_by_ids(ids=inventory_ids)
    assert len(items) == len(inventory_ids)

    # TODO: Enable this test after INV-70/add-flag-called-preserve-order complete
    # for inventory_id, inventory in zip(inventory_ids, bulk_get, strict=True):
    #     assert f"INV{inventory_id}" == inventory.id


def test_inventory_update(client: Albert, seed_prefix: str):
    # create a new test inventory item
    ii = InventoryItem(
        name=f"{seed_prefix} - SDK UPDATE/DELETE TEST",
        description="SDK item that will be updated and deleted.",
        category=InventoryCategory.RAW_MATERIALS,
        unit_category=InventoryUnitCategory.MASS,
        security_class=SecurityClass.CONFIDENTIAL,
        company="",
    )
    created = client.inventory.create(inventory_item=ii)

    # Give time for the DB to sync - somewhere between 1 and 4 seconds is needed
    # for this test to work
    time.sleep(4)

    assert client.inventory.inventory_exists(inventory_item=created)
    d = "testing SDK CRUD"
    created.description = d

    updated = client.inventory.update(inventory_item=created)
    assert updated.description == d
    assert updated.id == created.id

    client.inventory.delete(id=created.id)
    assert not client.inventory.inventory_exists(inventory_item=created)


def test_collection_blocks_formulation(client: Albert, seeded_projects):
    """assert that trying to create a FORMULATION with a collection block raises an error"""

    # create a formulation with the collection block
    with pytest.raises(NotImplementedError):
        r = client.inventory.create(
            inventory_item=InventoryItem(
                name="test formulation",
                category=InventoryCategory.FORMULAS,
                project_id=seeded_projects[0].id,
            )
        )

        # delete the collection block in case it was created
        client.inventory.delete(r)
        assert not client.inventory.inventory_exists(r.id)


def test_blocks_dupes(caplog, client: Albert, seeded_inventory: list[InventoryItem]):
    ii_copy = seeded_inventory[0].model_copy(update={"id": None})
    returned_ii = client.inventory.create(inventory_item=ii_copy)

    assert returned_ii.id == seeded_inventory[0].id
    assert returned_ii.name == seeded_inventory[0].name
    assert (
        f"Inventory item already exists with name {returned_ii.name} and company {returned_ii.company.name}, returning existing item."
        in caplog.text
    )


def test_add_property_to_inv_spec(
    seed_prefix: str,
    client: Albert,
    seeded_inventory: list[InventoryItem],
    seeded_data_columns: list[DataColumn],
    seeded_units: list[Unit],
    seeded_workflows: list[Workflow],
):
    specs = []
    for dc in seeded_data_columns:
        spec_to_add = InventorySpec(
            name=f"{seed_prefix} -- {dc.name}",
            data_column_id=dc.id,
            unit_id=seeded_units[0].id,
            value=InventorySpecValue(reference="42"),
            workflow_id=seeded_workflows[0].id,
        )
        specs.append(spec_to_add)
    added_specs = client.inventory.add_specs(inventory_id=seeded_inventory[0].id, specs=specs)
    assert len(added_specs.specs) == len(seeded_data_columns)
    assert all([isinstance(x, InventorySpec) for x in added_specs.specs])


def test_update_inventory_item_standard_attributes(
    client: Albert, seeded_inventory: list[InventoryItem]
):
    """
    Test updating each updatable attribute for an InventoryItem.

    Parameters
    ----------
    client : Albert
        The Albert client instance.
    seeded_inventory : List[InventoryItem]
        A list of seeded inventory items.
    """

    # Assume we have at least one seeded inventory item

    updated_inventory_item = seeded_inventory[0].model_copy(
        update={
            "name": "Updated Inventory Name",
            "description": "Updated Description",
            "unit_category": InventoryUnitCategory.VOLUME.value,
            "security_class": "confidential",
            "alias": "Updated Alias",
        }
    )
    # Perform the update
    updated_item = client.inventory.update(inventory_item=updated_inventory_item)

    # Verify that all updatable attributes have been updated
    assert updated_item.name == "Updated Inventory Name"
    assert updated_item.description == "Updated Description"
    assert updated_item.unit_category == InventoryUnitCategory.VOLUME.value
    assert updated_item.security_class == "confidential"
    assert updated_item.alias == "Updated Alias"

    # Optionally, re-fetch the item and verify the updates are persisted
    fetched_item = client.inventory.get_by_id(id=updated_inventory_item.id)
    assert fetched_item.name == "Updated Inventory Name"
    assert fetched_item.description == "Updated Description"
    assert fetched_item.unit_category == InventoryUnitCategory.VOLUME.value
    assert fetched_item.security_class == "confidential"
    assert fetched_item.alias == "Updated Alias"


def test_update_inventory_item_advanced_attributes(
    client: Albert,
    seeded_inventory: list[InventoryItem],
    seeded_cas: list[Cas],
    seeded_companies: list[Company],
    seeded_tags: list[Tag],
):
    """
    Test updating advanced attributes for an InventoryItem.

    Parameters
    ----------
    client : Albert
        The Albert client instance.
    seeded_inventory : List[InventoryItem]
        A list of seeded inventory items.
    """

    updated_inventory_item = seeded_inventory[0].model_copy(
        update={
            "cas": [CasAmount(id=seeded_cas[1].id, min=0.5, max=0.75)],
            "company": seeded_companies[1],
            "tags": [seeded_tags[0], seeded_tags[1]],
            "alias": "Updated Alias Again",
        }
    )

    returned_item = client.inventory.update(inventory_item=updated_inventory_item)
    assert returned_item.cas[0].id == seeded_cas[1].id
    assert returned_item.cas[0].min == 0.5
    assert returned_item.cas[0].max == 0.75
    assert returned_item.company.id == seeded_inventory[1].company.id
    assert len(returned_item.tags) == 2
    assert seeded_tags[1].id in [x.id for x in returned_item.tags]
    assert seeded_tags[0].id in [x.id for x in returned_item.tags]

    # Get the updated item and verify the changes are persisted
    fetched_item = client.inventory.get_by_id(id=updated_inventory_item.id)
    assert fetched_item.cas[0].id == seeded_cas[1].id
    assert fetched_item.cas[0].min == 0.5
    assert fetched_item.cas[0].max == 0.75
    assert fetched_item.company.id == seeded_inventory[1].company.id
    assert len(fetched_item.tags) == 2
    assert seeded_tags[1].id in [x.id for x in fetched_item.tags]
    assert seeded_tags[0].id in [x.id for x in fetched_item.tags]

    # Update existing values

    fetched_item.cas = [
        CasAmount(id=seeded_cas[1].id, min=0.1, max=0.5),
        CasAmount(id=seeded_cas[0].id, min=0.4, max=0.9),
    ]
    fetched_item.company = seeded_companies[0]
    fetched_item.tags = [seeded_tags[0]]

    returned_item = client.inventory.update(inventory_item=fetched_item)

    for c in returned_item.cas:
        if c.id == seeded_cas[1].id:
            assert c.min == 0.1
            assert c.max == 0.5
        elif c.id == seeded_cas[0].id:
            assert c.min == 0.4
            assert c.max == 0.9

    assert returned_item.company.id == seeded_inventory[0].company.id
    assert len(returned_item.tags) == 1
    assert seeded_tags[0].id in [x.id for x in returned_item.tags]

    # remove an existing Cas
    fetched_item.cas = [CasAmount(id=seeded_cas[0].id, min=0.4, max=0.9)]
    returned_item = client.inventory.update(inventory_item=fetched_item)
    assert len(returned_item.cas) == 1
    # You can't unset a company
    with pytest.raises(BadRequestError):
        fetched_item.company = None
        client.inventory.update(inventory_item=fetched_item)


def test_get_facets(client: Albert):
    facets = client.inventory.get_all_facets()
    assert len(facets) > 0
    expected_facets = [
        "Category",
        "Manufacturer",
        "Location",
        "Storage Location",
        "CAS Number",
        "Tags",
        "Pictograms",
        "Quarantine Status",
        "Created By",
        "Lot Owner",
        "Lot Created By",
    ]
    for facet in facets:
        assert isinstance(facet, FacetItem)
        assert facet.name in expected_facets

    assert isinstance(facets[0].value[0], FacetValue)


def test_get_facet_by_name(client: Albert):
    facets = client.inventory.get_facet_by_name("Category")
    assert isinstance(facets, list)
    assert len(facets) > 0
    assert isinstance(facets[0], FacetItem)
    assert facets[0].name == "Category"

    facets = client.inventory.get_facet_by_name(["Category", "Manufacturer"])
    assert len(facets) == 2
    assert facets[0].name == "Category"
    assert facets[1].name == "Manufacturer"

    # The list order is not preserved, the API always returns facets in the same order
    facets = client.inventory.get_facet_by_name(["Manufacturer", "Category"])
    assert len(facets) == 2
    assert facets[0].name == "Category"
    assert facets[1].name == "Manufacturer"


def test_get_search_records(
    client: Albert, seeded_inventory: list[InventoryItem], seeded_tags: list[Tag]
):
    res = client.inventory.search(
        tags=[x.tag for x in seeded_tags[:2]], match_all_conditions=True, limit=100
    )
    c = 0
    for x in res:
        assert ensure_inventory_id(x.id) in [y.id for y in seeded_inventory]
        c += 1
    assert c == 1
