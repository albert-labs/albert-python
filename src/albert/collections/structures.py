from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.async_session import AsyncAlbertSession
from albert.core.session import AlbertSession
from albert.resources.structures import Structure, StructureField

# The platform accepts at most 25 structure IDs per lookup and rejects larger
# sets, as well as duplicate IDs.
_MAX_STRUCTURE_IDS = 25


def _build_get_by_ids_params(
    *, structure_ids: list[str], required_fields: list[StructureField] | None
) -> dict[str, str]:
    """Assemble lookup parameters, rejecting ID sets the platform will not accept."""
    if len(structure_ids) > _MAX_STRUCTURE_IDS:
        raise ValueError(
            f"At most {_MAX_STRUCTURE_IDS} structure IDs can be looked up at a time; "
            f"got {len(structure_ids)}."
        )
    params = {"structureId": ",".join(structure_ids)}
    if required_fields:
        params["requiredFields"] = ",".join(field.value for field in required_fields)
    return params


def _deserialize_structures(items: list[dict] | None) -> list[Structure]:
    return [Structure(**item) for item in items or []]


class StructureCollection(BaseCollection):
    """Access chemical structures in the Albert platform.

    A structure ([`Structure`][albert.resources.structures.Structure]) holds the
    identifiers and names of a chemical (SMILES, InChI, formula, common names)
    along with measured property values such as molecular weight. Both tenant
    and public structures can be looked up by ID.

    This collection is accessed as ``client.structures``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.structures import StructureField

        client = Albert()
        structures = client.structures.get_by_ids(
            structure_ids=["STT1f139757-997e-62b0-863b-4cbed10437c7"],
            required_fields=[StructureField.SMILES],
        )
        structures[0].smiles
        # 'O'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for structure requests.

    Methods
    -------
    get_by_ids(structure_ids, required_fields) -> list[Structure]
        Get multiple structures by their IDs.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a StructureCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{self._api_version}/structures"

    @validate_call
    def get_by_ids(
        self,
        *,
        structure_ids: list[str],
        required_fields: list[StructureField] | None = None,
    ) -> list[Structure]:
        """Get multiple structures by their IDs.

        IDs are accepted with or without the ``STT`` prefix. At most 25 IDs can be
        looked up at a time. Structures that cannot be found are omitted from the
        result; if none of the IDs match, a ``NotFoundError`` is raised. Duplicate
        IDs are rejected.

        Each returned structure carries only the attributes named in
        ``required_fields`` plus any measured property values (such as molecular
        weight) known for it. Include
        [`StructureField.ID`][albert.resources.structures.StructureField] in
        ``required_fields`` to tell the returned structures apart; their order is
        not guaranteed to match the input list.

        !!! example
            ```python
            from albert.resources.structures import StructureField

            structures = client.structures.get_by_ids(
                structure_ids=[
                    "STT1f139757-997e-62b0-863b-4cbed10437c7",
                    "1f1397ea-8af0-6160-915c-fe9dbf21cb03",
                ],
                required_fields=[StructureField.ID, StructureField.SMILES],
            )
            for structure in structures:
                print(structure.id, structure.smiles)
            ```

        Parameters
        ----------
        structure_ids : list[str]
            The structure IDs to look up, with or without the ``STT`` prefix.
            An empty list returns no structures.
        required_fields : list[StructureField], optional
            Narrow which attributes each returned structure carries. When omitted,
            all attributes are included.

        Returns
        -------
        list[Structure]
            The matching structures. Structures not found are omitted, and order
            is not guaranteed to match the input list.

        Raises
        ------
        ValueError
            If more than 25 structure IDs are given.
        NotFoundError
            If none of the given IDs match a structure.
        BadRequestError
            If duplicate IDs are given.
        """
        if not structure_ids:
            return []
        params = _build_get_by_ids_params(
            structure_ids=structure_ids, required_fields=required_fields
        )
        response = self.session.get(self.base_path, params=params)
        return _deserialize_structures(response.json().get("structures"))


class AsyncStructureCollection:
    """Access chemical structures in the Albert platform asynchronously.

    The async counterpart of
    [`StructureCollection`][albert.collections.structures.StructureCollection],
    accessed as ``client.structures`` on an [`AsyncAlbert`][albert.client.AsyncAlbert]
    client.

    !!! example
        ```python
        from albert import AsyncAlbert
        from albert.resources.structures import StructureField

        async with AsyncAlbert() as client:
            structures = await client.structures.get_by_ids(
                structure_ids=["STT1f139757-997e-62b0-863b-4cbed10437c7"],
                required_fields=[StructureField.SMILES],
            )
            structures[0].smiles
            # 'O'
        ```

    Parameters
    ----------
    session : AsyncAlbertSession
        The authenticated Albert async session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for structure requests.

    Methods
    -------
    get_by_ids(structure_ids, required_fields) -> list[Structure]
        Get multiple structures by their IDs.
    """

    _api_version = "v3"

    def __init__(self, *, session: AsyncAlbertSession):
        """Initialize an AsyncStructureCollection.

        Parameters
        ----------
        session : AsyncAlbertSession
            The authenticated Albert async session used for API calls.
        """
        self._session = session
        self.base_path = f"/api/{self._api_version}/structures"

    @validate_call
    async def get_by_ids(
        self,
        *,
        structure_ids: list[str],
        required_fields: list[StructureField] | None = None,
    ) -> list[Structure]:
        """Get multiple structures by their IDs.

        IDs are accepted with or without the ``STT`` prefix. At most 25 IDs can be
        looked up at a time. Structures that cannot be found are omitted from the
        result; if none of the IDs match, a ``NotFoundError`` is raised. Duplicate
        IDs are rejected.

        Each returned structure carries only the attributes named in
        ``required_fields`` plus any measured property values (such as molecular
        weight) known for it. Include
        [`StructureField.ID`][albert.resources.structures.StructureField] in
        ``required_fields`` to tell the returned structures apart; their order is
        not guaranteed to match the input list.

        !!! example
            ```python
            from albert.resources.structures import StructureField

            async with AsyncAlbert() as client:
                structures = await client.structures.get_by_ids(
                    structure_ids=["STT1f139757-997e-62b0-863b-4cbed10437c7"],
                    required_fields=[StructureField.ID, StructureField.SMILES],
                )
            ```

        Parameters
        ----------
        structure_ids : list[str]
            The structure IDs to look up, with or without the ``STT`` prefix.
            An empty list returns no structures.
        required_fields : list[StructureField], optional
            Narrow which attributes each returned structure carries. When omitted,
            all attributes are included.

        Returns
        -------
        list[Structure]
            The matching structures. Structures not found are omitted, and order
            is not guaranteed to match the input list.

        Raises
        ------
        ValueError
            If more than 25 structure IDs are given.
        NotFoundError
            If none of the given IDs match a structure.
        BadRequestError
            If duplicate IDs are given.
        """
        if not structure_ids:
            return []
        params = _build_get_by_ids_params(
            structure_ids=structure_ids, required_fields=required_fields
        )
        response = await self._session.get(self.base_path, params=params)
        return _deserialize_structures(response.json().get("structures"))
