# Albert Python

<div class="logo-wrapper">
  <img src="assets/Wordmark_White.png" class="logo only-dark" alt="Albert Logo">
  <img src="assets/Wordmark_Black.png" class="logo only-light" alt="Albert Logo">
</div>



## Installation

You can install Albert Python using pip:

```bash
pip install albert
```

The latest stable release is available on [PyPI](https://pypi.org/project/albert/).

## Overview
Albert Python is built around two main concepts:

1. **Resource Models**: Represent individual entities like `InventoryItem`, `Project`, `Company`, and `Tag`. These are all controlled using [Pydantic](https://docs.pydantic.dev/).

2. **Resource Collections**: Provide methods to interact with the API endpoints related to a specific resource, such as listing, creating, updating, and deleting resources.

### Resource Models
Resource Models represent the data structure of individual resources. They encapsulate the attributes and behaviors of a single resource. For example, an `InventoryItem` has attributes like `name`, `description`, `category`, and `tags`.

### Resource Collections
Resource Collections act as managers for Resource Models. They provide methods for performing CRUD operations (Create, Read, Update, Delete) on the resources. For example, the `InventoryCollection` class has methods like create, `get_by_id()`, `list()`, `update()`, and `delete()`. `list()` methods generally accept parameters to narrow the query to use it like a search.

## Usage
### Initialization
To use Albert Python, you need to initialize the Albert client with your base URL and either a bearer token (which will expire) or client credientals, which will enable automatic token refresh.

```python
import os

from albert import Albert, ClientCredentials

# Initialize the client using a JWT token
client = Albert(
    base_url="https://app.albertinvent.com/", # example value
    token = os.getenv("ALBERT_TOKEN") # example value
)


# Initalize using an API key from environment

client = Albert(
    client_credentials=ClientCredentials.from_env(
        client_id_env="ALBERT_CLIENT_ID",
        client_secret_env="ALBERT_CLIENT_SECRET",
    )
)

#  By default, if environment variables `ALBERT_CLIENT_ID` and `ALBERT_CLIENT_SECRET` are set, you can simply do:

client = Albert()
```

## Working with Resource Collections and Models
### Example: Inventory Collection
You can interact with inventory items using the `InventoryCollection` class. Here is an example of how to create a new inventory item, list all inventory items, and fetch an inventory item by its ID.

```python
from albert import Albert
from albert.resources.inventory import InventoryItem, InventoryCategory, UnitCategory

client = Albert()

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
all_inventories = client.inventory.list()

# Fetch an inventory item by ID
inventory_id = "INV1"
inventory_item = client.inventory.get_by_id(inventory_id=inventory_id)

# Search an inventory item by name
inventory_item = inventory_collection.list(name="Acetone")
```

## EntityLink / SerializeAsEntityLink

We introduced the concept of a `EntityLink` to represent the foreign key references you can find around the Albert API. Payloads to the API expect these refrences in the `EntityLink` format (e.g., `{"id":x}`). However, as a convenience, you will see some value types defined as `SerializeAsEntityLink`, and then another resource name (e.g., `SerializeAsEntityLink[Location]`). This allows a user to make that reference either to a base and link or to the actual other entity, and the SDK will handle the serialization for you! For example:

```python
from albert import Albert
from albert.resources.project import Project
from albert.resources.base import EntityLink

client = Albert()

my_location = next(client.locations.list(name="My Location")

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