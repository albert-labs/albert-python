import pytest

from albert.albert import Albert
from albert.exceptions import AlbertException
from albert.resources.companies import Company


def _list_asserts(returned_list):
    found = False
    for i, c in enumerate(returned_list):
        if i == 100:
            break
        found = True
        assert isinstance(c, Company)
        assert isinstance(c.name, str)
        assert isinstance(c.id, str)
        assert c.id.startswith("COM")
    assert found


def test_simple_company_list(client: Albert):
    simple_list = client.companies.list()
    _list_asserts(simple_list)


def test_advanced_company_list(client: Albert, seeded_companies: list[Company]):
    name = seeded_companies[1].name
    adv_list = client.companies.list(name=name, exact_match=True)
    adv_list = list(adv_list)
    for c in adv_list:
        assert name.lower() in c.name.lower()
    _list_asserts(adv_list)

    list_small_batch = client.companies.list(limit=2)
    _list_asserts(list_small_batch)


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

    company = client.companies.create(company=company)
    assert isinstance(company, Company)
    assert company.id is not None
    assert company.name == company_name

    new_company_name = f"{seed_prefix} new company name"
    renamed_company = client.companies.rename(old_name=company_name, new_name=new_company_name)
    assert isinstance(renamed_company, Company)
    assert renamed_company.name == new_company_name
    assert renamed_company.id == company.id

    client.companies.delete(id=company.id)
    assert not client.companies.company_exists(name=company_name)
    with pytest.raises(AlbertException):
        client.companies.rename(old_name=company_name, new_name="nope")
