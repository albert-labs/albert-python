from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.inventory import InventoryCollection
from albert.collections.product_design import ProductDesignCollection
from albert.core.session import AlbertSession
from albert.exceptions import AlbertException
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.resources.sds import (
    GeneratedSDS,
    SDSDataEntity,
    SDSFieldOptions,
    SDSLegalEntity,
    SDSRequest,
    _composition_from_unpacked,
)


def _require_formula_inventory(item: InventoryItem) -> None:
    if item.category != InventoryCategory.FORMULAS:
        raise AlbertException(
            f"SDS generation is available for formula inventory items only, not {item.category}."
        )


class SDSCollection(BaseCollection):
    """Manage SDS generation for formula inventory items in the Albert platform (🧪 Beta).

    Generate a GHS Safety Data Sheet (JSON plus PDF) for a **formula** inventory
    item. Lookups (jurisdictions, languages, physical states, products, legal
    entities, field options) are tenant-specific; language and legal entity are
    also region-scoped. Always send lookup **values** on
    [`SDSRequest`][albert.resources.sds.SDSRequest], not display names.

    [`generate_sds`][albert.collections.sds.SDSCollection.generate_sds] always
    loads the inventory name and unpacks the formula for ingredients, CAS-level
    composition, and inventory SDS rows. Callers do not supply those lists. This
    collection does not generate SDS for raw materials.

    This collection is accessed as ``client.sds``. Do not use
    [`attachments.get_jurisdiction_codes`][albert.collections.attachments.AttachmentCollection.get_jurisdiction_codes]
    or
    [`attachments.get_language_codes`][albert.collections.attachments.AttachmentCollection.get_language_codes]
    for generate; those tag uploaded PDFs. To attach an existing SDS PDF, use
    [`upload_and_attach_sds_to_inventory_item`][albert.collections.attachments.AttachmentCollection.upload_and_attach_sds_to_inventory_item].

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert.
        This feature currently falls outside of the Albert support contract, but
        we'd love your feedback!

    !!! example
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
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for document-generator SDS requests.

    Methods
    -------
    generate_sds(sds) -> GeneratedSDS
        Generate an SDS for a formula inventory item.
    get_field_options(entity, region=None, physical_state=None, flammability=None, template=None) -> SDSFieldOptions
        Get tenant-specific options for one SDS input field.
    get_physical_states() -> dict[str, str]
        Get physical-state display names mapped to codes.
    get_products(region=None, physical_state=None) -> dict[str, str]
        Get product-type display names mapped to codes.
    get_languages(region) -> dict[str, str]
        Get language display names mapped to codes for a jurisdiction.
    get_jurisdictions(region=None) -> dict[str, str]
        Get jurisdiction display names mapped to codes.
    get_jurisdiction_groups() -> dict[str, list[str]]
        Get jurisdictions grouped by category.
    get_legal_entities(region) -> list[SDSLegalEntity]
        Get legal entities for a jurisdiction.
    """

    _api_version = "v2"

    def __init__(self, *, session: AlbertSession):
        """Initialize an SDSCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{SDSCollection._api_version}/documentgenerator"
        self._rule_engine_path = f"/api/{SDSCollection._api_version}/sdsruleengine"

    @validate_call
    def generate_sds(self, *, sds: SDSRequest) -> GeneratedSDS:
        """Generate an SDS for a formula inventory item.

        Always unpacks the formula (same as the Albert UI) and fills the product
        name, ingredients, CAS-level composition, and inventory SDS rows. Callers
        supply the formula Albert ID and lookup codes only.

        Formula inventory only. Region, language, product type, physical state,
        and legal entity must already be lookup **values**. The product name is
        taken from the inventory item.

        The returned PDF URL is a short-lived download link. This is the SDS
        generate workflow; do not call
        [`PDFGeneratorCollection`][albert.collections.pdf_generator.PDFGeneratorCollection]
        for SDS.

        !!! example
            ```python
            result = client.sds.generate_sds(sds=sds)
            result.sds_json["section1"]
            result.pdf_url
            # 'https://...'
            ```

        Parameters
        ----------
        sds : SDSRequest
            The SDS generate request. Product name and formula composition are
            taken from the inventory item and unpack.

        Returns
        -------
        GeneratedSDS
            The generated SDS JSON, PDF URL, and metadata URL.

        Raises
        ------
        AlbertException
            If the inventory item is not a formula, or unpack returns no products.
        """
        item = InventoryCollection(session=self.session).get_by_id(id=sds.albert_id)
        _require_formula_inventory(item)
        unpacked = ProductDesignCollection(session=self.session).get_unpacked_products(
            inventory_ids=[sds.albert_id],
            unpack_id="DESIGN",
        )
        if not unpacked:
            raise AlbertException("Unpack returned no products for this formula inventory id.")
        composition = _composition_from_unpacked(unpacked[0])
        payload = sds.model_dump(by_alias=True, mode="json", exclude_none=True)
        payload["name"] = item.name or payload["albertID"]
        payload["substances"] = composition["substances"]
        payload["casLevelSubstances"] = composition["cas_level_substances"]
        payload["inventorySDSList"] = composition["inventory_sds_list"]
        response = self.session.post(f"{self.base_path}/sds", json=payload)
        return GeneratedSDS.model_validate(response.json())

    @validate_call
    def get_field_options(
        self,
        *,
        entity: SDSDataEntity | str,
        region: str | None = None,
        physical_state: str | None = None,
        flammability: str | None = None,
        template: str | None = None,
    ) -> SDSFieldOptions:
        """Get tenant-specific options for one SDS input field.

        Entity query names do not always match [`SDSRequest`][albert.resources.sds.SDSRequest]
        field names (e.g. ``flashpoint`` → ``flash_point``). If ``display`` is
        false, omit the field. If ``data`` is a list of objects with ``value``,
        send that ``value``.

        !!! example
            ```python
            from albert.resources.sds import SDSDataEntity

            options = client.sds.get_field_options(
                entity=SDSDataEntity.FLASHPOINT,
                region=region,
                physical_state=physical_state,
            )
            options.display
            ```

        Parameters
        ----------
        entity : SDSDataEntity or str
            The field-options entity name.
        region : str, optional
            Jurisdiction code. Required for some entities (e.g. flash point).
        physical_state : str, optional
            Physical-state code used to filter options.
        flammability : str, optional
            Flammability code used to filter burning-test options.
        template : str, optional
            Template ID used to filter some tenant-gated fields.

        Returns
        -------
        SDSFieldOptions
            Display flag, required flag, and allowed values.
        """
        entity_value = entity.value if isinstance(entity, SDSDataEntity) else entity
        params: dict[str, Any] = {
            "entity": entity_value,
            "region": region,
            "physicalState": physical_state,
            "flammability": flammability,
            "template": template,
        }
        params = {k: v for k, v in params.items() if v is not None}
        payload = self.session.get(f"{self.base_path}/data", params=params).json()
        if isinstance(payload, list):
            return SDSFieldOptions(data=payload, display=True)
        return SDSFieldOptions.model_validate(payload)

    @validate_call
    def get_physical_states(self) -> dict[str, str]:
        """Get physical-state display names mapped to codes.

        Tenant-specific. Send the **values** (e.g. ``"liquid"``) as
        [`SDSRequest.physical_state`][albert.resources.sds.SDSRequest.physical_state].

        !!! example
            ```python
            states = client.sds.get_physical_states()
            states["Liquid"]
            # 'liquid'
            ```

        Returns
        -------
        dict[str, str]
            Mapping of display name to code (e.g. ``{"Liquid": "liquid"}``).
        """
        return self.session.get(f"{self._rule_engine_path}/physicalStates").json()

    @validate_call
    def get_products(
        self,
        *,
        region: str | None = None,
        physical_state: str | None = None,
    ) -> dict[str, str]:
        """Get product-type display names mapped to codes.

        Tenant-specific and optionally filtered by jurisdiction and physical
        state. Send the **values** (e.g. ``"acrylate"``) as
        [`SDSRequest.product_type`][albert.resources.sds.SDSRequest.product_type].

        !!! example
            ```python
            products = client.sds.get_products(region=region, physical_state=physical_state)
            products["Acrylate"]
            # 'acrylate'
            ```

        Parameters
        ----------
        region : str, optional
            Jurisdiction code used to filter product types.
        physical_state : str, optional
            Physical-state code used to filter product types.

        Returns
        -------
        dict[str, str]
            Mapping of display name to code.
        """
        params: dict[str, Any] = {"region": region, "physicalState": physical_state}
        params = {k: v for k, v in params.items() if v is not None}
        return self.session.get(f"{self._rule_engine_path}/products", params=params).json()

    @validate_call
    def get_languages(self, *, region: str) -> dict[str, str]:
        """Get language display names mapped to codes for a jurisdiction.

        Tenant-specific and region-scoped. Pass ``region="all"`` for the full
        set. Send the **values** (e.g. ``"EN"``) as
        [`SDSRequest.language`][albert.resources.sds.SDSRequest.language].

        Do not use
        [`get_language_codes`][albert.collections.attachments.AttachmentCollection.get_language_codes]
        for generate.

        !!! example
            ```python
            languages = client.sds.get_languages(region=region)
            languages["English"]
            # 'EN'
            ```

        Parameters
        ----------
        region : str
            Jurisdiction code, or ``"all"`` for every language.

        Returns
        -------
        dict[str, str]
            Mapping of display name to code (e.g. ``{"English": "EN"}``).
        """
        return self.session.get(
            f"{self._rule_engine_path}/languages", params={"region": region}
        ).json()

    @validate_call
    def get_jurisdictions(self, *, region: str | None = None) -> dict[str, str]:
        """Get jurisdiction display names mapped to codes.

        Tenant-specific. Omit ``region`` for the tenant list. Pass
        ``region="all"`` for the full set. Send the **values** (e.g. ``"US"``)
        as [`SDSRequest.region`][albert.resources.sds.SDSRequest.region].

        Do not use
        [`get_jurisdiction_codes`][albert.collections.attachments.AttachmentCollection.get_jurisdiction_codes]
        for generate. For grouped jurisdictions see
        [`get_jurisdiction_groups`][albert.collections.sds.SDSCollection.get_jurisdiction_groups].

        !!! example
            ```python
            jurisdictions = client.sds.get_jurisdictions()
            next(iter(jurisdictions.values()))
            ```

        Parameters
        ----------
        region : str, optional
            ``"all"`` for every jurisdiction. Omit for the tenant-configured list.

        Returns
        -------
        dict[str, str]
            Mapping of display name to code.
        """
        params = {"region": region} if region is not None else None
        return self.session.get(f"{self._rule_engine_path}/jurisdictions", params=params).json()

    @validate_call
    def get_jurisdiction_groups(self) -> dict[str, list[str]]:
        """Get jurisdictions grouped by category.

        !!! example
            ```python
            groups = client.sds.get_jurisdiction_groups()
            list(groups)
            ```

        Returns
        -------
        dict[str, list[str]]
            Mapping of category name to jurisdiction codes.
        """
        return self.session.get(
            f"{self._rule_engine_path}/jurisdictions", params={"region": "categorized"}
        ).json()

    @validate_call
    def get_legal_entities(self, *, region: str) -> list[SDSLegalEntity]:
        """Get legal entities for a jurisdiction.

        Tenant-specific and region-scoped. Send each row's ``value`` as
        [`SDSRequest.legal_entity`][albert.resources.sds.SDSRequest.legal_entity].

        !!! example
            ```python
            entities = client.sds.get_legal_entities(region=region)
            entities[0].value
            ```

        Parameters
        ----------
        region : str
            Jurisdiction code.

        Returns
        -------
        list[SDSLegalEntity]
            Legal entities available for the jurisdiction.
        """
        payload = self.session.get(
            f"{self._rule_engine_path}/legalEntities", params={"region": region}
        ).json()
        return [SDSLegalEntity.model_validate(item) for item in payload]
