# Getting Started

## Overview
The SDK is built around two main concepts:

1. *Resource Models*: Represent individual entities like InventoryItem, Project, Company, and Tag. These are all controlled using Pydantic.

2. *Resource Collections*: Provide methods to interact with the API endpoints related to a specific resource, such as listing, creating, updating, and deleting resources.

### Resource Models
Resource Models represent the data structure of individual resources. They encapsulate the attributes and behaviors of a single resource. For example, an `InventoryItem` has attributes like `name`, `description`, `category`, and `tags`.

### Resource Collections
Resource Collections act as managers for Resource Models. They provide methods for performing CRUD operations (Create, Read, Update, Delete) on the resources. For example, the `InventoryCollection` class has methods like create, `get_by_id()`, `list()`, `update()`, and `delete()`. `list()` methods generally accept parameters to narrow the query to use it like a search.

## Usage
### Initialization
To use the SDK, you need to initialize the Albert client with your base URL and either a bearer token (which will expire) or client credientals, which will enable automatic token refresh.

```python
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

#  By default, if environment variables `ALBERT_CLIENT_ID` and `ALBERT_CLIENT_SECRET` are set you can simply do:

client = Albert()
```

## Working with Resource Collections and Models
### Example: Inventory Collection
You can interact with inventory items using the InventoryCollection class. Here is an example of how to create a new inventory item, list all inventory items, and fetch an inventory item by its ID.

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

We introduced the concept of a `EntityLink` to represent the foreign key references you can find around the Albert API. Payloads to the API expect these refrences in the EntityLink format (e.g., `{"id":x}`). However, as a convenience, you will see some value types defined as `SerializeAsEntityLink`, and then another resource name (e.g., `SerializeAsEntityLink[Location]`). This allows a user to make that reference either to a base and link or to the actual other entity, and the SDK will handle the serialization for you! For example:

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
```

## Custom Fields & Lists

`CustomFields` allow you to store custom metadata on a `Project`, `InventoryItem`, `User`, `BaseTask` (Tasks), and `Lot`. The `FieldType` used determines the shape of the medatdata field's value. If the `FieldType` is `LIST`, then the `FieldCategory` defines the ACL needed to add new allowed items to the given list. A `FieldCategory.USER_DEFINED` allows general users to add new items to the list whereas `FieldCategory.BUSINESS_DEFINED` allows only admin users to add new allowed values.

### Creating Custom Fields
```python
# Create some custom fields on projects
# Let's add a stage-gate field, which is a single allowed value from a list, and an open text field for "Project Justification"

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
    category=FieldCategory.BUSINESS_DEFINED # These are going to be defined by the business, not by any user
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

# Next, let's add some allowed values to the Stage Gate List (assumes user is an admin)

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
        name=s
        category=stage_gate_field.category,
        list_type=stage_gate_field.name,
    )
    client.lists.create(list_item=item)

# Now, let's say I want to add some Projects with this metadata.

p = Project(
    description="Example project",
    locations=[next(client.locations.list(name="My Location"))],
    metadata = {
        stage_gate_field.name: [client.lists.get_matching_item(list_type=stage_gate_field.name, name = stages[0]).to_entity_link()],
        justification_field.name: "To show an example of using custom fields."
    }
# Also note that the values of list metadata fields are list[EntityLink]
)
```
