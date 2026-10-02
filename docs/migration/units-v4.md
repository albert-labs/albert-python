# Units v3 → v4 (🧪 Beta)

!!! warning "Beta Feature"
    `units_v4` and `unit_families_v4` are currently in beta. The v3 `client.units`
    collection continues to work without any changes. Adopting the v4 collections now
    is entirely opt-in, and you can migrate at your own pace before SDK 2.0.

## What's changing

The "v3" and "v4" labels refer to the underlying Albert backend API version, not SDK
version numbers. Today, `client.units` calls the v3 backend API, which stores a flat
list of units with a free-form `category`. The new `client.units_v4` and
`client.unit_families_v4` collections wrap the v4 backend API, which introduces
**unit families** and **SI-based conversion**: a convertible unit knows its SI unit
and conversion factor, and units that share an SI basis are grouped into a family.

**Timeline:**

| SDK version | What's available |
|---|---|
| 1.x (current) | `client.units` (v3), plus `client.units_v4` and `client.unit_families_v4` (beta) |
| 2.0 (planned) | `units_v4` is renamed to `units`, `unit_families_v4` to `unit_families`; v3 is removed |

Migrating now means your code is ready for 2.0 with only a rename.

---

## What's new in v4

- **Unit families** replace the fixed `UnitCategory` enum. A family is a first-class
  record (`UnitFamilyV4`) you can create, search and update.
- **Convertible units** carry an SI mapping (`si_unit`, `si_value`) that Albert resolves
  from a reference unit symbol or a unit expression such as `"1000*g"`.
- **Non-convertible units** (for example `batch`) are linked to families explicitly.
- **Conflict checks** with `lookup()` before creating a unit or family.
- **SI preview** with `get_compatible()` to see what Albert will resolve before creating.
- **Async merge** with `merge()`, which returns a job ID instead of blocking.
- **Optimistic locking** on updates is handled for you: `update()` sends the version it
  read, so a concurrent edit fails loudly instead of being overwritten.

---

## Side-by-side comparison

| | v3 `client.units` | v4 `client.units_v4` |
|---|---|---|
| Get by ID | `get_by_id(id=...)` | `get_by_id(id=...)` |
| Bulk get | `get_by_ids(ids=[...])` | `get_by_ids(ids=[...])` |
| List / search | `get_all(name=..., category=...)` | `search(text=..., type=..., family_name=...)` |
| Create | `create(unit=Unit(...))` | `create(unit=UnitV4(...))` |
| Update | `update(unit=...)` | `update(unit=...)` |
| Delete | `delete(id=...)` | `delete(id=...)` |
| Exists check | `exists(name=...)` | `lookup(symbol=...)` or `lookup(name=...)` |
| Grouping | `UnitCategory` enum | Unit families (`client.unit_families_v4`) |
| SI conversion | ❌ | ✅ `si_unit`, `si_value`, `get_compatible()` |
| Merge | ❌ | ✅ `merge(parent_id=..., child_ids=[...])` |
| Return model | `Unit` | `UnitV4` |

---

## Migrating

### `get_by_id` / `get_by_ids`

```python
# v3
unit = client.units.get_by_id(id="UNI123")

# v4: IDs may be a UUID or a legacy UNI... ID
unit = client.units_v4.get_by_id(id="UNI123")
units = client.units_v4.get_by_ids(ids=["UNI123", "UNI456"])
```

### `get_all` → `search`

```python
from albert.resources.units import UnitCategory
from albert.resources.units_v4 import UnitV4Type

# v3
for unit in client.units.get_all(category=UnitCategory.MASS, max_items=50):
    print(unit.name, unit.symbol)

# v4: filter by family name and type instead of category
for unit in client.units_v4.search(
    family_name=["Mass"], type=[UnitV4Type.CONVERTIBLE], max_items=50
):
    print(unit.name, unit.symbol, unit.si_unit)
```

### `create`

