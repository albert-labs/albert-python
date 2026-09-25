"""Offline tests pinning request/response wire shapes against the API.

Pure validation helpers and model parsing: no client, no session, no network.
"""

from albert.collections.users import UserCollection
from albert.resources.data_columns import DataColumn
from albert.resources.roles import Role
from albert.resources.un_numbers import UnNumber
from albert.resources.users import UserFilterType


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


def test_role_accepts_missing_tenant() -> None:
    """Test role-only (id-filtered) responses validate without a ``tenant`` key."""
    role = Role.model_validate({"albertId": "ROL1", "name": "Administrator"})
    assert role.id == "ROL1"
    assert role.tenant is None


def test_user_filter_id_keeps_known_prefixes() -> None:
    """Test role-filtered user listing keeps ROL ids instead of rewriting them to USR."""
    assert UserCollection._normalize_filter_id("ROL1", type=UserFilterType.ROLE) == "ROL1"
    assert UserCollection._normalize_filter_id("rol1", type=UserFilterType.ROLE) == "ROL1"
    assert UserCollection._normalize_filter_id("USR12", type=UserFilterType.ROLE) == "USR12"
    assert UserCollection._normalize_filter_id("usr12", type=None) == "USR12"


def test_user_filter_id_prefixes_bare_ids_by_type() -> None:
    """Test bare filter ids get the prefix implied by the filter type."""
    assert UserCollection._normalize_filter_id("12", type=None) == "USR12"
    assert UserCollection._normalize_filter_id("1", type=UserFilterType.ROLE) == "ROL1"
