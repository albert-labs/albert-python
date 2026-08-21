from pydantic import Field

from albert.core.shared.models.base import BaseAlbertModel, BaseResource
from albert.core.shared.types import SerializeAsEntityLink
from albert.resources.locations import Location


class StorageLocation(BaseResource):
    """A specific place where an Inventory Item is physically stored.

    Examples include a flammables cabinet, a freezer, or a storeroom shelf. Every
    storage location belongs to a parent Location
    ([`Location`][albert.resources.locations.Location]), and Inventory search filters
    can narrow results to items held in a given storage location. Managed through
    [`StorageLocationsCollection`][albert.collections.storage_locations.StorageLocationsCollection].

    !!! example
        ```python
        from albert import Albert
        from albert.resources.storage_locations import StorageLocation
        client = Albert()
        parent = client.locations.get_by_id(id="...")
        storage_location = StorageLocation(name="Freezer A", location=parent)
        ```"""

    name: str = Field(alias="name", min_length=2, max_length=255)
    """The human-readable name of the storage location (2 to 255 characters)."""

    id: str | None = Field(alias="albertId", default=None)
    """The Albert ID of the storage location (format ``STL...``). Assigned by Albert and populated once the storage location has been created or retrieved."""

    location: SerializeAsEntityLink[Location] = Field(alias="Location")
    """The parent Location this storage location belongs to."""


class StorageLocationFilter(BaseAlbertModel):
    """A name-based storage location filter for inventory search.

    Inventory search and listing serialize the storage location filter by
    storage-location name only, so unlike [`StorageLocation`][albert.resources.storage_locations.StorageLocation]
    (the create/update type, which requires a parent ``location``) this filter
    needs just the exact unit name.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.storage_locations import StorageLocationFilter
        client = Albert()
        items = client.inventory.search(
            storage_location=[StorageLocationFilter(name="Freezer A")]
        )
        ```"""

    name: str = Field(min_length=2, max_length=255)
    """The exact name of the storage location to filter by (2 to 255 characters)."""
