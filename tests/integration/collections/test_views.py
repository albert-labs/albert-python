import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import NotFoundError
from albert.resources.views import View, ViewEntity, ViewQuery, ViewState

# Both tests change the same user's tab order for one grid, so they share a worker.
pytestmark = pytest.mark.xdist_group("views")


def _name() -> str:
    return f"TEST {uuid.uuid4().hex[:8]}"


def test_view_crud(client: Albert):
    """Test creating, reading, listing, updating, and deleting a view."""
    created = client.views.create(
        view=View(
            name=_name(),
            entity=ViewEntity.DATA_TEMPLATES,
            state=ViewState(query=[ViewQuery(filter={"owner": ["SDK Test"]})]),
        )
    )
    try:
        assert created.id and created.id.startswith("VEW")
        assert created.entity is ViewEntity.DATA_TEMPLATES
        assert created.state.columns, "columns are copied from the default view"
        assert created.state.query[0].filter == {"owner": ["SDK Test"]}

        fetched = client.views.get_by_id(id=created.id)
        assert fetched.name == created.name
        assert fetched.state.columns == created.state.columns

        listed = list(client.views.get_all(entity=ViewEntity.DATA_TEMPLATES))
        assert created.id in {v.id for v in listed}
        assert any(v.system for v in listed)
        assert created.id in client.views.get_order(entity=ViewEntity.DATA_TEMPLATES)

        new_name = _name()
        updated = client.views.update(
            view=View(
                id=created.id,
                name=new_name,
                entity=ViewEntity.DATA_TEMPLATES,
                state=ViewState(query=[ViewQuery(filter={}, search="coating")]),
            )
        )
        assert updated.name == new_name
        assert updated.state.query[0].search == "coating"
        assert updated.state.columns == created.state.columns
        assert updated.state.sort_by == created.state.sort_by
    finally:
        with suppress(NotFoundError):
            client.views.delete(id=created.id)

    with pytest.raises(NotFoundError):
        client.views.get_by_id(id=created.id)
    assert created.id not in client.views.get_order(entity=ViewEntity.DATA_TEMPLATES)


def test_view_set_order(client: Albert):
    """Test moving a view to the first tab and restoring the original order."""
    view = client.views.create(view=View(name=_name(), entity=ViewEntity.DATA_TEMPLATES))
    try:
        original = client.views.get_order(entity=ViewEntity.DATA_TEMPLATES)
        reordered = [view.id] + [v for v in original if v != view.id]

        client.views.set_order(entity=ViewEntity.DATA_TEMPLATES, view_ids=reordered)
        assert client.views.get_order(entity=ViewEntity.DATA_TEMPLATES) == reordered

        with pytest.raises(ValueError, match="missing"):
            client.views.set_order(entity=ViewEntity.DATA_TEMPLATES, view_ids=reordered[:1])
    finally:
        with suppress(NotFoundError):
            client.views.delete(id=view.id)


def test_view_builders(client: Albert):
    """Test building a view's filters and columns with the helper methods."""
    filters = client.views.list_filters(entity=ViewEntity.DATA_TEMPLATES)
    by_key = {f.key: f for f in filters}
    assert by_key["owner"].multi is True

    values = client.views.suggest_filter_values(entity=ViewEntity.DATA_TEMPLATES, filter="owner")
    assert all(value.name for value in values)

    query = client.views.build_query(
        entity=ViewEntity.DATA_TEMPLATES,
        owner=["SDK Test"],
        search="coating",
        contains={"description": "polymer"},
    )
    assert query.filter == {"owner": ["SDK Test"]}

    columns = client.views.build_columns(entity=ViewEntity.DATA_TEMPLATES, hide=["tags"])
    assert columns, "columns are built from the grid's default view"
    assert next(c for c in columns if c.id == "tags").is_hidden is True

    view = client.views.create(
        view=View(
            name=_name(),
            entity=ViewEntity.DATA_TEMPLATES,
            state=ViewState(query=[query], columns=columns),
        )
    )
    try:
        assert view.state.query[0].filter == {"owner": ["SDK Test"]}
        assert next(c for c in view.state.columns if c.id == "tags").is_hidden is True
    finally:
        with suppress(NotFoundError):
            client.views.delete(id=view.id)
