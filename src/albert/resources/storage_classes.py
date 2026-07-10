from pydantic import Field

from albert.core.base import BaseAlbertModel


class StorageCompatibilityMatrix(BaseAlbertModel):
    """Co-storage compatibility for a single Storage Class.

    Describes which other storage classes a given class may be stored alongside.
    Each entry identifies another storage class (by name or number).

    Attributes
    ----------
    allowed : list[str] | None
        Storage classes that may be safely co-stored with this class.
    not_allowed : list[str] | None
        Storage classes that must not be co-stored with this class.
    warnings : dict[str, list[str]] | None
        Storage classes that may be co-stored only with caution, keyed by the
        other class, with the list describing the applicable warnings.
    """

    allowed: list[str] | None = Field(default_factory=list, alias="Allowed")
    not_allowed: list[str] | None = Field(default_factory=list, alias="NotAllowed")
    warnings: dict[str, list[str]] | None = Field(default_factory=dict, alias="Warnings")


class StorageClass(BaseAlbertModel):
    """A hazardous-materials storage classification.

    A Storage Class governs which materials may be safely stored together.
    Inventory Items carry a storage/security class that ties back to one of these
    classifications. Retrieved through
    :class:`~albert.collections.storage_classes.StorageClassesCollection`.

    Attributes
    ----------
    storage_class_name : str | None
        The human-readable name of the storage class.
    storage_class_number : str | None
        The identifying number/code of the storage class within its
        classification scheme.
    storage_compatibility : StorageCompatibilityMatrix | None
        The co-storage compatibility matrix for this class, listing which other
        classes it may, may not, or may with warnings be stored alongside.
    """

    storage_class_name: str | None = Field(default=None, alias="storageClassName")
    storage_class_number: str | None = Field(default=None, alias="storageClassNumber")
    storage_compatibility: StorageCompatibilityMatrix | None = Field(
        default=None, alias="StorageCompatibility"
    )
