from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.descriptors import (
    CalculateDescriptorsResponse,
    DescriptorFamily,
    DescriptorInfo,
    DescriptorInfoList,
    MoleculeDescriptors,
)


def _calculate_payload(
    *,
    smiles: list[str],
    names: list[str] | None,
    families: list[DescriptorFamily] | None,
) -> dict[str, Any]:
    """Build the calculate request body.

    ``names`` and ``families`` are omitted when the caller did not pass them, so the
    service falls back to its default descriptors. An empty list is sent as given.
    """
    payload: dict[str, Any] = {"smiles": smiles}
    config: dict[str, Any] = {}
    if names is not None:
        config["names"] = names
    if families is not None:
        config["families"] = [family.value for family in families]
    if config:
        payload["config"] = config
    return payload


class DescriptorCollection(BaseCollection):
    """Calculate molecular descriptors and read the descriptor catalog.

    Descriptors are numeric features of a molecule, computed from SMILES. The catalog
    lists every descriptor with its families, unit, and whether it needs a 3D conformer.
    Calculate accepts explicit names, feature families, or both. When neither is given,
    the service calculates its default set.

    Families differ in size and cost. ``fingerprints_ml`` is 2214 values per molecule
    (prefer ``MACCSKeys``, or one Morgan vector, by name). ``shape_3d`` embeds a 3D
    conformer, which is slower and can return a null value. A small baseline is
    ``physicochemical`` plus ``composition`` or ``functional_groups``.

    Preset bundles (``surface_asd``, ``silicon_network``, ``nitrogen_aminosilane``) are
    not accepted here. Pass their descriptor names in ``names``.

    This collection is accessed as ``client.descriptors``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.descriptors import DescriptorFamily

        client = Albert()
        catalog = client.descriptors.list_info()
        print(catalog[0].name, catalog[0].unit)

        results = client.descriptors.calculate(
            smiles=["CCO"],
            families=[DescriptorFamily.COMPOSITION],
        )
        print(results[0].descriptors[0].name, results[0].descriptors[0].value.value)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for descriptor requests.

    Methods
    -------
    list_info(all=True) -> list[DescriptorInfo]
        List catalog entries. ``all=False`` returns only the default descriptors.
    calculate(smiles, names=None, families=None) -> list[MoleculeDescriptors]
        Calculate descriptors for each SMILES.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a DescriptorCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{DescriptorCollection._api_version}/ai/chem/descriptors"

    @validate_call
    def list_info(self, *, all: bool = True) -> list[DescriptorInfo]:
        """List descriptors in the catalog.

        !!! example
            ```python
            items = client.descriptors.list_info(all=False)
            [item.name for item in items if item.default]
            ```

        Parameters
        ----------
        all : bool, optional
            When True (the default), return every descriptor. When False, return only
            the descriptors calculated when ``calculate`` is called with no names and
            no families.

        Returns
        -------
        list[DescriptorInfo]
            Catalog entries, each with its families, unit, and ``requires_3d`` flag.
        """
        response = self.session.get(f"{self.base_path}/info", params={"all": all})
        return DescriptorInfoList.model_validate(response.json()).items

    @validate_call
    def calculate(
        self,
        *,
        smiles: list[str],
        names: list[str] | None = None,
        families: list[DescriptorFamily] | None = None,
    ) -> list[MoleculeDescriptors]:
        """Calculate descriptors for each SMILES string.

        Pass ``names``, ``families``, or both. The two are combined. When neither is
        given, the service calculates its default descriptors.

        !!! example
            ```python
            from albert.resources.descriptors import DescriptorFamily

            results = client.descriptors.calculate(
                smiles=["CCO"],
                names=["MolecularWeight"],
                families=[DescriptorFamily.COMPOSITION],
            )
            results[0].descriptors[0].unit
            ```

        Parameters
        ----------
        smiles : list[str]
            Molecules to calculate, as SMILES strings.
        names : list[str], optional
            Registered descriptor names. Unknown names are rejected by the service.
        families : list[DescriptorFamily], optional
            Feature families. Each family expands to its descriptors. ``fingerprints_ml``
            is 2214 values per molecule. ``shape_3d`` embeds a 3D conformer and can
            return null.

        Returns
        -------
        list[MoleculeDescriptors]
            One result per SMILES, in request order. A null descriptor value means that
            descriptor could not be calculated for that molecule.
        """
        payload = _calculate_payload(smiles=smiles, names=names, families=families)
        response = self.session.post(self.base_path, json=payload)
        return CalculateDescriptorsResponse.model_validate(response.json()).results
