from collections.abc import Generator

import pytest

from albert.albert import Albert
from albert.collections.inventory import InventoryCategory
from albert.resources.cas import Cas
from albert.resources.companies import Company
from albert.resources.inventory import CasAmount, InventoryItem, InventoryUnitCategory
from albert.resources.tags import Tag
from albert.utils.exceptions import BadRequestError


def _list_asserts(returned_list):
    for i, u in enumerate(returned_list):
        if i == 50:
            break
        assert isinstance(u, InventoryItem)
        assert isinstance(u.name, str | None)
        assert isinstance(u.id, str)


def test_simple_inventory_list(client: Albert, seeded_inventory):
    inventory = client.inventory.list()
    assert isinstance(inventory, Generator)
    _list_asserts(inventory)


def test_advanced_inventory_list(
    client: Albert, seeded_inventory: list[InventoryItem], seeded_cas: list[Cas]
):
    test_inv_item = seeded_inventory[1]
    matching_cas = [x for x in seeded_cas if x.id in test_inv_item.cas[0].id][0]
    inventory = client.inventory.list(
        name=test_inv_item.name,
        category=InventoryCategory.CONSUMABLES,
        cas=matching_cas,
        company=test_inv_item.company,
    )
    assert isinstance(inventory, Generator)
    _list_asserts(inventory)
    for i, x in enumerate(inventory):
        if i == 10:  # just check the first 10 for speed
            break
        assert "goggles" in x.name.lower()


def test_get_by_id(client: Albert, seeded_inventory):
    get_by_id = client.inventory.get_by_id(inventory_id=seeded_inventory[1].id)
    assert isinstance(get_by_id, InventoryItem)
    assert seeded_inventory[1].name == get_by_id.name
    assert seeded_inventory[1].id == get_by_id.id

    id_2 = seeded_inventory[0].id.replace("INV", "")
    get_by_id = client.inventory.get_by_id(inventory_id=id_2)
    assert isinstance(get_by_id, InventoryItem)
    assert seeded_inventory[0].name == get_by_id.name
    assert seeded_inventory[0].id == get_by_id.id


def test_get_by_ids(client: Albert, seeded_inventory):
    inventory_ids = [x.id for x in seeded_inventory]

    bulk_get = client.inventory.get_by_ids(inventory_ids=inventory_ids)
    assert {x.id for x in bulk_get} == set(inventory_ids)

    inventory_ids_bare = [x.replace("INV", "") for x in inventory_ids]
    bulk_get_no_inv = client.inventory.get_by_ids(inventory_ids=inventory_ids_bare)
    assert {x.id for x in bulk_get_no_inv} == set(inventory_ids)


def test_inventory_update(client: Albert, seeded_inventory):
    assert client.inventory.inventory_exists(inventory_item=seeded_inventory[2])
    test_inv_item = seeded_inventory[2]
    d = "testing SDK CRUD"
    test_inv_item.description = d

    updated = client.inventory.update(updated_object=test_inv_item)
    assert updated.description == d
    assert updated.id == seeded_inventory[2].id

    client.inventory.delete(inventory_id=test_inv_item)
    assert not client.inventory.inventory_exists(inventory_item=test_inv_item)


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
    updated_item = client.inventory.update(updated_object=updated_inventory_item)

    # Verify that all updatable attributes have been updated
    assert updated_item.name == "Updated Inventory Name"
    assert updated_item.description == "Updated Description"
    assert updated_item.unit_category == InventoryUnitCategory.VOLUME.value
    assert updated_item.security_class == "confidential"
    assert updated_item.alias == "Updated Alias"

    # Optionally, re-fetch the item and verify the updates are persisted
    fetched_item = client.inventory.get_by_id(inventory_id=updated_inventory_item.id)
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
        }
    )

    returned_item = client.inventory.update(updated_object=updated_inventory_item)
    assert returned_item.cas[0].id == seeded_cas[1].id
    assert returned_item.cas[0].min == 0.5
    assert returned_item.cas[0].max == 0.75
    assert returned_item.company.id == seeded_inventory[1].company.id
    assert len(returned_item.tags) == 2
    assert seeded_tags[1].id in [x.id for x in returned_item.tags]
    assert seeded_tags[0].id in [x.id for x in returned_item.tags]

    # Get the updated item and verify the changes are persisted
    fetched_item = client.inventory.get_by_id(inventory_id=updated_inventory_item.id)
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

    returned_item = client.inventory.update(updated_object=fetched_item)

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
    returned_item = client.inventory.update(updated_object=fetched_item)
    assert len(returned_item.cas) == 1
    # You can't unset a company
    with pytest.raises(BadRequestError):
        fetched_item.company = None
        client.inventory.update(updated_object=fetched_item)
