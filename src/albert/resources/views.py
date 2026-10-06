from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import UserId, ViewId
from albert.core.shared.models.base import BaseResource


class ViewEntity(str, Enum):
    """The grid a saved view belongs to.

    Each grid in the Albert app (Projects, Tasks, Inventory, and so on) keeps its
    own list of views. A view saved for one entity is only shown on that grid.

    Attributes
    ----------
    PROJECTS : str
        The Projects grid.
    TASKS : str
        The Tasks grid.
    INVENTORIES : str
        The Inventory grid.
    PARAMETER_GROUPS : str
        The Parameter Groups grid (Master Data Management).
    DATA_TEMPLATES : str
        The Data Templates grid (Master Data Management).
    DATA_COLUMNS : str
        The Results (data columns) grid (Master Data Management).
    PARAMETERS : str
        The Parameters grid (Master Data Management).
    TEMPLATES : str
        The Templates grid (Master Data Management).
    REPORTS : str
        The Reports grid.
    TEAMS : str
        The Teams grid (Admin).
    USERS : str
        The Users grid (Admin).
    REFERENCE_ATTRIBUTES : str
        The Attributes grid (Master Data Management).
    UNITS : str
        The Units grid.
    UNIT_FAMILIES : str
        The Unit Families grid.
    """

    PROJECTS = "projects"
    TASKS = "tasks"
    INVENTORIES = "inventories"
    PARAMETER_GROUPS = "parametergroups"
    DATA_TEMPLATES = "datatemplates"
    DATA_COLUMNS = "datacolumns"
    PARAMETERS = "parameters"
    TEMPLATES = "template"
    REPORTS = "reports"
    TEAMS = "teams"
    USERS = "users"
    REFERENCE_ATTRIBUTES = "referenceattributes"
    UNITS = "units"
    UNIT_FAMILIES = "unit-families"


class ViewColumn(BaseAlbertModel):
    """A column shown on a view's grid.

    The column order in [`ViewState.columns`][albert.resources.views.ViewState.columns]
    is the order the grid displays them in.

    !!! example
        ```python
        from albert.resources.views import ViewColumn

        column = ViewColumn(id="albertId")
        hidden = ViewColumn(id="description", is_hidden=True)
        ```
    """

    id: str
    """The column key, as used by the grid (e.g. ``albertId``, ``status``, ``owner``, ``tags``)."""

    is_hidden: bool = Field(default=False, alias="isHidden")
    """Whether the column is hidden on the grid. Hidden columns keep their position."""

    width: int | None = Field(default=None)
    """The column width in pixels. When unset, the grid uses its default width."""


class ViewSort(BaseAlbertModel):
    """A sort applied to a view's grid.

    !!! example
        ```python
        from albert.core.shared.enums import OrderBy
        from albert.resources.views import ViewSort

        newest_first = ViewSort(id="createdAt", direction=OrderBy.DESCENDING)
        ```
    """

    id: str
    """The key of the column to sort by (e.g. ``createdAt``, ``status``)."""

    direction: OrderBy = Field(alias="dir")
    """The sort direction: ascending or descending."""


class ViewQuery(BaseAlbertModel):
    """The filters and search text applied to a view's grid.

    ``filter`` maps a grid filter key to the values to keep. Keys and values are the
    ones the grid's filter bar uses, and values are display names, not IDs. For
    example, the Data Templates grid's "Owner" filter is
    ``{"owner": ["Jane Doe"]}`` and the Projects grid's "Status" filter is
    ``{"status": ["Active", "Not Started"]}``. Albert does not check the keys or
    values when a view is saved. A key or value the grid does not recognize is kept
    as is and simply matches nothing, so the grid shows no results.

    !!! example
        ```python
        from albert.resources.views import ViewQuery

        mine = ViewQuery(filter={"owner": ["Jane Doe"]})
        searched = ViewQuery(filter={"status": ["Active"]}, search="coating")
        ```
    """

    filter: dict[str, Any] = Field(default_factory=dict)
    """Grid filter key mapped to the values to keep (usually a list of display names)."""

    search: str | None = Field(default=None)
    """Free-text search applied on top of the filters."""

    contains_field: list[str] | None = Field(default=None, alias="containsField")
    """Column keys for "contains text" filters. Paired by position with ``contains_text``."""

    contains_text: list[str] | None = Field(default=None, alias="containsText")
    """Text each column in ``contains_field`` must contain. Paired by position with ``contains_field``."""


class ViewState(BaseAlbertModel):
    """The saved layout of a view: its columns, filters, sorting, and grouping.

    !!! example
        ```python
        from albert.core.shared.enums import OrderBy
        from albert.resources.views import ViewColumn, ViewQuery, ViewSort, ViewState

        state = ViewState(
            columns=[ViewColumn(id="albertId"), ViewColumn(id="owner")],
            query=[ViewQuery(filter={"owner": ["Jane Doe"]})],
            sort_by=[ViewSort(id="createdAt", direction=OrderBy.DESCENDING)],
        )
        ```
    """

    columns: list[ViewColumn] | None = Field(default=None, min_length=1)
    """The columns shown on the grid, in display order. A saved view always has at least one column. When creating a view, leave this unset to copy the columns of the grid's default "All" view."""

    query: list[ViewQuery] = Field(default_factory=list)
    """The filters and search text applied to the grid. The grid uses the first entry."""

    sort_by: list[ViewSort] = Field(default_factory=list, alias="sortBy")
    """The sorts applied to the grid, in priority order."""

    group_by: str | None = Field(default=None, alias="groupBy")
    """The key of the column the grid rows are grouped by, if any."""


class View(BaseResource):
    """A saved grid view in Albert.

    A view is a named, saved layout for one of the grids in the Albert app (for
    example the Projects or Data Templates grid): which columns are shown, which
    filters and search text are applied, and how rows are sorted and grouped.
    Saved views appear as tabs above the grid (for example ``All | My Open Projects``).

    Views are personal. Each view belongs to the user who created it and is only
    visible to that user. Views are managed through the
    [`ViewCollection`][albert.collections.views.ViewCollection].

    !!! example
        ```python
        from albert.resources.views import View, ViewEntity, ViewQuery, ViewState

        view = View(
            name="My Data Templates",
            entity=ViewEntity.DATA_TEMPLATES,
            state=ViewState(query=[ViewQuery(filter={"owner": ["Jane Doe"]})]),
        )
        ```
    """

    id: ViewId | None = Field(default=None, alias="albertId")
    """The Albert ID of the view (format ``VEW...``). Assigned by Albert when the view is created."""

    name: str
    """The display name of the view, shown on its tab. Must be 2 to 50 characters."""

    entity: ViewEntity
    """The grid the view belongs to. Cannot be changed after the view is created."""

    state: ViewState | None = Field(default=None)
    """The saved columns, filters, sorting, and grouping of the view."""

    parent_id: UserId | None = Field(default=None, alias="parentId", frozen=True)
    """The ID of the user who owns the view. Assigned from the current user when the view is created."""

    uuid: str | None = Field(default=None, frozen=True)
    """A unique identifier Albert assigns to the view alongside its ID."""

    system: bool | None = Field(default=None, frozen=True)
    """Whether Albert created the view as one of the grid's built-in defaults (for example the "All" view)."""
