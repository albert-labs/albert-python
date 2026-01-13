from collections.abc import Iterable
from typing import Any

from albert.core.shared.models.base import BaseResource, EntityLink
from albert.resources.inventory import CasAmount


def _cas_identifier(cas_amount: CasAmount) -> str | None:
    """Return the identifier used for CAS patch operations."""
    if cas_amount.id:
        return cas_amount.id
    if cas_amount.cas is not None and cas_amount.cas.id:
        return cas_amount.cas.id
    raise ValueError("CasAmount must include an identifier.")


def _raise_duplicate_cas_error(*, identifier: str | None = None) -> None:
    raise ValueError(f"Can't add duplicate CAS {identifier}")


def _ensure_unique_cas_amounts(cas_amounts: Iterable[CasAmount]) -> None:
    """Ensure there are no duplicate CAS identifiers in a collection of `CasAmount` entries."""
    seen: set[str] = set()
    for cas_amount in cas_amounts:
        identifier = _cas_identifier(cas_amount)
        if identifier in seen:
            _raise_duplicate_cas_error(identifier=identifier)
        seen.add(identifier)


def _build_cas_add_operation(cas_amount: CasAmount) -> dict[str, Any]:
    identifier = _cas_identifier(cas_amount)

    operation: dict[str, Any] = {
        "operation": "add",
        "attribute": "casId",
        "newValue": identifier,
    }
    if cas_amount.min is not None:
        operation["min"] = cas_amount.min
    if cas_amount.max is not None:
        operation["max"] = cas_amount.max
    if cas_amount.cas_category is not None:
        operation["casCategory"] = cas_amount.cas_category
    if cas_amount.type:
        operation["type"] = cas_amount.type
    if cas_amount.classification_type:
        operation["classificationType"] = cas_amount.classification_type
    return operation


def _build_cas_delete_operation(identifier: str) -> dict[str, Any]:
    return {
        "operation": "delete",
        "attribute": "casId",
        "oldValue": identifier,
    }


def _normalize_inventory_function_ids(
    value: list[BaseResource | EntityLink | str] | None,
) -> list[str]:
    if not value:
        return []
    ids: list[str] = []
    for item in value:
        if isinstance(item, str):
            if item:
                ids.append(item)
            continue
        if isinstance(item, BaseResource):
            if item.id:
                ids.append(item.id)
            continue
        if isinstance(item, EntityLink):
            if item.id:
                ids.append(item.id)
            continue
    return ids


def _build_inventory_function_operations(
    *,
    entity_id: str,
    existing: list[BaseResource | EntityLink | str] | None,
    updated: list[BaseResource | EntityLink | str] | None,
) -> list[dict[str, Any]]:
    existing_ids = set(_normalize_inventory_function_ids(existing))
    updated_ids = set(_normalize_inventory_function_ids(updated))
    to_add = sorted(updated_ids - existing_ids)
    to_delete = sorted(existing_ids - updated_ids)

    operations: list[dict[str, Any]] = []
    if to_add:
        operations.append(
            {
                "attribute": "inventoryFunction",
                "entityId": entity_id,
                "operation": "add",
                "newValue": to_add,
            }
        )
    if to_delete:
        operations.append(
            {
                "attribute": "inventoryFunction",
                "entityId": entity_id,
                "operation": "delete",
                "oldValue": to_delete,
            }
        )
    return operations


def _build_cas_scalar_operation(
    *,
    attribute: str,
    entity_id: str,
    old_value: Any,
    new_value: Any,
) -> dict[str, Any] | None:
    if old_value == new_value:
        return None

    payload: dict[str, Any] = {
        "attribute": attribute,
        "entityId": entity_id,
    }

    if new_value is None:
        if old_value is None:
            return None
        payload.update(
            {
                "operation": "delete",
                "oldValue": old_value,
            }
        )
        return payload

    payload["newValue"] = new_value
    if old_value is None:
        payload["operation"] = "add"
        return payload

    payload.update(
        {
            "operation": "update",
            "oldValue": old_value,
        }
    )
    return payload


def _build_cas_update_operations(existing: CasAmount, updated: CasAmount) -> list[dict[str, Any]]:
    identifier = _cas_identifier(updated) or _cas_identifier(existing)

    scalar_operations = [
        ("max", existing.max, updated.max),
        ("min", existing.min, updated.min),
        ("inventoryValue", existing.target, updated.target),
        ("casCategory", existing.cas_category, updated.cas_category),
    ]

    operations: list[dict[str, Any]] = []
    for attribute, old_value, new_value in scalar_operations:
        operation = _build_cas_scalar_operation(
            attribute=attribute,
            entity_id=identifier,
            old_value=old_value,
            new_value=new_value,
        )
        if operation is not None:
            operations.append(operation)

    operations.extend(
        _build_inventory_function_operations(
            entity_id=identifier,
            existing=existing.inventory_function,
            updated=updated.inventory_function,
        )
    )

    return operations


def _build_cas_patch_operations(
    *,
    existing: list[CasAmount] | None,
    updated: list[CasAmount] | None,
) -> list[dict[str, Any]]:
    existing = existing or []
    updated = updated or []

    _ensure_unique_cas_amounts(updated)

    existing_lookup = {
        identifier: cas_amount
        for cas_amount in existing
        if (identifier := _cas_identifier(cas_amount)) is not None
    }
    updated_lookup = {
        identifier: cas_amount
        for cas_amount in updated
        if (identifier := _cas_identifier(cas_amount)) is not None
    }

    operations: list[dict[str, Any]] = []

    for cas_amount in [
        updated_lookup[key] for key in updated_lookup.keys() - existing_lookup.keys()
    ]:
        identifier = _cas_identifier(cas_amount)
        if identifier is None:
            continue
        operations.append(_build_cas_add_operation(cas_amount))
        if cas_amount.target is not None:
            target_operation = _build_cas_scalar_operation(
                attribute="inventoryValue",
                entity_id=identifier,
                old_value=None,
                new_value=cas_amount.target,
            )
            if target_operation is not None:
                operations.append(target_operation)
        operations.extend(
            _build_inventory_function_operations(
                entity_id=identifier,
                existing=None,
                updated=cas_amount.inventory_function,
            )
        )

    removals = [existing_lookup[key] for key in existing_lookup.keys() - updated_lookup.keys()]
    for cas_amount in removals:
        identifier = _cas_identifier(cas_amount)
        if identifier is None:
            continue
        operations.append(_build_cas_delete_operation(identifier))

    for identifier in existing_lookup.keys() & updated_lookup.keys():
        operations.extend(
            _build_cas_update_operations(
                existing=existing_lookup[identifier],
                updated=updated_lookup[identifier],
            )
        )

    return operations
