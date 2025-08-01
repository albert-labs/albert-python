import re
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.resources.cas import Cas


class CasCollection(BaseCollection):
    "CasCollection is a collection class for managing Cas entities on the Albert Platform."

    _updatable_attributes = {"notes", "description", "smiles"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CasCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{CasCollection._api_version}/cas"

    def get_all(
        self,
        *,
        number: str | None = None,
        cas: list[str] | None = None,
        id: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Cas]:
        """
        Get all CAS entities with optional filters.

        Parameters
        ----------
        number : str, optional
            Filter CAS entities by CAS number.
        cas : list[str] | None, optional
            Filter CAS entities by a list of CAS numbers.
        id : str, optional
            Filter CAS entities by Albert CAS ID.
        order_by : OrderBy, optional
            Sort direction (ascending or descending). Default is DESCENDING.
        start_key : str, optional
            The pagination key to start fetching from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Cas]
            An iterator over Cas entities.
        """

        if cas:
            params = {
                "orderBy": order_by.value,
                "cas": cas,
            }

            response = self.session.get(url=self.base_path, params=params)
            items = response.json().get("Items", [])

            yield from [Cas(**item) for item in items]
            return

        params = {"orderBy": order_by.value, "startKey": start_key}

        cas_items = AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=None,
            deserialize=lambda items: [Cas(**item) for item in items],
        )

        # Apply custom filtering until https://linear.app/albert-invent/issue/TAS-564/inconsistent-cas-pagination-behaviour is fixed.
        def filtered_items() -> Iterator[Cas]:
            count = 0
            for item in cas_items:
                if number is not None and number not in item.number:
                    continue
                if id is not None and item.id != id:
                    continue
                yield item
                count += 1
                if max_items is not None and count >= max_items:
                    break

        yield from filtered_items()

    def exists(self, *, number: str, exact_match: bool = True) -> bool:
        """
        Checks if a CAS exists by its number.

        Parameters
        ----------
        number : str
            The number of the CAS to check.
        exact_match : bool, optional
            Whether to match the number exactly, by default True.

        Returns
        -------
        bool
            True if the CAS exists, False otherwise.
        """
        cas_list = self.get_by_number(number=number, exact_match=exact_match)
        return cas_list is not None

    def create(self, *, cas: str | Cas) -> Cas:
        """
        Creates a new CAS entity.

        Parameters
        ----------
        cas : Union[str, Cas]
            The CAS number or Cas object to create.

        Returns
        -------
        Cas
            The created Cas object.
        """
        if isinstance(cas, str):
            cas = Cas(number=cas)

        payload = cas.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        cas = Cas(**response.json())
        return cas

    def get_or_create(self, *, cas: str | Cas) -> Cas:
        """
        Retrieves a CAS by its number or creates it if it does not exist.

        Parameters
        ----------
        cas : Union[str, Cas]
            The CAS number or Cas object to retrieve or create.

        Returns
        -------
        Cas
            The Cas object if found or created.
        """
        if isinstance(cas, str):
            cas = Cas(number=cas)
        found = self.get_by_number(number=cas.number, exact_match=True)
        if found:
            return found
        else:
            return self.create(cas=cas)

    def get_by_id(self, *, id: str) -> Cas:
        """
        Retrieves a CAS by its ID.

        Parameters
        ----------
        id : str
            The ID of the CAS to retrieve.

        Returns
        -------
        Cas
            The Cas object if found, None otherwise.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        cas = Cas(**response.json())
        return cas

    def _clean_cas_number(self, text: str):
        """
        Cleans up strings that start with a CAS-like number by removing excess spaces within the CAS number format.
        This function mimics how the Albert backend checks for matching CAS numbers.
        Parameters:
        - text: str, the input string to clean.

        Returns:
        - str, the cleaned string with corrected CAS number formatting.
        """

        # Regex pattern to match CAS numbers at the start of the string (e.g., "50  - 0 -0")
        pattern = r"^(\d+)\s*-\s*(\d+)\s*-\s*(\d+)"

        # Replace matched CAS number patterns with cleaned-up format
        cleaned_text = re.sub(pattern, r"\1-\2-\3", text)

        return cleaned_text

    def get_by_number(self, *, number: str, exact_match: bool = True) -> Cas | None:
        """
        Retrieves a CAS by its number.

        Parameters
        ----------
        number : str
            The number of the CAS to retrieve.
        exact_match : bool, optional
            Whether to match the number exactly, by default True.

        Returns
        -------
        Optional[Cas]
            The Cas object if found, None otherwise.
        """
        found = self.get_all(cas=[number])
        if exact_match:
            for f in found:
                if self._clean_cas_number(f.number) == self._clean_cas_number(number):
                    return f
        return next(found, None)

    def delete(self, *, id: str) -> None:
        """
        Deletes a CAS by its ID.

        Parameters
        ----------
        id : str
            The ID of the CAS to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def update(self, *, updated_object: Cas) -> Cas:
        """Updates a CAS entity. The updated object must have the same ID as the object you want to update.

        Parameters
        ----------
        updated_object : Cas
            The Updated Cas object.

        Returns
        -------
        Cas
            The updated Cas object as it appears in Albert
        """
        # Fetch the current object state from the server or database
        existing_cas = self.get_by_id(id=updated_object.id)

        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(existing=existing_cas, updated=updated_object)
        url = f"{self.base_path}/{updated_object.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))

        updated_cas = self.get_by_id(id=updated_object.id)
        return updated_cas
