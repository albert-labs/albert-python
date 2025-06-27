# Albert Python

<div align="center">
    <img src="assets/Wordmark_Black.png" alt="Albert Logo" style="max-width: 300px; margin-bottom: 4rem;">
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

Resource Collections act as managers for Resource Models. They provide methods for performing CRUD operations (Create, Read, Update, Delete) on the resources. For example, the `InventoryCollection` class has methods like `create()`, `get_by_id()`, `get_all()`, `search()`, `update()`, and `delete()`. `search()` returns lightweight records for performance, while `get_all()` hydrates each item.

## Usage

### Authentication

Albert Python SDK supports three authentication methods:

* **Single Sign-On (SSO)** via browser-based OAuth2
* **Client Credentials** using a client ID and secret
* **Static Token** using a pre-generated token (via the `ALBERT_TOKEN` environment variable)

Static token-based authentication is suitable for temporary or testing purposes and does not support token refresh.

These modes are supported via the `auth_manager` or `token` argument to the `Albert` client.

---

#### 🔐 SSO (Browser-Based Login)

This is the recommended method for users authenticating interactively. It opens a browser window to authenticate using your email address and automatically manages tokens. The SSO client uses a local redirect server to complete the flow.

```python
from albert import Albert, AlbertSSOClient

sso = AlbertSSOClient(
    base_url="https://app.albertinvent.com",
    email="your-name@albertinvent.com",
)

# IMPORTANT: You must call authenticate() to complete the login flow
sso.authenticate()

client = Albert(base_url="https://app.albertinvent.com", auth_manager=sso)
```

Alternatively, you can use the helper constructor:

```python
client = Albert.from_sso(
    base_url="https://app.albertinvent.com",
    email="your-name@albertinvent.com"
)
```

!!! note
    You **must** call `sso.authenticate()` before using the client. This method launches a local HTTP server and opens the default browser for login.

---

#### 🔑 Client Credentials (Programmatic Access)

This method implements the OAuth2 Client Credentials flow and is suitable for non-interactive usage, like backend services or automation scripts. It manages token acquisition and refresh automatically via the `AlbertClientCredentials` class.

This method is ideal for server-to-server or CI/CD scenarios. You can authenticate using a client ID and secret, and the SDK will manage token fetching and refresh automatically.

You can use the helper constructor:

```python
from albert import Albert, AlbertClientCredentials

client = Albert.from_client_credentials(
    client_id="your-client-id",
    client_secret="your-client-secret",
    base_url="https://app.albertinvent.com"
)
```

Or load credentials from environment,

```python
creds = AlbertClientCredentials.from_env()
client = Albert(auth_manager=creds)
```

Or explicitly:

```python
from pydantic import SecretStr

creds = AlbertClientCredentials(
    id="your-client-id",
    secret=SecretStr("your-client-secret"),
    base_url="https://app.albertinvent.com",
)
client = Albert(auth_manager=creds)
```

Environment variables:

* `ALBERT_CLIENT_ID`
* `ALBERT_CLIENT_SECRET`
* `ALBERT_BASE_URL` (optional; defaults to `https://app.albertinvent.com`

---

#### 🧪 Token-Based Auth (For Testing Only)

You can still use a static token (e.g., copied from browser dev tools or passed via env) for one-off access:

```python
# Static token (direct)
client = Albert(
    base_url="https://app.albertinvent.com",
    token="your.jwt.token"
)

# Or using the helper
client = Albert.from_token(
    base_url="https://app.albertinvent.com",
    token="your.jwt.token"
)
```

!!! warning
    This method does not support auto-refresh and should be avoided for production use.

---

## Working with Resource Collections and Models

### Example: Inventory Collection

You can interact with inventory items using the `InventoryCollection` class. Here is an example of how to create a new inventory item, list all inventory items, and fetch an inventory item by its ID.

```python
from albert import Albert
from albert.resources.inventory import InventoryItem, InventoryCategory, UnitCategory

client = Albert(
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

client = Albert()

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
