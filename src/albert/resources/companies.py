from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Company(BaseResource):
    """A manufacturing company or supplier tracked in Albert.

    A Company is the organization that makes or supplies a material. It is the
    ``company`` linked on raw-material inventory items: each raw material points
    back to the Company that manufactures it (see
    [`InventoryItem`][albert.resources.inventory.InventoryItem]). Companies are managed
    through [`CompanyCollection`][albert.collections.companies.CompanyCollection], accessed as
    ``client.companies``.

    Companies are identified by a Company ID (format ``COM...``). A Company is
    typically minimal: a name plus its assigned ID. You construct one directly
    (``Company(name="Acme Chemicals")``) to create it or to attach it to an
    inventory item.

    !!! example
        ```python
        from albert.resources.companies import Company

        # Build a company to create or attach to an inventory item
        company = Company(name="Acme Chemicals")
        ```"""

    name: str
    """The company's name. This is the primary identifier used when searching for or creating a company."""

    id: str | None = Field(default=None, alias="albertId")
    """The Albert Company ID (format ``COM...``). ``None`` until the company is created in or retrieved from Albert."""

    # Read-only fields
    distance: float | None = Field(default=None, exclude=True, frozen=True)
    """Search-relevance score returned when the company comes back as a search result. Read-only; not set on companies you build yourself."""
