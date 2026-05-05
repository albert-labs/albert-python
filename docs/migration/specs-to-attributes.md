# Specs → Attributes (🧪 Beta)

!!! warning "Beta Feature"
    `client.attributes` is currently in beta. The existing `client.inventory.get_specs()`
    and `client.inventory.add_specs()` methods continue to work but are deprecated and will
    be removed in SDK 2.0. Adopting the new Attributes API now is entirely opt-in — you can
    migrate at your own pace.

## What's changing

The legacy Specs system is being replaced by two new concepts:

- **Attributes** — globally-defined, reusable property templates (e.g. "Viscosity @ 25°C")
  managed at the tenant level via `client.attributes`.
- **Reference Values** — the actual measured or assigned values for a given attribute on a
  specific inventory item or lot, managed via `client.attributes.add_values()` and related
  methods.

Previously, specs were defined and assigned to inventory items in a single step using
`InventorySpec`. The new API separates **definition** (what property is being tracked)
from **value** (what that property measures for this specific item).

**Timeline:**

| SDK version | What's available |
|---|---|
| 1.x (current) | Both `client.inventory.get_specs()` / `add_specs()` (deprecated) and `client.attributes` (beta) are available |
| 2.0 (planned) | `get_specs()`, `add_specs()`, `InventorySpec`, `InventorySpecValue`, `InventorySpecList` are removed |

Migrating now means your code is ready for 2.0 without further changes.

---

## What's new

- **Centralised attribute library** — attributes are defined once at the tenant level and
  reused across any number of inventory items and lots. Specs were defined per-item with no
  sharing.
- **Typed validation** — each attribute declares a `datatype` (`number`, `string`, `enum`)
  with optional range or operator constraints.
- **Lot-level values** — reference values can be assigned to individual lots (`LOT…`), not
  just inventory items.
- **Scoped reads** — `get_values(scope=ALL)` returns values for an inventory item and all
  its lots in one call.
- **Search** — `client.attributes.search()` provides full-text and field-level search across
  the attribute catalogue.

---

## Side-by-side comparison

| | `client.inventory` (deprecated) | `client.attributes` (new) |
|---|---|---|
| Define a property | Inline in `InventorySpec` | `client.attributes.create(attribute=...)` |
| Assign a value to inventory | `add_specs(inventory_id=..., specs=[...])` | `add_values(parent_id=..., values=[...])` |
| Read values for inventory | `get_specs(ids=[...])` | `get_values(parent_id=..., scope=SELF)` |
| Read values for inventory + lots | ❌ not supported | `get_values(parent_id=..., scope=ALL)` |
| Read values for lots only | ❌ not supported | `get_values(parent_id=..., scope=LOT)` |
| Bulk read across many items | ❌ not supported | `get_bulk_values(parent_ids=[...])` |
| Remove a specific value | ❌ not supported | `delete_values(parent_id=..., attribute_ids=[...])` |
| Remove all values | ❌ not supported | `clear_values(parent_id=...)` |
| Search attributes | ❌ not supported | `client.attributes.search(text=...)` |
| Shared attribute definitions | ❌ not supported | ✅ defined once, used everywhere |
| Return model | `InventorySpecList` | `AttributeValuesResponse` |

---

## Migrating

### Step 1 — Create attribute definitions

In the old system, property definitions lived inside each `InventorySpec`. In the new system,
you define attributes once and reuse them.

```python
from albert.resources.attributes import Attribute, AttributeCategory, ValidationItem
from albert.resources.parameter_groups import DataType, Operator

# Create a reusable "Viscosity" attribute
viscosity_attr = client.attributes.create(
    attribute=Attribute(
        datacolumn_id="DAC123",           # the data column this property maps to
        category=AttributeCategory.PROPERTY,
        reference_name="Viscosity @ 25°C",
        validation=[
            ValidationItem(
                datatype=DataType.NUMBER,
                min=0.0,
                max=500.0,
                operator=Operator.BETWEEN,
            )
        ],
    )
)
print(viscosity_attr.id)  # e.g. "ATR469"
```

---

### Step 2 — Assign values to inventory items

```python
from albert.resources.attributes import AttributeValue

# Before (deprecated)
from albert.resources.inventory import InventorySpec, InventorySpecValue

client.inventory.add_specs(
    inventory_id="INVA123",
    specs=[
        InventorySpec(
            name="Viscosity",
            data_column_id="DAC123",
            value=InventorySpecValue(reference="45.2"),
        )
    ],
)

# After
client.attributes.add_values(
    parent_id="INVA123",
    values=[
        AttributeValue(attributeId=viscosity_attr.id, referenceValue=45.2),
    ],
)
```

`add_values` is upsert — if a value already exists for an attribute it is updated, not
duplicated.

---

### Step 3 — Read values back

```python
# Before (deprecated)
spec_lists = client.inventory.get_specs(ids=["INVA123"])
for spec_list in spec_lists:
    for spec in spec_list.specs:
        print(spec.name, spec.value.reference)

# After — inventory item only (scope defaults to SELF)
for response in client.attributes.get_values(parent_id="INVA123"):
    for attr_value in response.attributes:
        print(attr_value.attribute_definition.name, attr_value.reference_value)

# After — inventory item + all its lots
for response in client.attributes.get_values(
    parent_id="INVA123",
    scope=AttributeScope.ALL,
):
    print(response.parent_id)
    for attr_value in response.attributes:
        print(attr_value.attribute_definition.name, attr_value.reference_value)
```

---

### Removing values

The old `InventorySpec` API had no way to remove values. The new API supports both targeted
and full removal.

```python
# Remove a specific attribute's value
client.attributes.delete_values(
    parent_id="INVA123",
    attribute_ids=["ATR469"],
)

# Remove all attribute values from an inventory item
client.attributes.clear_values(parent_id="INVA123")

# Remove all values from an inventory item and all its lots
client.attributes.clear_values(parent_id="INVA123", scope=AttributeScope.ALL)
```

---

## Resource model changes

| | `InventorySpec` (deprecated) | `AttributeValue` + `AttributeValuesResponse` (new) |
|---|---|---|
| Property identifier | `data_column_id: str` (inline) | `attribute_id: AttributeId` (references a shared `Attribute`) |
| Value | `InventorySpecValue.reference: str` | `reference_value: str \| float \| None` |
| Range | `InventorySpecValue.min`, `.max` | `AttributeValueRange.min`, `.max`, `.comparison_operator` |
| Property metadata | Embedded in `InventorySpec` | Separate `AttributeDefinition` (name, datacolumn, unit, validation, prmCount) |
| Lot-level support | ❌ | ✅ — any `parent_id` including `LOT…` IDs |

---

## Deprecated symbols

The following are deprecated in 1.x and will be removed in 2.0:

| Symbol | Replacement |
|---|---|
| `client.inventory.get_specs()` | `client.attributes.get_values()` |
| `client.inventory.add_specs()` | `client.attributes.add_values()` |
| `InventorySpec` | `Attribute` + `AttributeValue` |
| `InventorySpecValue` | `AttributeValueRange` |
| `InventorySpecList` | `AttributeValuesResponse` |
