from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Location(BaseResource):
    """A physical lab or site location in Albert.

    Locations are referenced by Tasks and Inventory Items to record where an
    activity is performed or where a material lives, and each Location can hold
    one or more Storage Locations
    (:class:`~albert.resources.storage_locations.StorageLocation`). Managed
    through :class:`~albert.collections.locations.LocationCollection`.

    Attributes
    ----------
    name : str
        The human-readable name of the location.
    id : str | None
        The Albert ID of the location. Assigned by Albert and populated once the
        location has been created or retrieved.
    latitude : float
        The latitude of the location, in decimal degrees.
    longitude : float
        The longitude of the location, in decimal degrees.
    address : str
        The street address of the location.
    country : str | None
        The two-letter country code of the location (for example, ``"US"``).

    Examples
    --------
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
        ```
    """

    name: str
    id: str | None = Field(None, alias="albertId")
    latitude: float = Field()
    longitude: float = Field()
    address: str
    country: str | None = Field(None, max_length=2, min_length=2)
