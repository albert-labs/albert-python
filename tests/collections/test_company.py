from collections.abc import Generator

import pytest

from albert.albert import Albert
from albert.resources.companies import Company
from albert.utils.exceptions import AlbertException


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
    assert isinstance(simple_list, Generator)
    _list_asserts(simple_list)


def test_advanced_company_list(client: Albert, seeded_companies: list[Company]):
    name = seeded_companies[1].name
    adv_list = client.companies.list(name=name, exact_match=True)
    assert isinstance(adv_list, Generator)
    adv_list = list(adv_list)
    for c in adv_list:
        assert name.lower() in c.name.lower()
    _list_asserts(adv_list)

    list_small_batch = client.companies._list_generator(limit=2)
    _list_asserts(list_small_batch)


def test_company_get_by(client: Albert, seeded_companies: list[Company]):
    test_name = seeded_companies[0].name
    company = client.companies.get_by_name(name=test_name)
    assert isinstance(company, Company)
    assert company.name == test_name

    company_by_id = client.companies.get_by_id(id=company.id)
    assert isinstance(company_by_id, Company)
    assert company_by_id.name == test_name


def test_basic_create_delete(client: Albert):
    simple_company = client.companies.create(company="Simple test company name!")
    assert isinstance(simple_company, Company)
    assert simple_company.id is not None

    client.companies.delete(id=simple_company.id)
    assert not client.companies.company_exists(name=simple_company.name)


def test_company_crud(client: Albert):
    new_company = Company(name="SDK Testing Corp.")

    # Clean Up incase of previous failed tests
    c1 = client.companies.get_by_name(name="SDK Testing Corp. UPDATED")
    if c1:
        client.companies.delete(id=c1.id)
    c2 = client.companies.get_by_name(name="A second cool name")
    if c2:
        client.companies.delete(id=c2.id)

    registered_company = client.companies.create(company=new_company)
    assert isinstance(registered_company, Company)
    assert registered_company.id is not None
    assert registered_company.name == "SDK Testing Corp."

    renamed_company = client.companies.rename(
        old_name="SDK Testing Corp.", new_name="SDK Testing Corp. UPDATED"
    )

    assert isinstance(renamed_company, Company)
    assert renamed_company.name == "SDK Testing Corp. UPDATED"
    assert renamed_company.id == registered_company.id

    renamed_company.name = "A second cool name"
    renamed_company = client.companies.update(updated_object=renamed_company)

    client.companies.delete(id=renamed_company.id)
    assert not client.companies.company_exists(name="SDK Testing Corp. UPDATED")
    with pytest.raises(AlbertException):
        client.companies.rename(old_name="SDK Testing Corp. UPDATED", new_name="nope")
