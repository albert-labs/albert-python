# Albert Python

<div class="logo-wrapper">
  <img src="assets/Wordmark_White.png" class="logo only-dark" alt="Albert Logo">
  <img src="assets/Wordmark_Black.png" class="logo only-light" alt="Albert Logo">
</div>

[![CI](https://img.shields.io/circleci/build/github/albert-labs/albert-python/main?label=CI)](https://app.circleci.com/pipelines/github/albert-labs/albert-python?branch=main)
[![pypi](https://img.shields.io/pypi/v/albert.svg)](https://pypi.python.org/pypi/albert)
[![downloads](https://img.shields.io/pypi/dm/albert.svg)](https://pypi.org/project/albert/)<br>
[![license](https://img.shields.io/github/license/albert-labs/albert-python.svg)](https://github.com/albert-labs/albert-python/blob/main/LICENSE)

Albert Python is the official Albert Invent Software Development Kit (SDK) for Python
that provides a comprehensive and easy-to-use interface for interacting with the Albert Platform.
The SDK allows Python developers to write software that interacts with various platform resources,
such as inventories, projects, companies, tags, and many more.

## Overview

Albert Python is built around two main concepts:

1. **Resource Models**: Represent individual entities like `InventoryItem`, `Project`, `Company`, and `Tag`. These are all controlled using [Pydantic](https://docs.pydantic.dev/).

2. **Resource Collections**: Provide methods to interact with the API endpoints related to a specific resource, such as listing, creating, updating, and deleting resources.

### Resource Models

Resource Models represent the data structure of individual resources. They encapsulate the attributes and behaviors of a single resource. For example, an `InventoryItem` has attributes like `name`, `description`, `category`, and `tags`.

### Resource Collections

Resource Collections act as managers for Resource Models. They provide methods for performing CRUD operations (Create, Read, Update, Delete) on the resources. For example, the `InventoryCollection` class has methods like `create()`, `get_by_id()`, `get_all()`, `search()`, `update()`, and `delete()`. `search()` returns lightweight records for performance, while `get_all()` hydrates each item.

## Working with Resource Collections and Models

### Example: Inventory Collection

You can interact with inventory items using the `InventoryCollection` class. Here is an example of how to create a new inventory item, list all inventory items, and fetch an inventory item by its ID.

```python
from albert import Albert
from albert.resources.inventory import InventoryItem, InventoryCategory, UnitCategory

client = Albert.from_token(
    base_url="https://app.albertinvent.com",
    token="your.jwt.token"
)

# Create a new inventory item
new_inventory = InventoryItem(
    name="Goggles",
    description="Safety Equipment",
    category=InventoryCategory.EQUIPMENT,
    unit_category=UnitCategory.UNITS,
    tags=["safety", "equipment"],
    company="Company ABC"
)
created_inventory = client.inventory.create(inventory_item=new_inventory)

# List all inventory items
all_inventories = client.inventory.get_all()

# Fetch an inventory item by ID
inventory_id = "INV1"
inventory_item = client.inventory.get_by_id(inventory_id=inventory_id)

# Search an inventory item by name
inventory_item = inventory_collection.search(text="Acetone")
```

!!! warning
    ``search()`` is optimized for performance and returns partial objects.
    Use ``get_all()`` or ``get_by_ids()`` when full details are required.

## EntityLink / SerializeAsEntityLink

We introduced the concept of a `EntityLink` to represent the foreign key references you can find around the Albert API. Payloads to the API expect these refrences in the `EntityLink` format (e.g., `{"id":x}`). However, as a convenience, you will see some value types defined as `SerializeAsEntityLink`, and then another resource name (e.g., `SerializeAsEntityLink[Location]`). This allows a user to make that reference either to a base and link or to the actual other entity, and the SDK will handle the serialization for you! For example:

```python
from albert import Albert
from albert.resources.project import Project
from albert.resources.base import EntityLink

client = Albert.from_token(
    base_url="https://app.albertinvent.com",
    token="your.jwt.token"
)

my_location = next(client.locations.get_all(name="My Location")

p = Project(
    description="Example project",
    locations=[my_location]
)

# Equivalent to

p = Project(
    description="Example project",
    locations=[EntityLink(id=my_location.id)]
)

# Equivalent to

p = Project(
    description="Example project",
    locations=[my_location.to_entity_link()]
)
```
