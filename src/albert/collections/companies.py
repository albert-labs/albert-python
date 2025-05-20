import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertException
from albert.resources.companies import Company
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


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

    def list(
        self,
        *,
        limit: int = 50,
        name: str | list[str] = None,
        exact_match: bool = True,
        start_key: str | None = None,
    ) -> Iterator[Company]:
        """
        Lists company entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of companies to return, by default 50.
        name : Union[str, None], optional
            The name of the company to filter by, by default None.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        Iterator
            An iterator of Company objects.
        """
        params = {"limit": limit, "dupDetection": "false", "startKey": start_key}
        if name:
            params["name"] = name if isinstance(name, list) else [name]
            params["exactMatch"] = str(exact_match).lower()
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [Company(**item) for item in items],
        )

    def company_exists(self, *, name: str, exact_match: bool = True) -> bool:
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

    def get_by_id(self, *, id: str) -> Company:
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
        found = self.list(name=name, exact_match=exact_match)
        return next(found, None)

    def create(self, *, company: str | Company, check_if_exists: bool = True) -> Company:
        """
        Creates a new company entity.

        Parameters
        ----------
        company : Union[str, Company]
            The company name or Company object to create.
        check_if_exists : bool, optional
            Whether to check if the company already exists, by default True.

        Returns
        -------
        Company
            The created Company object.
        """
        if isinstance(company, str):
            company = Company(name=company)
        hit = self.get_by_name(name=company.name, exact_match=True)
        if check_if_exists and hit:
            logging.warning(f"Company {company.name} already exists with id {hit.id}.")
            return hit

        payload = company.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        this_company = Company(**response.json())
        return this_company

    def delete(self, *, id: str) -> None:
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
