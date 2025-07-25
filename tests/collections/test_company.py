import pytest

from albert.client import Albert
from albert.exceptions import AlbertException
from albert.resources.companies import Company


def assert_valid_company_items(items: list[Company]):
    """Assert basic structure and types of Company items."""
    assert items, "Expected at least one Company result"
    for c in items[:10]:
        assert isinstance(c, Company)
        assert isinstance(c.name, str)
        assert isinstance(c.id, str)
        assert c.id.startswith("COM")


def test_company_get_all_with_pagination(client: Albert):
    """Test that Company get_all() respects pagination and max_items."""
    results = list(client.companies.get_all(max_items=10))
    assert len(results) <= 10
    assert_valid_company_items(results)


def test_company_get_all_with_filters(client: Albert, seeded_companies: list[Company]):
    """Test Company get_all() with name filter and exact match."""
    name = seeded_companies[1].name

    filtered = list(
        client.companies.get_all(
            name=name,
            exact_match=True,
            max_items=10,
        )
    )
    assert any(name.lower() in c.name.lower() for c in filtered)
    assert_valid_company_items(filtered)


def test_company_get_by(client: Albert, seeded_companies: list[Company]):
    test_name = seeded_companies[0].name
    company = client.companies.get_by_name(name=test_name)
    assert isinstance(company, Company)
    assert company.name == test_name

    company_by_id = client.companies.get_by_id(id=company.id)
    assert isinstance(company_by_id, Company)
    assert company_by_id.name == test_name


def test_company_crud(client: Albert, seed_prefix: str):
    company_name = f"{seed_prefix} company name"
    company = Company(name=company_name)

    company = client.companies.get_or_create(company=company)
    assert isinstance(company, Company)
    assert company.id is not None
    assert company.name == company_name

    new_company_name = f"{seed_prefix} new company name"
    renamed_company = client.companies.rename(old_name=company_name, new_name=new_company_name)
    assert isinstance(renamed_company, Company)
    assert renamed_company.name == new_company_name
    assert renamed_company.id == company.id

    client.companies.delete(id=company.id)
    assert not client.companies.exists(name=company_name)
    with pytest.raises(AlbertException):
        client.companies.rename(old_name=company_name, new_name="nope")
