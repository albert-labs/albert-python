from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import CompanyId
from albert.exceptions import AlbertException
from albert.resources.companies import Company


class CompanyCollection(BaseCollection):
    """
    CompanyCollection is a collection class for managing Company entities in the Albert platform.
    """

    _updatable_attributes = {"name"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CompanyCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
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
        """
        Get all company entities with optional filters.

        Parameters
        ----------
        name : str | list[str], optional
            The name(s) of the company to filter by.
        exact_match : bool, optional
            Whether to match the name(s) exactly. Default is True.
        start_key : str, optional
            Key to start paginated results from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Company]
            An iterator of Company entities.
        """
        params = {
            "dupDetection": "false",
            "startKey": start_key,
        }
        if name:
            params["name"] = name if isinstance(name, list) else [name]
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
        """
        Checks if a company exists by its name.

        Parameters
        ----------
        name : str
            The name of the company to check.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        bool
            True if the company exists, False otherwise.
        """
        companies = self.get_by_name(name=name, exact_match=exact_match)
        return bool(companies)

    @validate_call
    def get_by_id(self, *, id: CompanyId) -> Company:
        """
        Get a company by its ID.

        Parameters
        ----------
        id : str
            The ID of the company to retrieve.

        Returns
        -------
        Company
            The Company object.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        company = response.json()
        found_company = Company(**company)
        return found_company

    def get_by_name(self, *, name: str, exact_match: bool = True) -> Company | None:
        """
        Retrieves a company by its name.

        Parameters
        ----------
        name : str
            The name of the company to retrieve.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        Company
            The Company object if found, None otherwise.
        """
        found = self.get_all(name=name, exact_match=exact_match, max_items=1)
        return next(found, None)

    def create(self, *, company: str | Company) -> Company:
        """
        Creates a new company entity.

        Parameters
        ----------
        company : Union[str, Company]
            The company name or Company object to create.

        Returns
        -------
        Company
            The created Company object.
        """
        if isinstance(company, str):
            company = Company(name=company)

        payload = company.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        this_company = Company(**response.json())
        return this_company

    def get_or_create(self, *, company: str | Company) -> Company:
        """
        Retrieves a company by its name or creates it if it does not exist.

        Parameters
        ----------
        company : Union[str, Company]
            The company name or Company object to retrieve or create.

        Returns
        -------
        Company
            The Company object if found or created.
        """
        if isinstance(company, str):
            company = Company(name=company)
        found = self.get_by_name(name=company.name, exact_match=True)
        if found:
            return found
        else:
            return self.create(company=company)

    @validate_call
    def delete(self, *, id: CompanyId) -> None:
        """Deletes a company entity.

        Parameters
        ----------
        id : str
            The ID of the company to delete.
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def rename(self, *, old_name: str, new_name: str) -> Company:
        """
        Renames an existing company entity.

        Parameters
        ----------
        old_name : str
            The current name of the company.
        new_name : str
            The new name of the company.

        Returns
        -------
        Company
            The renamed Company object
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
        """Update a Company entity. The id of the company must be provided.

        Parameters
        ----------
        company : Company
            The updated Company object.

        Returns
        -------
        Company
            The updated Company object as registered in Albert.
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=company.id)

        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(existing=current_object, updated=company)
        url = f"{self.base_path}/{company.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))
        updated_company = self.get_by_id(id=company.id)
        return updated_company
