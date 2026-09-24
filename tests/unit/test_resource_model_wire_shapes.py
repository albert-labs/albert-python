"""Offline model tests pinning wire shapes the API actually sends.

Pure model validation: no client, no session, no network.
"""

from albert.resources.data_columns import DataColumn
from albert.resources.un_numbers import UnNumber


def test_data_column_default_reads_wire_key() -> None:
    """Test the API's ``default`` flag populates the model (was dropped via ``defalt`` typo)."""
    column = DataColumn.model_validate({"name": "Viscosity", "default": True})
    assert column.default is True


def test_data_column_default_serializes_as_default() -> None:
    """Test the create payload sends ``default``, not the misspelled ``defalt``."""
    column = DataColumn(name="Viscosity", default=True)
    dumped = column.model_dump(by_alias=True, exclude_unset=True, mode="json")
    assert dumped["default"] is True
    assert "defalt" not in dumped


def test_un_number_accepts_sparse_record() -> None:
    """Test sparse UN Number records validate with the fields the API omits left unset."""
    sparse = UnNumber.model_validate(
        {"unNumber": "UN1090", "albertId": "UNN1", "storageClassNumber": "3"}
    )
    assert sparse.un_number == "UN1090"
    assert sparse.storage_class_name is None
    assert sparse.shipping_description is None
    assert sparse.un_classification is None
