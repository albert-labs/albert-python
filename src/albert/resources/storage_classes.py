from pydantic import Field

from albert.core.base import BaseAlbertModel


class StorageCompatibilityMatrix(BaseAlbertModel):
    allowed: list[str] | None = Field(default_factory=list, alias="Allowed")
    not_allowed: list[str] | None = Field(default_factory=list, alias="NotAllowed")
    warnings: dict[str, list[str]] | None = Field(default_factory=dict, alias="Warnings")


class StorageClass(BaseAlbertModel):
    storage_class_name: str | None = Field(default=None, alias="storageClassName")
    storage_class_number: str | None = Field(default=None, alias="storageClassNumber")
    storage_compatibility: StorageCompatibilityMatrix | None = Field(
        default=None, alias="StorageCompatibility"
    )
