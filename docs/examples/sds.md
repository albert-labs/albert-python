# SDS (🧪 Beta)

Generate a GHS Safety Data Sheet for a **formula** inventory item. Lookups are tenant-specific; language and legal entity are also region-scoped. Always send lookup **values**, not display names.

!!! warning "Beta Feature!"
    Please do not use in production or without explicit guidance from Albert.
    This feature currently falls outside of the Albert support contract, but
    we'd love your feedback!

!!! example "Generate an SDS from lookup codes"
    ```python
    from albert import Albert
    from albert.resources.sds import SDSRequest

    client = Albert()

    region = next(iter(client.sds.get_jurisdictions().values()))
    language = next(iter(client.sds.get_languages(region=region).values()))
    physical_state = next(iter(client.sds.get_physical_states().values()))
    product_type = next(
        iter(client.sds.get_products(region=region, physical_state=physical_state).values())
    )
    legal_entity = client.sds.get_legal_entities(region=region)[0].value

    result = client.sds.generate_sds(
        sds=SDSRequest(
            albert_id="INVMO137681-012",
            region=region,
            language=language,
            product_type=product_type,
            physical_state=physical_state,
            legal_entity=legal_entity,
        )
    )
    result.pdf_url
    result.sds_json["section1"]
    ```

Leave name and composition off [`SDSRequest`][albert.resources.sds.SDSRequest].
[`generate_sds`][albert.collections.sds.SDSCollection.generate_sds] loads the
inventory name and unpacks the formula for ingredients, CAS, and inventory SDS
rows, matching the Albert UI.

To attach an existing SDS PDF to an inventory item, use
[`upload_and_attach_sds_to_inventory_item`][albert.collections.attachments.AttachmentCollection.upload_and_attach_sds_to_inventory_item].
Do not reuse
[`get_jurisdiction_codes`][albert.collections.attachments.AttachmentCollection.get_jurisdiction_codes]
or
[`get_language_codes`][albert.collections.attachments.AttachmentCollection.get_language_codes]
for generate.
