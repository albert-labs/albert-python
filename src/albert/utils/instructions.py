from albert.resources.instructions import (
    Instruction,
    InstructionOrder,
    SequencePosition,
)


def _resolve_instruction_list_params(
    *,
    parent_id: str | None,
    created_by: str | None,
    updated_by: str | None,
) -> dict[str, str]:
    chosen = {"parentId": parent_id, "createdBy": created_by, "updatedBy": updated_by}
    provided = {k: v for k, v in chosen.items() if v is not None}
    if len(provided) != 1:
        raise ValueError("Exactly one of parent_id, created_by, or updated_by must be provided.")
    return provided


def _validate_instruction_for_create(instruction: Instruction) -> None:
    if not instruction.name or not instruction.parent_id:
        raise ValueError("Instruction requires a name and a parent_id.")
    if (
        instruction.design
        and instruction.design.product_id
        and instruction.design.product_id != instruction.parent_id
    ):
        raise ValueError("design.product_id must match parent_id.")


def _build_instruction_create_payload(*, instruction: Instruction) -> dict:
    design_payload: dict[str, str] = {"productId": instruction.parent_id}
    if instruction.design and instruction.design.design_row_id:
        design_payload["designRowId"] = instruction.design.design_row_id
    return {
        "name": instruction.name,
        "parentId": instruction.parent_id,
        "Design": design_payload,
    }


def _build_instruction_name_patch(*, existing: Instruction, updated: Instruction) -> dict | None:
    if "name" not in updated.model_fields_set or updated.name == existing.name:
        return None
    return {
        "id": updated.id,
        "data": [
            {
                "operation": "update",
                "attribute": "name",
                "oldValue": existing.name or "",
                "newValue": updated.name or "",
            }
        ],
    }


def _build_instruction_row_sequence_payload(
    *,
    sequence: list[InstructionOrder],
    design_row_id: str | None,
    instruction_ids: list[str],
) -> dict:
    bucket = next((bucket for bucket in sequence if bucket.design_row_id == design_row_id), None)
    if bucket is None:
        target = design_row_id if design_row_id is not None else "the formula level"
        raise ValueError(f"No instructions found for {target}.")
    current_ids = bucket.instruction_ids
    if sorted(current_ids) != sorted(instruction_ids):
        raise ValueError(
            "instruction_ids must contain exactly the IDs currently in the row, in the new order."
        )
    old_bucket: dict = {"rowSequence": current_ids}
    new_bucket: dict = {"rowSequence": instruction_ids}
    if design_row_id is not None:
        old_bucket["designRowId"] = design_row_id
        new_bucket["designRowId"] = design_row_id
    return {
        "data": [
            {
                "operation": "update",
                "attribute": "sequence",
                "oldValue": [old_bucket],
                "newValue": [new_bucket],
            }
        ]
    }


def _build_instruction_sequence_move_payload(
    *, source_id: str, reference_id: str, position: SequencePosition, version: int
) -> dict:
    return {
        "data": [
            {
                "operation": "update",
                "attribute": "sequence",
                "sourceId": source_id,
                "referenceId": reference_id,
                "position": position.value,
                "version": version,
            }
        ]
    }
