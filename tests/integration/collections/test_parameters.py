import uuid

import pytest

from albert.client import Albert
from albert.core.shared.enums import PaginationMode
from albert.resources.parameters import Parameter, ParameterSearchItem
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("datatemplates")


def assert_valid_parameter_items(returned_list: list[Parameter]):
    """Assert that returned items are valid Parameter objects."""
    assert returned_list, "Expected at least one Parameter"
    for u in returned_list[:10]:
        assert isinstance(u, Parameter)


def test_parameter_get_all_basic(client: Albert, seeded_parameters: list[Parameter]):
    """Test basic retrieval of parameters."""
    response = list(client.parameters.get_all(max_items=10))
    assert_valid_parameter_items(response)


def test_parameter_get_all_with_name(client: Albert, seeded_parameters: list[Parameter]):
    """Test get_all with name filtering."""
    response = list(
        client.parameters.get_all(names=seeded_parameters[0].name, exact_match=True, max_items=10)
    )
    assert_valid_parameter_items(response)


def test_parameter_get_all_by_ids(client: Albert, seeded_parameters: list[Parameter]):
    """Test get_all with a list of parameter IDs."""
    ids = [x.id for x in seeded_parameters]
    results = poll_until(
        lambda: [p for p in client.parameters.get_all(ids=ids, max_items=10) if p.id in set(ids)],
        predicate=lambda results: {p.id for p in results} == set(ids),
        timeout=15.0,
        interval=1.0,
    )
    assert len(results) == len(ids)
    assert {x.id for x in results} == set(ids)


def test_parameter_search_uses_cursor_pagination(
    client: Albert, seeded_parameters: list[Parameter], monkeypatch: pytest.MonkeyPatch
):
    """Test search returns every scoped match exactly once across cursor pages."""
    monkeypatch.setattr("albert.core.pagination.DEFAULT_LIMIT", 1)
    parameter_ids = {parameter.id for parameter in seeded_parameters}

    def search_all_matches():
        results = client.parameters.search(ids=list(parameter_ids))
        matches = list(results)
        assert results.mode is PaginationMode.SEARCH_AFTER
        assert results.json["limit"] == 1
        assert not results.has_more
        return matches

    matches = poll_until(
        search_all_matches,
        predicate=lambda items: {item.id for item in items} == parameter_ids,
    )
    assert len(matches) == len(parameter_ids)
    assert {item.id for item in matches} == parameter_ids

    early_results = client.parameters.search(ids=list(parameter_ids), max_items=1)
    assert len(list(early_results)) == 1
    assert early_results.has_more


def test_parameter_search(client: Albert, seed_prefix: str, seeded_parameters: list[Parameter]):
    """Test search finds seeded parameters and hydrates full Parameter resources."""
    seeded_ids = {parameter.id for parameter in seeded_parameters}
    hits = poll_until(
        lambda: [
            item
            for item in client.parameters.search(text=seed_prefix, max_items=50)
            if item.id in seeded_ids
        ]
    )

    assert hits, "Expected seeded parameters in search results"
    hit = hits[0]
    assert isinstance(hit, ParameterSearchItem)
    assert hit.id in seeded_ids

    hydrated = hit.hydrate()
    assert isinstance(hydrated, Parameter)
    assert hydrated.id == hit.id


def test_get(client: Albert, seeded_parameters: list[Parameter]):
    p = client.parameters.get_by_id(id=seeded_parameters[0].id)
    assert p.id == seeded_parameters[0].id
    assert p.name == seeded_parameters[0].name


def test_get_by_ids(client: Albert, seeded_parameters: list[Parameter]):
    """Test get_by_ids returns the parameters matching the provided IDs."""
    ids = [x.id for x in seeded_parameters]
    results = poll_until(
        lambda: [p for p in client.parameters.get_by_ids(ids=ids) if p.id in set(ids)],
        predicate=lambda results: len(results) == len(ids),
        timeout=15.0,
        interval=1.0,
    )
    assert len(results) == len(ids)
    assert {x.id for x in results} == set(ids)


def test_get_by_ids_empty(client: Albert):
    """Test get_by_ids with empty IDs list returns empty list immediately."""
    assert client.parameters.get_by_ids(ids=[]) == []


def test_get_by_ids_omits_unknown_ids(client: Albert, seeded_parameters: list[Parameter]):
    """Test that known parameter IDs are returned and unknown ones are omitted."""
    known_ids = [x.id for x in seeded_parameters[:2]]
    results = poll_until(
        lambda: [
            p
            for p in client.parameters.get_by_ids(ids=[*known_ids, "PRM0"])
            if p.id in set(known_ids)
        ],
        predicate=lambda results: len(results) == len(known_ids),
        timeout=15.0,
        interval=1.0,
    )
    assert len(results) == len(known_ids)
    assert {p.id for p in results} == set(known_ids)


def test_get_or_create_parameters(caplog, client: Albert, seeded_parameters: list[Parameter]):
    p = seeded_parameters[0].model_copy(update={"id": None})
    returned = client.parameters.get_or_create(parameter=p)
    assert (
        f"Parameter with name {p.name} already exists. Returning existing parameter."
        in caplog.text
    )
    assert returned.id == seeded_parameters[0].id
    assert returned.name == seeded_parameters[0].name


def test_update(client: Albert, seeded_parameters: list[Parameter]):
    p = seeded_parameters[0].model_copy(deep=True)
    updated_name = f"TEST - {uuid.uuid4()}"
    p.name = updated_name
    updated = client.parameters.update(parameter=p)
    assert updated.name == updated_name
