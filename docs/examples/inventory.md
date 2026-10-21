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

## Search inventory via metadata/custom fields

!!! example "Search inventory using metadata filters"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    items = client.inventory.search(
        metadata_filters={
            "batchCode": ["B-100", "B-200"],
            "grade": {"name": ["Premium"]},
        },
    )
    # batchCode is a string-type custom field.
    # grade is a list-type custom field.

    for item in items:
        print(item)
    ```

Keys are custom field names. String-type custom fields take a list of values; list-type custom fields take a `{"name": [...]}` dict of list item names. Multiple values on one field match any of them (OR); different fields must all match (AND). The same `metadata_filters` shape is supported on `search()` for projects, tasks, lots, parameter groups, data templates, data columns, and users.
