from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Location(BaseResource):
    """A physical lab or site location in Albert.

    Locations are referenced by Tasks and Inventory Items to record where an
    activity is performed or where a material lives, and each Location can hold
    one or more Storage Locations
    ([`StorageLocation`][albert.resources.storage_locations.StorageLocation]). Managed
    through [`LocationCollection`][albert.collections.locations.LocationCollection].

    !!! example
        ```python
        from albert.resources.locations import Location
        location = Location(
            name="Boston Lab",
            latitude=42.3601,
            longitude=-71.0589,
            address="1 Main St",
            country="US",
        )
        ```"""

    name: str
    """The human-readable name of the location."""
    id: str | None = Field(None, alias="albertId")
    """The Albert ID of the location. Assigned by Albert and populated once the location has been created or retrieved."""
    latitude: float = Field()
    """The latitude of the location, in decimal degrees."""
    longitude: float = Field()
    """The longitude of the location, in decimal degrees."""
    address: str
    """The street address of the location."""
    country: str | None = Field(None, max_length=2, min_length=2)
    """The two-letter country code of the location (for example, ``"US"``)."""
