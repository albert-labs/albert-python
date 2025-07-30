# Concepts

This document outlines the core concepts used throughout the Albert Python SDK. Understanding these concepts will help you use the SDK more effectively and customize your integrations with the Albert platform.

---

## Resource Models

Resource Models represent individual entities in the Albert API, such as `InventoryItem`, `Project`, `Company`, `Tag`, `User`, and many more. These models are implemented using [Pydantic](https://docs.pydantic.dev/) and define the structure of the data being exchanged with the API.

Each model supports validation, serialization, and automatic handling of nested objects.

### Example

```python
from albert.resources.inventory import InventoryItem, InventoryCategory

item = InventoryItem(
    name="Goggles",
    description="Safety Equipment",
    category=InventoryCategory.EQUIPMENT
)
```

---

## Resource Collections

Each Resource Model has a corresponding Collection that acts as its manager. These collections expose methods to interact with the Albert backend APIs.

### Common Methods

- `create()` – Create a new resource.
- `get_by_id()` – Retrieve a specific resource by its ID.
- `get_all()` – List all matching resources.
- `search()` – Perform a lightweight search, returns partial records.
- `update()` – Modify a resource.
- `delete()` – Remove a resource.

### Example

```python
from albert import Albert

client = Albert.from_token(token="your.jwt.token")
all_projects = client.projects.get_all()
```

---

## EntityLink and SerializeAsEntityLink

The Albert API represents foreign key relationships using minimal JSON objects like `{ "id": "abc123" }`. This pattern is modeled using the `EntityLink` class.

The SDK simplifies this using `SerializeAsEntityLink[T]`, which accepts either the full object or just an `EntityLink`, and handles the conversion internally.

### Example

```python
from albert.resources.project import Project
from albert.resources.base import EntityLink

# Directly use EntityLink
project = Project(
    description="Example",
    locations=[EntityLink(id="loc123")]
)

# Or pass full object and let SDK convert
location = client.locations.get_by_id("loc123")
project = Project(
    description="Example",
    locations=[location]  # Automatically converted
)
```

---

## Authentication

The SDK supports multiple authentication flows:

- `from_token(...)` – Use a static JWT token.
- `client_credentials=...` – Use OAuth2 Client ID and Secret.
- `auth_manager=AlbertSSOClient(...)` – Use interactive browser-based SSO.

Each authenticated `Albert` instance provides access to all resource collections.

---

## Metadata and Custom Fields

`CustomFields` allow you to store custom metadata on a `Project`, `InventoryItem`, `User`, `BaseTask` (Tasks), and `Lot`. The `FieldType` used determines the shape of the metadata field's value. If the `FieldType` is `LIST`, then the `FieldCategory` defines the ACL needed to add new allowed items to the given list. A `FieldCategory.USER_DEFINED` allows general users to add new items to the list whereas `FieldCategory.BUSINESS_DEFINED` allows only admin users to add new allowed values.

### Creating Custom Fields

```python
from albert import Albert
from albert.resources.custom_fields import CustomField, FieldCategory, FieldType, ServiceType
from albert.resources.lists import ListItem
from albert.resources.project import Project

stage_gate_field = CustomField(
    name="stage_gate_status",
    display_name="Stage Gate",
    field_type=FieldType.LIST,
    service=ServiceType.PROJECTS,
    min=1,
    max=1,
    category=FieldCategory.BUSINESS_DEFINED
)

justification_field = CustomField(
    name="justification",
    display_name="Project Justification",
    field_type=FieldType.STRING,
    service=ServiceType.PROJECTS,
)

client = Albert()

client.custom_fields.create(stage_gate_field)
client.custom_fields.create(justification_field)

stages = [
    "1. Discovery",
    "2. Concept Validation",
    "3. Proof of Concept",
    "4. Prototype Development",
    "5. Preliminary Evaluation",
    "6. Feasibility Study",
    "7. Optimization",
    "8. Scale-Up",
    "9. Regulatory Assessment",
]

for s in stages:
    item = ListItem(
        name=s,
        category=stage_gate_field.category,
        list_type=stage_gate_field.name,
    )
    client.lists.create(list_item=item)

p = Project(
    description="Example project",
    locations=[next(client.locations.get_all(name="My Location"))],
    metadata={
        stage_gate_field.name: [client.lists.get_matching_item(list_type=stage_gate_field.name, name=stages[0]).to_entity_link()],
        justification_field.name: "To show an example of using custom fields."
    }
    # Note: the values of list metadata fields are list[EntityLink]
)
```

---

## Partial vs Full Records

- `search()` returns **partial records** for performance. These contain minimal fields.
- `get_all()` or `get_by_id()` return **fully hydrated** records.

This allows faster operations when full data isn't needed.

!!! warning
    Use `get_all()` or `get_by_ids()` when you need complete information. `search()` is optimized for speed and returns partial data.

---

## Pagination

Many methods in the SDK support pagination via the `max_items` parameter. The SDK handles pagination behind the scenes to return a complete list.

```python
projects = client.projects.get_all(max_items=200)
```

Use `search()` + `max_items` when working with large datasets.

---

## Tagging

Some resources like InventoryItems and Projects support tags. Tags are strings and can be freely defined by users.

```python
item = InventoryItem(
    name="Gloves",
    tags=["safety", "lab"]
)
```

Tags are searchable and help categorize content.

---

## Summary

Concepts you should know:

| Concept                 | Purpose                                      |
|-------------------------|----------------------------------------------|
| Resource Models         | Define the structure of data entities        |
| Resource Collections    | Manage CRUD operations for each model        |
| EntityLink              | Represents foreign key references            |
| Custom Fields & Lists   | Add structured metadata to resources         |
| SerializeAsEntityLink  | Allows transparent references or links       |
| Authentication          | Supports static token, OAuth2, and SSO       |
| Partial Records         | Lightweight search results                   |
| Tags and Metadata       | Categorize and extend data                   |

These concepts form the foundation of working effectively with the Albert SDK.
