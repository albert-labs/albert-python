# Substances V4

The `substances_v4` collection wraps the Albert v4 substance API, which exposes hazard data, custom tenant metadata, and structural identifiers at the CAS level.

## Update metadata

Use `update_metadata` to change specific fields on a tenant substance. Only the keyword arguments you pass are updated — everything else on the substance is left as-is.

!!! example "Update scalar fields"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    client.substances_v4.update_metadata(
        id="SUB123",
        notes="Revised safety notes",
        description="Aqueous solvent",
        cas_smiles="O",
    )
    ```

!!! example "Update a custom string metadata field"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    client.substances_v4.update_metadata(
        id="SUB123",
        metadata={"solubility": "5 mg/mL"},
    )
    ```

!!! example "Update a single-select custom metadata field"
    Single-select fields take an `EntityLink` whose `id` is the list item ID. Use `client.lists.get_all()` or `client.lists.get_matching_item()` to look up IDs.

    ```python
    from albert import Albert
    from albert.resources.base import EntityLink

    client = Albert.from_client_credentials()

    client.substances_v4.update_metadata(
        id="SUB123",
        metadata={"cmr_eu": EntityLink(id="LST1253")},
    )
    ```

!!! example "Update a multi-select custom metadata field"
    Multi-select fields take a list of `EntityLink` objects representing the desired selection.

    ```python
    from albert import Albert
    from albert.resources.base import EntityLink

    client = Albert.from_client_credentials()

    client.substances_v4.update_metadata(
        id="SUB123",
        metadata={
            "amide_category": [
                EntityLink(id="LST1256"),
                EntityLink(id="LST1257"),
            ]
        },
    )
    ```

!!! example "Delete a custom metadata field"
    Pass `None` as the value to remove a custom field (works for string, single-select, and multi-select fields).

    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    client.substances_v4.update_metadata(
        id="SUB123",
        metadata={"deprecated_field": None},
    )
    ```

!!! example "Mix scalar and custom field updates in one call"
    ```python
    from albert import Albert
    from albert.resources.base import EntityLink

    client = Albert.from_client_credentials()

    client.substances_v4.update_metadata(
        id="SUB123",
        notes="Updated notes",
        metadata={
            "solubility": "10 mg/mL",
            "cmr_eu": EntityLink(id="LST1253"),
            "old_field": None,          # deletes this custom field
        },
    )
    ```
