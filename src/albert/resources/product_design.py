from pydantic import Field

from albert.core.base import BaseAlbertModel


class CasLevelSubstance(BaseAlbertModel):
    """A CAS-level substance reference within a product design.

    Attributes
    ----------
    cas_primary_key_id : str | None
        The primary key ID of the CAS entry.
    cas_id : str | None
        The Albert ID of the CAS entry.
    amount : float | None
        The amount of this substance in the formulation.
    """

    cas_primary_key_id: str | None = Field(default=None, alias="casPrimaryKeyId")
    cas_id: str | None = Field(default=None, alias="casID")
    amount: float | None = Field(default=None)


class NormalizedCAS(BaseAlbertModel):
    """A normalized CAS entry with computed amount within a product design.

    Attributes
    ----------
    name : str | None
        The name of the CAS substance.
    value : float | None
        The normalized amount value.
    albert_id : str | None
        The Albert ID of the CAS entry.
    smiles : str | None
        The SMILES notation for the substance.
    """

    name: str | None = Field(default=None)
    value: float | None = Field(default=None)
    albert_id: str | None = Field(default=None, alias="albertId")
    smiles: str | None = Field(default=None)


class UnpackedInventorySDS(BaseAlbertModel):
    """SDS summary for an inventory item within an unpacked product design.

    Attributes
    ----------
    albert_id : str | None
        The Albert ID of the inventory item.
    value : float | None
        The amount of this item in the formulation.
    sds_class : str | None
        The SDS/storage class identifier.
    un_number : str | None
        The UN number for hazardous materials.
    """

    albert_id: str | None = Field(default=None, alias="albertId")
    value: float | None = Field(default=None)
    sds_class: str | None = Field(default=None, alias="class")
    un_number: str | None = Field(default=None, alias="unNumber")


class UnpackedCasInfo(BaseAlbertModel):
    """CAS composition information for an ingredient in an unpacked product design.

    Attributes
    ----------
    id : str | None
        The Albert ID of the CAS entry.
    name : str | None
        The name of the CAS substance.
    min : float | None
        The minimum amount of this CAS in the formulation.
    max : float | None
        The maximum amount of this CAS in the formulation.
    number : str | None
        The CAS registry number.
    cas_average : float | None
        The average computed CAS amount.
    cas_sum : float | None
        The summed CAS amount across all occurrences.
    """

    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    min: float | None = Field(default=None)
    max: float | None = Field(default=None)
    number: str | None = Field(default=None)
    cas_average: float | None = Field(default=None, alias="casAvg")
    cas_sum: float | None = Field(default=None, alias="casSum")


class UnpackedInventoryListItem(BaseAlbertModel):
    """A single cell reference in an unpacked product design grid.

    Attributes
    ----------
    row_inventory_id : str | None
        The inventory ID of the row.
    value : float | None
        The cell value.
    column_id : str | None
        The column identifier in the design grid.
    column_inventory_id : str | None
        The inventory ID of the column (formulation).
    parent_id : str | None
        The parent design identifier.
    row_id : str | None
        The row identifier in the design grid.
    """

    row_inventory_id: str | None = Field(default=None, alias="rowInventoryId")
    value: float | None = Field(default=None)
    column_id: str | None = Field(default=None, alias="colId")
    column_inventory_id: str | None = Field(default=None, alias="colInventoryId")
    parent_id: str | None = Field(default=None, alias="parentId")
    row_id: str | None = Field(default=None, alias="rowId")


class UnpackedInventory(UnpackedInventoryListItem):
    """An ingredient row in an unpacked product design, with SDS and CAS details.

    Attributes
    ----------
    id : str | None
        The Albert ID of the inventory item.
    name : str | None
        The name of the inventory item.
    rsn_number : str | None
        The RSN (regulatory substance) number.
    total_cas_sum : float | None
        The total sum of all CAS amounts for this ingredient.
    value : float | None
        The amount of this ingredient in the formulation.
    sds_info : UnpackedInventorySDS | None
        SDS information for this ingredient.
    cas_info : list[UnpackedCasInfo] | None
        CAS composition details for this ingredient.
    """

    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    rsn_number: str | None = Field(default=None, alias="rsnNumber")
    total_cas_sum: float | None = Field(default=None, alias="totalCasSum")
    value: float | None = Field(default=None)
    sds_info: UnpackedInventorySDS | None = Field(default=None, alias="sdsInfo")
    cas_info: list[UnpackedCasInfo] | None = Field(default=None, alias="casInfo")


class UnpackedProductDesign(BaseAlbertModel):
    """The fully expanded product design data, including ingredient and CAS breakdowns.

    Attributes
    ----------
    inventories : list[UnpackedInventory] | None
        The ingredient rows with SDS and CAS details.
    inventory_list : list[UnpackedInventoryListItem] | None
        Raw grid cell references for all inventory items.
    inventory_sds_list : list[UnpackedInventorySDS] | None
        SDS summaries for all inventory items in the design.
    cas_level_substances : list[CasLevelSubstance] | None
        CAS-level substance entries computed from the formulation.
    normalized_cas_list : list[NormalizedCAS] | None
        Normalized CAS amounts computed across the formulation.
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
