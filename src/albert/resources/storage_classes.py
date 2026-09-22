from pydantic import Field

from albert.core.base import BaseAlbertModel


class StorageCompatibilityMatrix(BaseAlbertModel):
    """Co-storage compatibility for a single Storage Class.

    Describes which other storage classes a given class may be stored alongside.
    Each entry identifies another storage class (by name or number)."""

    allowed: list[str] | None = Field(default_factory=list, alias="Allowed")
    """Storage classes that may be safely co-stored with this class."""

    not_allowed: list[str] | None = Field(default_factory=list, alias="NotAllowed")
    """Storage classes that must not be co-stored with this class."""

    warnings: dict[str, list[str]] | None = Field(default_factory=dict, alias="Warnings")
    """Storage classes that may be co-stored only with caution, keyed by the other class, with the list describing the applicable warnings."""


class StorageClass(BaseAlbertModel):
    """A hazardous-materials storage classification.

    A Storage Class governs which materials may be safely stored together.
    Inventory Items carry a storage/security class that ties back to one of these
    classifications. Retrieved through
    [`StorageClassesCollection`][albert.collections.storage_classes.StorageClassesCollection]."""

    storage_class_name: str | None = Field(default=None, alias="storageClassName")
    """The human-readable name of the storage class."""

    storage_class_number: str | None = Field(default=None, alias="storageClassNumber")
    """The identifying number/code of the storage class within its classification scheme."""

    storage_compatibility: StorageCompatibilityMatrix | None = Field(
        default=None, alias="StorageCompatibility"
    )
    """The co-storage compatibility matrix for this class, listing which other classes it may, may not, or may with warnings be stored alongside."""
