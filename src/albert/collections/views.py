from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import ViewId
from albert.exceptions import AlbertException, NotFoundError
from albert.resources.views import View, ViewColumn, ViewEntity, ViewState

# The list handler parses `limit` with no fallback, so the SDK always sends a page size.
_VIEW_PAGE_LIMIT = 200

_STATE_ALIASES = {
    "columns": "columns",
    "query": "query",
    "sort_by": "sortBy",
    "group_by": "groupBy",
}


class ViewCollection(BaseCollection):
    """Manage saved grid views in the Albert platform.

    A view is a named, saved layout for one of the grids in the Albert app (for
    example the Projects, Tasks, Inventory, or Data Templates grid): which columns
    are shown, which filters and search text are applied, and how rows are sorted
    and grouped. Saved views appear as tabs above the grid, in the order returned by
    [`get_order`][albert.collections.views.ViewCollection.get_order].

    Views are personal. Every method works on the views of the current user: views
    are created for the current user, and only the current user's views are listed.

    This collection is accessed as ``client.views``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.views import View, ViewEntity, ViewQuery, ViewState

        client = Albert()
        view = client.views.create(
            view=View(
                name="My Data Templates",
                entity=ViewEntity.DATA_TEMPLATES,
                state=ViewState(query=[ViewQuery(filter={"owner": ["Jane Doe"]})]),
            )
        )
        view.id
        # 'VEW123'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for view requests.

    Methods
    -------
    create(view) -> View
        Create a new view for the current user.
    get_by_id(id) -> View
        Get a single view by its ID.
    get_all(entity, ...) -> Iterator[View]
        Get the current user's views for a grid.
    update(view) -> View
        Update the name or saved layout of a view.
    delete(id) -> None
        Delete a view by its ID.
    get_order(entity) -> list[str]
        Get the tab order of the current user's views for a grid.
    set_order(entity, view_ids) -> None
        Set the tab order of the current user's views for a grid.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a ViewCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ViewCollection._api_version}/views"

    @validate_call
    def create(self, *, view: View) -> View:
        """Create a new view for the current user.

        The view is owned by the current user and added as the last tab on its grid.

        Filters in ``view.state.query`` use the grid's own filter keys and display
        names (for example ``{"owner": ["Jane Doe"]}``). They are saved as given and
        not checked, so a key or value the grid does not recognize makes the view
        show no results. See [`ViewQuery`][albert.resources.views.ViewQuery].

        When ``view.state`` or ``view.state.columns`` is not set, the view gets the
        columns of the grid's default "All" view, so it looks like the grid the user
        already knows. If the user has no views for the grid yet, the grid's built-in
        default views are created first, so they stay alongside the new view.

        !!! example
            ```python
            from albert.resources.views import View, ViewEntity, ViewQuery, ViewState

            view = client.views.create(
                view=View(
                    name="Active Projects",
                    entity=ViewEntity.PROJECTS,
                    state=ViewState(query=[ViewQuery(filter={"status": ["Active"]})]),
                )
            )
            view.id
            # 'VEW123'
            [column.id for column in view.state.columns]
            # ['albertId', 'status', 'marketSegment', 'application', 'technology']
            ```

        Parameters
        ----------
        view : View
            The view to create. Requires ``name`` (2 to 50 characters) and
            ``entity``. ``state`` is optional.

        Returns
        -------
        View
            The created View, populated with its assigned ID.

        Raises
        ------
        AlbertException
            If no columns are given and the grid has no default view to copy them from.
        """
        state = view.state or ViewState()
        default_columns = self._default_columns(entity=view.entity)
        if state.columns is None:
            if default_columns is None:
                raise AlbertException(
                    f"No default view found for '{view.entity.value}' to copy columns from. "
                    "Set `view.state.columns` explicitly."
                )
            state = state.model_copy(update={"columns": default_columns})
        payload = {
            "name": view.name,
            "entity": view.entity.value,
            "state": state.model_dump(by_alias=True, exclude_none=True, mode="json"),
        }
        response = self.session.post(self.base_path, json=payload)
        return View(**response.json())

    @validate_call
    def get_by_id(self, *, id: ViewId) -> View:
        """Get a view by its ID.

        Only views owned by the current user can be retrieved.

        !!! example
            ```python
            view = client.views.get_by_id(id="VEW123")
            view.name
            # 'Active Projects'
            ```

        Parameters
        ----------
        id : ViewId
            The ID of the view (format ``VEW...``).

        Returns
        -------
        View
            The fully populated View.

        Raises
        ------
        NotFoundError
            If no view with this ID exists, or it was deleted.
        ForbiddenError
            If the view belongs to another user.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return View(**response.json())

    @validate_call
    def get_all(self, *, entity: ViewEntity, max_items: int | None = None) -> Iterator[View]:
        """Get the current user's views for a grid.

        Views are returned in tab order. The first time a user's views are listed for
        a grid, Albert creates the grid's built-in default views for that user (for
        example "All"), the same as when the user first opens the grid in the app.
        These default views have ``system`` set to True.

        !!! example
            ```python
            from albert.resources.views import ViewEntity

            for view in client.views.get_all(entity=ViewEntity.PROJECTS):
                print(view.id, view.name)
            # VEW1 All
            # VEW2 My Open Projects
            ```

        Parameters
        ----------
        entity : ViewEntity
            The grid to list views for.
        max_items : int, optional
            Maximum number of views to return in total. If None, returns all views.

        Returns
        -------
        Iterator[View]
            An iterator of the current user's views for the grid.
        """
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params={"entity": entity.value, "limit": _VIEW_PAGE_LIMIT},
            max_items=max_items,
            deserialize=lambda items: [View(**item) for item in items],
        )

    @validate_call
    def update(self, *, view: View) -> View:
        """Update the name or saved layout of a view.

        Only the parts of ``view.state`` that were explicitly set are changed; every
        other part of the saved layout is kept. For example, passing
        ``ViewState(query=[...])`` replaces the filters and keeps the current columns,
        sorting, and grouping. Setting ``group_by=None`` explicitly removes grouping.

        !!! example
            ```python
            from albert.resources.views import ViewQuery

            view = client.views.get_by_id(id="VEW123")
            view.name = "Active and Planned Projects"
            view.state.query = [ViewQuery(filter={"status": ["Active", "Not Started"]})]
            updated = client.views.update(view=view)
            updated.name
            # 'Active and Planned Projects'
            ```

        Parameters
        ----------
        view : View
            The view with its changes. Requires ``id``. ``entity`` must match the
            existing view.

        Returns
        -------
        View
            The updated View.

        Raises
        ------
        ValueError
            If ``view.id`` is not set, or ``view.entity`` differs from the existing view.

        Notes
        -----
        The following can be updated: ``name`` and ``state`` (``columns``,
        ``query``, ``sort_by``, and ``group_by``). ``entity`` cannot be changed; to
        move a layout to another grid, create a new view there.
        """
        if view.id is None:
            raise ValueError("`view.id` is required to update a view.")
        existing = self.session.get(f"{self.base_path}/{view.id}").json()
        data = self._build_update_data(existing=existing, updated=view)
        if data:
            self.session.patch(f"{self.base_path}/{view.id}", json={"data": data})
        return self.get_by_id(id=view.id)

    @validate_call
    def delete(self, *, id: ViewId) -> None:
        """Delete a view by its ID.

        The view is also removed from the tab order of its grid.

        !!! example
            ```python
            client.views.delete(id="VEW123")
            ```

        Parameters
        ----------
        id : ViewId
            The ID of the view to delete (format ``VEW...``).

        Returns
        -------
        None

        Raises
        ------
        NotFoundError
            If no view with this ID exists, or it was already deleted.
        """
        self.session.delete(f"{self.base_path}/{id}")

    @validate_call
    def get_order(self, *, entity: ViewEntity) -> list[str]:
        """Get the tab order of the current user's views for a grid.

        !!! example
            ```python
            from albert.resources.views import ViewEntity

            client.views.get_order(entity=ViewEntity.PROJECTS)
            # ['VEW1', 'VEW2', 'VEW123']
            ```

        Parameters
        ----------
        entity : ViewEntity
            The grid to get the tab order for.

        Returns
        -------
        list[str]
            The view IDs in tab order, left to right. Empty when the user has no
            views for the grid yet.
        """
        try:
            response = self.session.get(
                f"{self.base_path}/sequence", params={"entity": entity.value}
            )
        except NotFoundError:
            return []
        return list(response.json().get("sequence") or [])

    @validate_call
    def set_order(self, *, entity: ViewEntity, view_ids: list[ViewId]) -> None:
        """Set the tab order of the current user's views for a grid.

        ``view_ids`` must list every one of the user's views for the grid exactly
        once, in the new order. Use
        [`get_order`][albert.collections.views.ViewCollection.get_order] to get the
        current IDs.

        !!! example
            ```python
            from albert.resources.views import ViewEntity

            order = client.views.get_order(entity=ViewEntity.PROJECTS)
            # ['VEW1', 'VEW2', 'VEW123']
            client.views.set_order(
                entity=ViewEntity.PROJECTS, view_ids=["VEW123", "VEW1", "VEW2"]
            )
            ```

        Parameters
        ----------
        entity : ViewEntity
            The grid to reorder views for.
        view_ids : list[ViewId]
            The IDs of all the user's views for the grid, in the new tab order.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If ``view_ids`` adds, drops, or repeats a view compared to the current order.
        AlbertException
            If the user has no views for the grid yet.
        """
        current = self.get_order(entity=entity)
        if not current:
            raise AlbertException(
                f"No views exist yet for '{entity.value}'. Create a view before ordering."
            )
        self._validate_order(current=current, new=view_ids)
        if view_ids == current:
            return
        self.session.patch(
            f"{self.base_path}/sequence",
            params={"entity": entity.value},
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "sequence",
                        "oldValue": current,
                        "newValue": view_ids,
                    }
                ]
            },
        )

    def _default_columns(self, *, entity: ViewEntity) -> list[ViewColumn] | None:
        """Return the columns of the grid's built-in default view, if the user has one.

        Listing the user's views also makes sure the grid's built-in default views exist
        before a custom view is added; once a user has any view for a grid, the defaults
        are no longer created for them.
        """
        for existing in self.get_all(entity=entity):
            if existing.system and existing.state and existing.state.columns:
                return existing.state.columns
        return None

    @staticmethod
    def _build_update_data(*, existing: dict[str, Any], updated: View) -> list[dict[str, Any]]:
        """Build the change list that turns the stored view into ``updated``.

        ``existing`` is the stored view in wire format. ``oldValue`` carries the
        stored value unchanged so the server's optimistic concurrency check compares
        like with like. Only state fields the caller explicitly set replace the
        stored ones.
        """
        if updated.entity.value != existing.get("entity"):
            raise ValueError(
                f"A view's entity cannot be changed (existing: '{existing.get('entity')}', "
                f"given: '{updated.entity.value}')."
            )
        data: list[dict[str, Any]] = []
        old_name = existing.get("name")
        if "name" in updated.model_fields_set and updated.name != old_name:
            data.append(
                {
                    "operation": "update",
                    "attribute": "name",
                    "oldValue": old_name,
                    "newValue": updated.name,
                }
            )
        state = updated.state
        if "state" in updated.model_fields_set and state is not None:
            old_state = existing.get("state") or {}
            new_state = dict(old_state)
            for field in state.model_fields_set:
                value = getattr(state, field)
                alias = _STATE_ALIASES[field]
                if value is None:
                    if field == "group_by":
                        new_state[alias] = None
                    continue
                new_state[alias] = state.model_dump(
                    by_alias=True, exclude_none=True, mode="json", include={field}
                )[alias]
            if ViewCollection._normalize_state(new_state) != ViewCollection._normalize_state(
                old_state
            ):
                data.append(
                    {
                        "operation": "update",
                        "attribute": "state",
                        "oldValue": old_state,
                        "newValue": new_state,
                    }
                )
        return data

    @staticmethod
    def _normalize_state(state: dict[str, Any]) -> dict[str, Any]:
        """Return ``state`` in a canonical form so equivalent layouts compare equal."""
        return ViewState.model_validate(state).model_dump(by_alias=True, mode="json")

    @staticmethod
    def _validate_order(*, current: list[str], new: list[str]) -> None:
        """Ensure ``new`` is a reordering of ``current`` with no views added or dropped."""
        if len(new) != len(set(new)):
            raise ValueError("`view_ids` must not repeat a view.")
        missing = [view_id for view_id in current if view_id not in new]
        unknown = [view_id for view_id in new if view_id not in current]
        if missing or unknown:
            parts = []
            if missing:
                parts.append(f"missing {missing}")
            if unknown:
                parts.append(f"not in the current order {unknown}")
            raise ValueError(
                "`view_ids` must list every current view exactly once: " + "; ".join(parts)
            )
