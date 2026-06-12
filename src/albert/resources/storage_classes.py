from pydantic import Field

from albert.core.base import BaseAlbertModel


class StorageCompatibilityMatrix(BaseAlbertModel):
    """Compatibility rules between storage classes.

    Attributes
    ----------
    allowed : list[str] | None
        Storage class names or numbers that can be co-stored together.
    not_allowed : list[str] | None
        Storage class names or numbers that must not be co-stored.
    warnings : dict[str, list[str]] | None
        Storage class combinations that require caution, with warning messages.
    """

    allowed: list[str] | None = Field(default_factory=list, alias="Allowed")
    not_allowed: list[str] | None = Field(default_factory=list, alias="NotAllowed")
    warnings: dict[str, list[str]] | None = Field(default_factory=dict, alias="Warnings")


class StorageClass(BaseAlbertModel):
    """A chemical storage class with its compatibility rules.

    Attributes
    ----------
    storage_class_name : str | None
        The human-readable name of the storage class.
    storage_class_number : str | None
        The numeric identifier of the storage class.
    storage_compatibility : StorageCompatibilityMatrix | None
        Compatibility rules with other storage classes.
    """

    storage_class_name: str | None = Field(default=None, alias="storageClassName")
    storage_class_number: str | None = Field(default=None, alias="storageClassNumber")
    storage_compatibility: StorageCompatibilityMatrix | None = Field(
        default=None, alias="StorageCompatibility"
    )
