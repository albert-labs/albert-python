from pydantic import Field

from albert.core.base import BaseAlbertModel


class CasLevelSubstance(BaseAlbertModel):
    """A single CAS-level substance in an unpacked product's composition.

    Attributes
    ----------
    cas_primary_key_id : str, optional
        Internal key identifying the CAS record for this substance.
    cas_id : str, optional
        The CAS identifier for the substance (format ``CAS...``).
    amount : float, optional
        The amount of this substance in the unpacked composition.
    """

    cas_primary_key_id: str | None = Field(default=None, alias="casPrimaryKeyId")
    cas_id: str | None = Field(default=None, alias="casID")
    amount: float | None = Field(default=None)


class NormalizedCAS(BaseAlbertModel):
    """A CAS entry with its normalized proportion in the unpacked product.

    Attributes
    ----------
    name : str, optional
        The name of the CAS substance.
    value : float, optional
        The normalized amount of this CAS substance in the product.
    albert_id : str, optional
        The Albert identifier for the CAS record.
    smiles : str, optional
        The SMILES string describing the substance's chemical structure.
    """

    name: str | None = Field(default=None)
    value: float | None = Field(default=None)
    albert_id: str | None = Field(default=None, alias="albertId")
    smiles: str | None = Field(default=None)


class UnpackedInventorySDS(BaseAlbertModel):
    """Safety data sheet (SDS) and regulatory details for an unpacked ingredient.

    Attributes
    ----------
    albert_id : str, optional
        The Albert identifier this SDS information belongs to.
    value : float, optional
        The amount associated with this SDS entry.
    sds_class : str, optional
        The SDS hazard classification.
    un_number : str, optional
        The UN number used for transport / regulatory classification.
    """

    albert_id: str | None = Field(default=None, alias="albertId")
    value: float | None = Field(default=None)
    sds_class: str | None = Field(default=None, alias="class")
    un_number: str | None = Field(default=None, alias="unNumber")


class UnpackedCasInfo(BaseAlbertModel):
    """CAS composition detail for an ingredient in an unpacked product.

    Attributes
    ----------
    id : str, optional
        The Albert identifier for the CAS record.
    name : str, optional
        The name of the CAS substance.
    min : float, optional
        The minimum proportion of this substance in the ingredient.
    max : float, optional
        The maximum proportion of this substance in the ingredient.
    number : str, optional
        The CAS registry number (e.g. ``"7732-18-5"``).
    cas_average : float, optional
        The averaged CAS proportion.
    cas_sum : float, optional
        The summed CAS proportion.
    """

    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    min: float | None = Field(default=None)
    max: float | None = Field(default=None)
    number: str | None = Field(default=None)
    cas_average: float | None = Field(default=None, alias="casAvg")
    cas_sum: float | None = Field(default=None, alias="casSum")


class UnpackedInventoryListItem(BaseAlbertModel):
    """A single flattened ingredient entry linking a formula cell to an item.

    Represents one row/column position in the unpacked formula together with the
    inventory item at that position and its amount.

    Attributes
    ----------
    row_inventory_id : str, optional
        The Inventory ID of the item on this row.
    value : float, optional
        The amount contributed by this entry.
    column_id : str, optional
        The identifier of the formula column this entry belongs to.
    column_inventory_id : str, optional
        The Inventory ID associated with the column.
    parent_id : str, optional
        The identifier of the parent formula this entry was unpacked from.
    row_id : str, optional
        The identifier of the row this entry belongs to.
    """

    row_inventory_id: str | None = Field(default=None, alias="rowInventoryId")
    value: float | None = Field(default=None)
    column_id: str | None = Field(default=None, alias="colId")
    column_inventory_id: str | None = Field(default=None, alias="colInventoryId")
    parent_id: str | None = Field(default=None, alias="parentId")
    row_id: str | None = Field(default=None, alias="rowId")


class UnpackedInventory(UnpackedInventoryListItem):
    """A fully unpacked ingredient (inventory item) within a product.

    Extends [`UnpackedInventoryListItem`][albert.resources.product_design.UnpackedInventoryListItem] with the item's identity plus its
    resolved SDS information and CAS-level breakdown.

    Attributes
    ----------
    id : str, optional
        The Inventory ID of the ingredient (format ``INV...``).
    name : str, optional
        The name of the ingredient.
    rsn_number : str, optional
        The RSN (registered substance) number for the ingredient.
    total_cas_sum : float, optional
        The summed CAS proportion across the ingredient's constituents.
    value : float, optional
        The amount of this ingredient in the unpacked product.
    sds_info : UnpackedInventorySDS, optional
        The SDS / regulatory details for the ingredient.
    cas_info : list[UnpackedCasInfo], optional
        The CAS-level composition breakdown for the ingredient.
    """

    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    rsn_number: str | None = Field(default=None, alias="rsnNumber")
    total_cas_sum: float | None = Field(default=None, alias="totalCasSum")
    value: float | None = Field(default=None)
    sds_info: UnpackedInventorySDS | None = Field(default=None, alias="sdsInfo")
    cas_info: list[UnpackedCasInfo] | None = Field(default=None, alias="casInfo")


class UnpackedProductDesign(BaseAlbertModel):
    """The full unpacked composition of a single formulated product.

    Returned by
    [`get_unpacked_products`][albert.collections.product_design.ProductDesignCollection.get_unpacked_products],
    one per formula that was unpacked. Unpacking recursively resolves the
    formulation's ingredient tree into two views: a row-level inventory list (the
    direct worksheet ingredients, some of which may be sub-formulations) and a flat
    CAS-level substance list (fully resolved raw materials with combined weight
    fractions). This object gathers the resolved ingredients, the flattened
    ingredient list, SDS details, and the CAS-level substance rollup.

    Attributes
    ----------
    inventories : list[UnpackedInventory], optional
        The resolved ingredients making up the product, each with its SDS and
        CAS breakdown.
    inventory_list : list[UnpackedInventoryListItem], optional
        The flattened list of ingredient entries by formula position.
    inventory_sds_list : list[UnpackedInventorySDS], optional
        The SDS / regulatory details collected across the ingredients.
    cas_level_substances : list[CasLevelSubstance], optional
        The product's composition expressed as individual CAS-level substances
        and their amounts.
    normalized_cas_list : list[NormalizedCAS], optional
        The CAS substances with their normalized proportions in the product.
    """

    inventories: list[UnpackedInventory] | None = Field(default=None, alias="Inventories")
    inventory_list: list[UnpackedInventoryListItem] | None = Field(
        default=None, alias="inventoryList"
    )
    inventory_sds_list: list[UnpackedInventorySDS] | None = Field(
        default=None, alias="inventorySDSList"
    )
    cas_level_substances: list[CasLevelSubstance] | None = Field(
        default=None, alias="casLevelSubstances"
    )
    normalized_cas_list: list[NormalizedCAS] | None = Field(
        default=None, alias="normalizedCasList"
    )
