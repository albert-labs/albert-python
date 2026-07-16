from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import SerializeAsEntityLink
from albert.resources.locations import Location


class StorageLocation(BaseResource):
    """A specific place where an Inventory Item is physically stored.

    Examples include a flammables cabinet, a freezer, or a storeroom shelf. Every
    storage location belongs to a parent Location
    ([`Location`][albert.resources.locations.Location]), and Inventory search filters
    can narrow results to items held in a given storage location. Managed through
    [`StorageLocationsCollection`][albert.collections.storage_locations.StorageLocationsCollection].

    Attributes
    ----------
    name : str
        The human-readable name of the storage location (2 to 255 characters).
    id : str | None
        The Albert ID of the storage location (format ``STL...``). Assigned by
        Albert and populated once the storage location has been created or
        retrieved.
    location : Location
        The parent Location this storage location belongs to.

    Examples
    --------
    ```python
    from albert import Albert
    from albert.resources.storage_locations import StorageLocation
    client = Albert()
    parent = client.locations.get_by_id(id="...")
    storage_location = StorageLocation(name="Freezer A", location=parent)
    ```
    """

    name: str = Field(alias="name", min_length=2, max_length=255)
    id: str | None = Field(alias="albertId", default=None)
    location: SerializeAsEntityLink[Location] = Field(alias="Location")
