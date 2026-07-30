from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import CompanyId
from albert.core.utils import ensure_list
from albert.exceptions import AlbertException
from albert.resources.companies import Company


class CompanyCollection(BaseCollection):
    """Manage Companies in the Albert platform.

    A Company is a manufacturing company or supplier: the organization that makes
    or supplies a material. Companies are the ``company`` linked on raw-material
    inventory items (see [`InventoryItem`][albert.resources.inventory.InventoryItem]), so
    they are usually created as a side effect of registering raw materials, but
    they can also be managed directly here.

    Companies are identified by a Company ID (format ``COM...``) and are looked up
    primarily by name. Because a Company is essentially a name, this collection
    offers find-or-create and rename helpers in addition to the usual CRUD.

    This collection is accessed as ``client.companies``.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        company = client.companies.get_or_create(company="Acme Chemicals")
        print(company.id, company.name)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for company requests.

    Methods
    -------
    get_all(name=None, exact_match=True, max_items=None) -> Iterator[Company]
        Iterate over companies, optionally filtered by name.
    get_by_id(id) -> Company
        Get a single company by its ID.
    get_by_name(name, exact_match=True) -> Company | None
        Get a single company by name, or None if not found.
    exists(name, exact_match=True) -> bool
        Check whether a company with the given name exists.
    create(company) -> Company
        Create a new company from a name or Company object.
    get_or_create(company) -> Company
        Return the existing company with this name, or create it.
    rename(old_name, new_name) -> Company
        Rename an existing company.
    update(company) -> Company
        Update an existing company (identified by its ID).
    merge(parent_id, child_ids) -> Company
        Merge one or more duplicate companies into a parent company.
    delete(id) -> None
        Delete a company by its ID.
    """

    _updatable_attributes = {"name"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a CompanyCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CompanyCollection._api_version}/companies"

    def get_all(
        self,
        *,
        name: str | list[str] = None,
        exact_match: bool = True,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Company]:
        """Iterate over companies, optionally filtered by name.

        Use this to list companies or to find companies whose name matches a
        search term. To fetch a single company, prefer [`get_by_id`][albert.collections.companies.CompanyCollection.get_by_id] (by ID)
        or [`get_by_name`][albert.collections.companies.CompanyCollection.get_by_name] (by name).

        !!! example
            ```python
            # All companies whose name contains "chem"
            for company in client.companies.get_all(name="chem", exact_match=False):
                print(company.id, company.name)
            ```

        Parameters
        ----------
        name : str or list[str], optional
            One or more company names to filter by. When omitted, all companies
            are returned.
        exact_match : bool, optional
            When True (default), only companies whose name matches ``name``
            exactly are returned. When False, ``name`` is treated as a substring
            search.
        start_key : str, optional
            Pagination cursor to resume from a previous page. Usually left unset.
        max_items : int, optional
            Maximum number of companies to return in total. If None, iterates
            over all matching companies.

        Returns
        -------
        Iterator[Company]
            An iterator over the matching [`Company`][albert.resources.companies.Company]
            objects.
        """
        params = {
            "dupDetection": "false",
            "startKey": start_key,
        }
        params["name"] = ensure_list(name)
        params["exactMatch"] = str(exact_match).lower()

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Company(**item) for item in items],
        )

    def exists(self, *, name: str, exact_match: bool = True) -> bool:
        """Check whether a company with the given name exists.

        Useful before creating a company to avoid duplicates. To get the matching
        company itself, use [`get_by_name`][albert.collections.companies.CompanyCollection.get_by_name]; to look up or create in one step,
        use [`get_or_create`][albert.collections.companies.CompanyCollection.get_or_create].

        !!! example
            ```python
            client.companies.exists(name="Acme Chemicals")
            # True
            ```

        Parameters
        ----------
        name : str
            The company name to check for.
        exact_match : bool, optional
            When True (default), requires an exact name match. When False, matches
            on a substring of the name.

        Returns
        -------
        bool
            True if a matching company exists, False otherwise.
        """
        companies = self.get_by_name(name=name, exact_match=exact_match)
        return bool(companies)

    @validate_call
    def get_by_id(self, *, id: CompanyId) -> Company:
        """Get a single company by its ID.

        To look up a company when you only know its name, use [`get_by_name`][albert.collections.companies.CompanyCollection.get_by_name].

        !!! example
            ```python
            company = client.companies.get_by_id(id="COM123")
            print(company.name)
            ```

        Parameters
        ----------
        id : CompanyId
            The Company ID (format ``COM...``).

        Returns
        -------
        Company
            The fully populated [`Company`][albert.resources.companies.Company].
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        company = response.json()
        found_company = Company(**company)
        return found_company

    def get_by_name(self, *, name: str, exact_match: bool = True) -> Company | None:
        """Get a single company by name.

        Returns the first match, or None if no company matches. To check only for
        existence, use [`exists`][albert.collections.companies.CompanyCollection.exists]; to look up or create in one step, use
        [`get_or_create`][albert.collections.companies.CompanyCollection.get_or_create].

        !!! example
            ```python
            company = client.companies.get_by_name(name="Acme Chemicals")
            company.id if company else "not found"
            # 'COM123'
            ```

        Parameters
        ----------
        name : str
            The company name to look up.
        exact_match : bool, optional
            When True (default), requires an exact name match. When False, matches
            on a substring of the name.

        Returns
        -------
        Company or None
            The matching [`Company`][albert.resources.companies.Company], or None if
            no company matches.
        """
        found = self.get_all(name=name, exact_match=exact_match, max_items=1)
        return next(found, None)

    def create(self, *, company: str | Company) -> Company:
        """Create a new company.

        To avoid creating a duplicate when a company with the same name may
        already exist, use [`get_or_create`][albert.collections.companies.CompanyCollection.get_or_create] instead.

        !!! example
            ```python
            company = client.companies.create(company="Acme Chemicals")
            company.id
            # 'COM123'
            ```

        Parameters
        ----------
        company : str or Company
            The company to create. Pass a plain name string, or a
            [`Company`][albert.resources.companies.Company] object.

        Returns
        -------
        Company
            The newly created company, populated with its assigned Company ID.
        """
        if isinstance(company, str):
            company = Company(name=company)

        payload = company.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        this_company = Company(**response.json())
        return this_company

    def get_or_create(self, *, company: str | Company) -> Company:
        """Return the existing company with this name, or create it if none exists.

        A find-or-create helper: matches on exact name via [`get_by_name`][albert.collections.companies.CompanyCollection.get_by_name],
        and falls back to [`create`][albert.collections.companies.CompanyCollection.create] when there is no match. This is the safe
        way to reference a company without risking a duplicate.

        !!! example
            ```python
            company = client.companies.get_or_create(company="Acme Chemicals")
            print(company.id, company.name)
            ```

        Parameters
        ----------
        company : str or Company
            The company to look up or create. Pass a plain name string, or a
            [`Company`][albert.resources.companies.Company] object.

        Returns
        -------
        Company
            The existing company if one matches by name, otherwise the newly
            created company.
        """
        if isinstance(company, str):
            company = Company(name=company)
        found = self.get_by_name(name=company.name, exact_match=True)
        if found:
            return found
        else:
            return self.create(company=company)

    @validate_call
    def merge(
        self,
        *,
        parent_id: CompanyId,
        child_ids: CompanyId | list[CompanyId],
    ) -> Company:
        """Merge one or more duplicate companies into a parent company.

        Use this to consolidate duplicate companies: the child company records are
        folded into the parent, which is kept. Inventory items and other entities
        referencing a child are repointed to the parent.

        !!! example
            ```python
            company = client.companies.merge(
                parent_id="COM123",
                child_ids=["COM456", "COM789"],
            )
            ```

        Parameters
        ----------
        parent_id : CompanyId
            The Company ID (format ``COM...``) of the company to keep.
        child_ids : CompanyId or list[CompanyId]
            One or more Company IDs of the duplicate companies to merge into the
            parent.

        Returns
        -------
        Company
            The parent company, re-fetched after the merge.
        """

        child_ids = [child_ids] if isinstance(child_ids, str) else list(child_ids)

        url = f"{self.base_path}/merge"
        payload = {
            "parentId": parent_id,
            "ChildCompanies": [{"id": cid} for cid in child_ids],
        }
        response = self.session.post(url, json=payload)
        if response.status_code == 206:
            details = response.json()
            logger.warning("Company merge partially succeeded", extra={"details": details})
        return self.get_by_id(id=parent_id)

    @validate_call
    def delete(self, *, id: CompanyId) -> None:
        """Delete a company by its ID.

        !!! example
            ```python
            client.companies.delete(id="COM123")
            ```

        Parameters
        ----------
        id : CompanyId
            The Company ID (format ``COM...``) of the company to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def rename(self, *, old_name: str, new_name: str) -> Company:
        """Rename an existing company, looking it up by its current name.

        A convenience wrapper that finds the company by name and updates its name.
        If you already hold a [`Company`][albert.resources.companies.Company] object,
        you can instead set ``name`` and call [`update`][albert.collections.companies.CompanyCollection.update].

        !!! example
            ```python
            company = client.companies.rename(
                old_name="Acme Chemicals",
                new_name="Acme Specialty Chemicals",
            )
            ```

        Parameters
        ----------
        old_name : str
            The company's current name. Must match an existing company exactly.
        new_name : str
            The new name to assign.

        Returns
        -------
        Company
            The renamed company, re-fetched after the update.

        Raises
        ------
        AlbertException
            If no company with ``old_name`` is found.
        """
        company = self.get_by_name(name=old_name, exact_match=True)
        if not company:
            msg = f'Company "{old_name}" not found.'
            logger.error(msg)
            raise AlbertException(msg)
        company_id = company.id
        endpoint = f"{self.base_path}/{company_id}"
        payload = {
            "data": [
                {
                    "operation": "update",
                    "attribute": "name",
                    "oldValue": old_name,
                    "newValue": new_name,
                }
            ]
        }
        self.session.patch(endpoint, json=payload)
        updated_company = self.get_by_id(id=company_id)
        return updated_company

    def update(self, *, company: Company) -> Company:
        """Update an existing company.

        The company is identified by its ``id``, which must be set. Only the
        updatable fields listed in Notes are applied. To rename a company by its
        current name rather than by its ID, use [`rename`][albert.collections.companies.CompanyCollection.rename].

        !!! example
            ```python
            company = client.companies.get_by_id(id="COM123")
            company.name = "Acme Specialty Chemicals"
            updated = client.companies.update(company=company)
            ```

        Parameters
        ----------
        company : Company
            The company to update, carrying the desired field values. Its ``id``
            must be set.

        Returns
        -------
        Company
            The updated company.

        Notes
        -----
        The following fields can be updated: ``name``.
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=company.id)

        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(existing=current_object, updated=company)
        url = f"{self.base_path}/{company.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))
        updated_company = self.get_by_id(id=company.id)
        return updated_company
