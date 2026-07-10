from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Company(BaseResource):
    """A manufacturing company or supplier tracked in Albert.

    A Company is the organization that makes or supplies a material. It is the
    ``company`` linked on raw-material inventory items: each raw material points
    back to the Company that manufactures it (see
    :class:`~albert.resources.inventory.InventoryItem`). Companies are managed
    through :class:`~albert.collections.companies.CompanyCollection`, accessed as
    ``client.companies``.

    Companies are identified by a Company ID (format ``COM...``). A Company is
    typically minimal: a name plus its assigned ID. You construct one directly
    (``Company(name="Acme Chemicals")``) to create it or to attach it to an
    inventory item.

    Attributes
    ----------
    name : str
        The company's name. This is the primary identifier used when searching
        for or creating a company.
    id : str | None
        The Albert Company ID (format ``COM...``). ``None`` until the company is
        created in or retrieved from Albert.
    distance : float | None
        Search-relevance score returned when the company comes back as a search
        result. Read-only; not set on companies you build yourself.
    status : Status | None
        Lifecycle status of the company (inherited from
        :class:`~albert.core.shared.models.base.BaseResource`).

    Examples
    --------
    !!! example
        ```python
        from albert.resources.companies import Company

        # Build a company to create or attach to an inventory item
        company = Company(name="Acme Chemicals")
        ```
    """

    name: str
    id: str | None = Field(default=None, alias="albertId")

    # Read-only fields
    distance: float | None = Field(default=None, exclude=True, frozen=True)
