from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.cas import Cas
from albert.session import AlbertSession


class CasCollection(BaseCollection):
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

    def _list_generator(
        self,
        *,
        limit: int = 50,
        start_key: str | None = None,
        number: str | None = None,
        id: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Generator[Cas, None, None]:
        """
        Lists CAS entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of CAS entities to return, by default 50.
        start_key : Optional[str], optional
            The primary key of the first item that this operation will evaluate.
        number : Optional[str], optional
            Fetches list of CAS by CAS number.
        id : Optional[str], optional
            Fetches list of CAS using the CAS Albert ID.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.

        Yields
        -------
        Generator
            A Generator of Cas objects.
        """
        params = {"limit": limit, "orderBy": order_by.value}
        if start_key:  # pragma: no cover
            params["startKey"] = start_key
        if number:
            params["number"] = number
        if id:
            params["albertId"] = id
        while True:
            response = self.session.get(self.base_path, params=params)
            cas_data = response.json().get("Items", [])
            if not cas_data or cas_data == []:
                break
            for x in cas_data:
                this_cas = Cas(**x)
                yield this_cas
            start_key = response.json().get("lastKey")
            if not start_key:  # start key is tested here but not on init
                break
            params["startKey"] = start_key

    def list(
        self,
        *,
        number: str | None = None,
        id: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Iterator[Cas]:
        """
        Lists CAS entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of CAS entities to return, by default 50.
        start_key : Optional[str], optional
            The primary key of the first item that this operation will evaluate.
        number : Optional[str], optional
            Fetches list of CAS by CAS number.
        id : Optional[str], optional
            Fetches list of CAS using the CAS Albert ID.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.

        Returns
        -------
        Generator
            A generator of Cas objects.
        """
        return self._list_generator(number=number, order_by=order_by, id=id)

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
            payload = cas.model_dump(by_alias=True, exclude_unset=True)
            response = self.session.post(self.base_path, json=payload)
            cas = Cas(**response.json())
            return cas

    def get_by_id(self, *, cas_id: str) -> Cas:
        """
        Retrieves a CAS by its ID.

        Parameters
        ----------
        cas_id : str
            The ID of the CAS to retrieve.

        Returns
        -------
        Cas
            The Cas object if found, None otherwise.
        """
        url = f"{self.base_path}/{cas_id}"
        response = self.session.get(url)
        cas = Cas(**response.json())
        return cas

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
                if f.number.replace(" ", "") == number:
                    return f
        return next(found, None)

    def delete(self, *, cas_id: str) -> None:
        """
        Deletes a CAS by its ID.

        Parameters
        ----------
        cas_id : str
            The ID of the CAS to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{cas_id}"
        self.session.delete(url)

    def update(self, *, updated_object: Cas) -> Cas:
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(cas_id=updated_object.id)

        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(
            existing=current_object, updated=updated_object
        )

        url = f"{self.base_path}/{updated_object.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))

        updated_cas = self.get_by_id(cas_id=updated_object.id)
        return updated_cas