```python
from albert.resources.units import Unit, UnitCategory
from albert.resources.units_v4 import UnitFamilyV4Ref, UnitV4, UnitV4Type

# v3
unit = client.units.create(unit=Unit(name="Grams", symbol="g", category=UnitCategory.MASS))

# v4, convertible: Albert resolves SI unit, SI value and families from ref_unit
unit = client.units_v4.create(
    unit=UnitV4(name="Grams", symbol="g", type=UnitV4Type.CONVERTIBLE, ref_unit="g")
)

# v4, non-convertible: link families by ID
unit = client.units_v4.create(
    unit=UnitV4(
        name="Batch",
        symbol="batch",
        type=UnitV4Type.NON_CONVERTIBLE,
        unit_families=[UnitFamilyV4Ref(id="UNF3")],
    )
)
```

### `update`

The get, modify, update flow is unchanged. Only fields you changed are sent.

```python
unit = client.units_v4.get_by_id(id="UNI123")
unit.synonyms = ["g", "gram", "grams"]
unit = client.units_v4.update(unit=unit)
```

!!! note "SI mapping is fixed"
    `si_unit`, `si_value`, `ref_unit`, `ref_unit_exp` and `ref_unit_value` cannot be
    changed on a convertible unit after creation, because doing so would alter
    historical measurements. Create a new unit instead.

### `exists` → `lookup`

```python
# v3
if client.units.exists(name="Grams"):
    ...

# v4: check by symbol or name, and see near-duplicates
result = client.units_v4.lookup(symbol="g")
if result.exists:
    ...
for similar in result.similar_matches:
    print(similar.symbol, similar.name)
```

### Unit families (new in v4)

```python
from albert.resources.unit_families_v4 import UnitFamilyV4, UnitFamilyV4Type

family = client.unit_families_v4.create(
    unit_family=UnitFamilyV4(
        name="Force", type=UnitFamilyV4Type.CONVERTIBLE, unit_expression="kg*m/s^2"
    )
)
print(family.si_unit, family.dimension)

for family in client.unit_families_v4.search(dimension=["Mass"]):
    print(family.name, family.si_unit)
```

---

## Models reference

All v4 models live in `albert.resources.units_v4` and
`albert.resources.unit_families_v4`. In SDK 2.0 the `V4` infix will be dropped.

| Model | Used by | Purpose |
|---|---|---|
| `UnitV4` | `create`, `get_by_id`, `get_by_ids`, `search`, `update` | Full unit record, including SI mapping and family references |
| `UnitV4Type` | `UnitV4`, `search` | `Convertible` or `Non-Convertible` |
| `UnitV4Origin` | `UnitV4`, `search` | `Albert Managed`, `Custom`, or `Custom (Legacy)` |
| `UnitFamilyV4Ref` | `UnitV4`, `UnitV4Compatible` | `{id, name}` reference to a family |
| `UnitV4Ref` | `UnitV4Lookup` | `{id, name, symbol}` reference to a unit |
| `UnitV4Lookup` | `lookup` | `exists` flag plus `similar_matches` |
| `UnitV4Compatible` | `get_compatible` | Resolved SI mapping, dimension and compatible families |
| `UnitFamilyV4` | `unit_families_v4.create`, `get_by_id`, `update` | Full unit family record, including linked unit symbols |
| `UnitFamilyV4SearchItem` | `unit_families_v4.search`, `get_by_ids` | Family record without the computed `units` and `same_si_basis_families` fields |
| `UnitFamilyV4Type`, `UnitFamilyV4Origin` | `UnitFamilyV4`, `search` | Family type and origin enums |
| `UnitFamilyV4Lookup` | `unit_families_v4.lookup` | `exists` flag plus `similar_matches` |

---

## Response model changes

| Field | v3 `Unit` | v4 `UnitV4` |
|---|---|---|
| `id` | ✅ (`UNI...`) | ✅ (UUID or `UNI...`) |
| `name`, `symbol`, `synonyms` | ✅ | ✅ |
| `category` | `UnitCategory` | ❌ replaced by `unit_families` |
| `verified` | ✅ | ❌ replaced by `origin` |
| `description` | ❌ | ✅ |
| `type` | ❌ | ✅ `UnitV4Type` |
| `si_unit`, `si_value` | ❌ | ✅ |
| `ref_unit`, `ref_unit_exp`, `ref_unit_value` | ❌ | ✅ |
| `unit_families` | ❌ | ✅ `list[UnitFamilyV4Ref]` |
| `status`, `created`, `updated` | ✅ | ✅ |
