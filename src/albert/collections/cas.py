import re
from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.cas import Cas
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


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

    def list(
        self,
        *,
        limit: int = 50,
        start_key: str | None = None,
        number: str | None = None,
        id: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Iterator[Cas]:
        """
        Lists CAS entities with optional filters.

        Parameters
        ----------
        limit : int | None, optional
            The maximum number of CAS entities to return, by default 50.
        start_key : str | None, optional
            The primary key of the first item that this operation will evaluate.
        number : str | None, optional
            Fetches list of CAS by CAS number.
        id : str | None, optional
            Fetches list of CAS using the CAS Albert ID.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.

        Returns
        -------
        Iterator[Cas]
            An iterator of Cas objects.
        """
        params = {
            "limit": limit,
            "orderBy": order_by.value,
            "startKey": start_key,
            "number": number,
            "albertId": id,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [Cas(**item) for item in items],
        )

    def cas_exists(self, *, number: str, exact_match: bool = True) -> bool:
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
        hit = self.get_by_number(number=cas.number, exact_match=True)
        if hit:
            return hit
        else:
            payload = cas.model_dump(by_alias=True, exclude_unset=True, mode="json")
            response = self.session.post(self.base_path, json=payload)
            cas = Cas(**response.json())
            return cas

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

    import re

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
        found = self.list(number=number)
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
