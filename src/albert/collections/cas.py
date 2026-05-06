import re
from collections.abc import Iterator
from typing import Any

from pydantic import validate_call
from typing_extensions import deprecated

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import CasId
from albert.resources.cas import Cas


class CasPaginator(AlbertPaginator):
    """Paginator for CAS filtered search using self-managed integer offset pagination."""

    def __init__(
        self,
        *,
        path: str,
        session: AlbertSession,
        params: dict[str, Any] | None = None,
        max_items: int | None = None,
    ):
        params = dict(params or {})
        params["startKey"] = self._cas_offset = int(params.get("startKey", 0))
        params["limit"] = 50
        super().__init__(
            path=path,
            mode=PaginationMode.OFFSET,
            session=session,
            deserialize=lambda items: [Cas(**item) for item in items],
            params=params,
            max_items=max_items,
        )

    def _update_params(self, *, data: dict[str, Any], count: int) -> bool:
        self._cas_offset += count
        self.params["startKey"] = self._cas_offset
        return True


@deprecated(
    "CasCollection is deprecated and will be removed in SDK 2.0. "
    "Use client.substances_v4 instead. "
    "In SDK 2.0, all write operations target the Substance entity exclusively — "
    "CAS entities, reports, and SQL DWH tables backed by CAS will no longer be updated."
)
class CasCollection(BaseCollection):
    "CasCollection is a collection class for managing Cas entities on the Albert Platform."

    _updatable_attributes = {"notes", "description", "smiles", "metadata"}
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

    @validate_call
    def get_all(
        self,
        *,
        number: str | None = None,
        cas: list[str] | None = None,
        id: CasId | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        start_key: str | int | None = None,
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
        start_key : str | int, optional
            Pagination resume key. For unfiltered listing, pass the string key
            returned by a previous page. For filtered search (``number`` or ``cas``),
            pass an integer offset.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Cas]
            An iterator over Cas entities.
        """

        params: dict[str, Any] = {"orderBy": order_by}
        if id is not None:
            yield self.get_by_id(id=id)
            return

        if number is not None or cas:
            # Filtered search path: self-managed integer offset pagination.
            # The backend has a bug where it overwrites the numeric lastKey with a
            # string key — we must ignore lastKey and use integer offsets. (TAS-564)
            start_offset = 0
            if start_key is not None:
                try:
                    start_offset = int(start_key)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "start_key must be an integer for filtered CAS search."
                    ) from exc
            params["startKey"] = start_offset
            if number is not None:
                params["number"] = number
            if cas:
                params["cas"] = cas
            yield from CasPaginator(
                path=self.base_path,
                session=self.session,
                params=params,
                max_items=max_items,
            )
        else:
            # Unfiltered listing path: string key pagination via lastKey in response.
            if start_key is not None:
                params["startKey"] = start_key
            yield from AlbertPaginator(
                mode=PaginationMode.KEY,
                path=self.base_path,
                session=self.session,
                params=params,
                max_items=max_items,
                deserialize=lambda items: [Cas(**item) for item in items],
            )

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

    @validate_call
    def get_by_id(self, *, id: CasId) -> Cas:
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
        cleaned_number = self._clean_cas_number(number)

        if exact_match:
            for candidate in self.get_all(cas=[cleaned_number], max_items=1):
                if self._clean_cas_number(candidate.number) == cleaned_number:
                    return candidate
            return None

        for candidate in self.get_all(number=cleaned_number):
            if cleaned_number in self._clean_cas_number(candidate.number):
                return candidate
        return None

    @validate_call
    def delete(self, *, id: CasId) -> None:
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

        Notes
        -----
        The following fields can be updated: ``description``, ``metadata``, ``notes``, ``smiles``.
        """
        # Fetch the current object state from the server or database
        existing_cas = self.get_by_id(id=updated_object.id)

        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(existing=existing_cas, updated=updated_object)
        url = f"{self.base_path}/{updated_object.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))

        updated_cas = self.get_by_id(id=updated_object.id)
        return updated_cas
