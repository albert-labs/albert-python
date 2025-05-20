from pydantic import Field

from albert.resources.base import BaseAlbertModel


class CasLevelSubstance(BaseAlbertModel):
    cas_primary_key_id: str | None = Field(default=None, alias="casPrimaryKeyId")
    cas_id: str | None = Field(default=None, alias="casID")
    amount: float | None = Field(default=None)


class NormalizedCAS(BaseAlbertModel):
    name: str | None = Field(default=None)
    value: float | None = Field(default=None)
    albert_id: str | None = Field(default=None, alias="albertId")
    smiles: str | None = Field(default=None)


class UnpackedInventorySDS(BaseAlbertModel):
    albert_id: str | None = Field(default=None, alias="albertId")
    value: float | None = Field(default=None)
    sds_class: str | None = Field(default=None, alias="class")
    un_number: str | None = Field(default=None, alias="unNumber")


class UnpackedCasInfo(BaseAlbertModel):
    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    min: float | None = Field(default=None)
    max: float | None = Field(default=None)
    number: str | None = Field(default=None)
    cas_average: float | None = Field(default=None, alias="casAvg")
    cas_sum: float | None = Field(default=None, alias="casSum")


class UnpackedInventoryListItem(BaseAlbertModel):
    row_inventory_id: str | None = Field(default=None, alias="rowInventoryId")
    value: float | None = Field(default=None)
    column_id: str | None = Field(default=None, alias="colId")
    column_inventory_id: str | None = Field(default=None, alias="colInventoryId")
    parent_id: str | None = Field(default=None, alias="parentId")
    row_id: str | None = Field(default=None, alias="rowId")


class UnpackedInventory(UnpackedInventoryListItem):
    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    rsn_number: str | None = Field(default=None, alias="rsnNumber")
    total_cas_sum: float | None = Field(default=None, alias="totalCasSum")
    value: float | None = Field(default=None)
    sds_info: UnpackedInventorySDS | None = Field(default=None, alias="sdsInfo")
    cas_info: list[UnpackedCasInfo] | None = Field(default=None, alias="casInfo")


class UnpackedProductDesign(BaseAlbertModel):
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
