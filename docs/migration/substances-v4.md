# Substances v3 → v4 (🧪Beta)

!!! warning "Beta Feature"
    `substances_v4` is currently in beta. The v3 `client.substances` collection
    continues to work without any changes. Adopting `substances_v4` now is
    entirely opt-in — you can migrate at your own pace before SDK 2.0.

## What's changing

The "v3" and "v4" labels refer to the underlying Albert backend API version — they
are not SDK version numbers. Today, `client.substances` calls the v3 backend API,
which supports only basic CAS-based lookups. The new `client.substances_v4`
collection wraps the v4 backend API, which is a ground-up rework that brings
richer substance data, multiple identifier types, search, and write capabilities
that simply do not exist in v3.

**Timeline:**

| SDK version | What's available |
|---|---|
| 1.x (current) | Both `client.substances` (v3) and `client.substances_v4` (beta) are available |
| 2.0 (planned) | `substances_v4` is renamed to `substances`; v3 is removed |

Migrating now means your code is ready for 2.0 with only a rename.

---

## What's new in v4

- **Multiple identifier types** — look up substances by CAS ID, substance ID (`SUB…`), or external ID; v3 supports CAS ID only.
- **Richer response model** — `SubstanceV4Info` includes toxicology data, exposure controls (ACGIH, OSHA, AIHA, NIOSH), REACH registration, carcinogen flags, and more.
- **Search** — `search()` provides paginated free-text and field-level search across the substance catalogue.
- **Create** — `create()` allows registering new substance records.
- **Metadata updates** — `update_metadata()` lets you patch notes, description, SMILES, and custom tenant metadata.

---

## Side-by-side comparison

| | v3 `client.substances` | v4 `client.substances_v4` |
|---|---|---|
| Look up by CAS | ✅ | ✅ |
| Look up by substance ID | ❌ | ✅ |
| Look up by external ID | ❌ | ✅ |
| Bulk lookup | ✅ `get_by_ids(cas_ids=[...])` | ✅ `get_by_ids(cas_ids=[], sub_ids=[], ...)` |
| Search | ❌ | ✅ `search(search_key=..., cas=..., ...)` |
| Create | ❌ | ✅ `create(substance=...)` |
| Update metadata | ❌ | ✅ `update_metadata(id=..., metadata=...)` |
| Default region | `"US"` | `"global"` |
| Return model | `SubstanceInfo` | `SubstanceV4Info` |

---

## Migrating

### `get_by_id`

```python
# v3
substance = client.substances.get_by_id(cas_id="64-17-5", region="US")

# v4
substance = client.substances_v4.get_by_id(cas_id="64-17-5")
# or by substance ID:
substance = client.substances_v4.get_by_id(sub_id="SUB00001")
```

!!! note "Region default changed"
    v3 defaults to `region="US"`. v4 defaults to `region="global"`. Pass
    `region="US"` explicitly if you rely on US-specific hazard data.

### `get_by_ids`

```python
# v3 — CAS IDs only
substances = client.substances.get_by_ids(cas_ids=["64-17-5", "67-56-1"])

# v4 — CAS IDs, substance IDs, or external IDs
substances = client.substances_v4.get_by_ids(cas_ids=["64-17-5", "67-56-1"])
substances = client.substances_v4.get_by_ids(sub_ids=["SUB00001", "SUB00002"])
```

### `search` (new in v4)

```python
from albert import Albert

client = Albert.from_client_credentials(...)

# Free-text search
for substance in client.substances_v4.search(search_key="ethanol", max_items=50):
    print(substance.name, substance.cas_id)

# Field-level search
for substance in client.substances_v4.search(cas="64-17-5"):
    print(substance.substance_id)
```

### `create` (new in v4)

```python
from albert.resources.substance_v4 import (
    SubstanceV4Create,
    SubstanceV4Identifier,
    SubstanceV4Attribute,
)

substance = SubstanceV4Create(
    identifiers=[
        SubstanceV4Identifier(attributeName="casID", value="64-17-5"),
    ],
    attributes=[
        SubstanceV4Attribute(attributeName="name", data="Ethanol"),
    ],
)
result = client.substances_v4.create(substance=substance)
print(result.created_items)
```

### `update_metadata` (new in v4)

```python
from albert.resources.substance_v4 import SubstanceV4Metadata

client.substances_v4.update_metadata(
    id="SUB00001",
    metadata=SubstanceV4Metadata(
        notes="Reviewed 2026-04",
        description="Common solvent",
        cas_smiles="CCO",
    ),
)
```

---

## Response model changes

`SubstanceV4Info` is a superset of `SubstanceInfo`. Field names are preserved
where they existed in v3; new fields are simply added.

| Field | v3 `SubstanceInfo` | v4 `SubstanceV4Info` |
|---|---|---|
| `cas_id` | ✅ | ✅ |
| `substance_id` | ❌ | ✅ |
| `ec_list_no` | ❌ | ✅ |
| `name` | `str` | `list[dict]` (multi-language) |
| `hazards` | ✅ | ✅ (same structure) |
| Toxicology | ❌ | ✅ (`oral_acute_toxicity`, etc.) |
| Exposure controls | ❌ | ✅ (ACGIH, OSHA, AIHA, NIOSH) |
| REACH | ❌ | ✅ (`reach_registration_no`) |
| Carcinogen flags | ❌ | ✅ (`ntp_carcinogen`, `iarc_carcinogen`, `osha_carcinogen`) |
