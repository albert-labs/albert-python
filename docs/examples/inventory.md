# Inventory

Albert Inventory serves as a digital manifestation of your physical inventory. It enables you to sort, filter, trace, and manage all types of inventory.

## Inventory function on CAS

Inventory function is a business-controlled, multi-select list on the Inventory ↔ CAS relationship.
Use it by updating an existing inventory item.

!!! example "Add inventory function values to a CAS entry"
    ```python
    from albert import Albert
    from albert.resources.lists import ListItem, ListItemCategory

    client = Albert.from_client_credentials()

    inventory_id = "INV123"
    cas_id = "CAS123"

    # Optional: create a new inventoryFunction list item first.
    list_item = ListItem(
        name="Primary Function",
        category=ListItemCategory.INVENTORY,
        list_type="inventoryFunction",
    )
    list_item = client.lists.create(list_item=list_item)

    inventory_item = client.inventory.get_by_id(id=inventory_id)
    if inventory_item.cas:
        for cas_amount in inventory_item.cas:
            if cas_amount.id == cas_id:
                cas_amount.inventory_function = [list_item]
                break

    updated_item = client.inventory.update(inventory_item=inventory_item)
    print(updated_item.id)
    ```
