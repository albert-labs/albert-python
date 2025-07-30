# Migration Guide: Alpha → v1.0.0

Albert `v1.0.0` introduces a number of changes to the API, including some breaking changes.
This guide provides details highlighting the most important changes to help you migrate your code.

If you run into any issues, please open a [GitHub issue](https://github.com/albert-labs/albert-python/issues) and use the `bug v1` label. This helps us track problems more efficiently and keep improving the library.

## Changes to Authentication

### Unified AuthManager system

**What changed:**

* Introduced three built-in auth managers and helper constructors:

  * **SSO** via a new `AlbertSSOClient` and `Albert.from_sso(...)` (new in v1.0.0)
  * **Client Credentials** via `AlbertClientCredentials` and `Albert.from_client_credentials(...)`
  * **Static Token** via `token` parameter, `ALBERT_TOKEN` env var, or `Albert.from_token(...)`

* Deprecated the `client_credentials` and `token` parameters in `Albert(..)`, replaced by the `auth_manager` parameter.

**How to migrate:**

1. **SSO (browser-based login) — new feature**

    ```python
    from albert import Albert

    # v1.0.0 SSO helper opens a browser for authentication
    client = Albert.from_sso(
        email="yourname@albertinvent.com",
        base_url="https://app.albertinvent.com"
    )
    ```

2. **Client Credentials (service-to-service)**

    ```python
    from albert import Albert, AlbertClientCredentials

    # alpha: passed in client_credentials param
    # client = Albert(client_credentials=ClientCredentials(...))

    # v1.0.0: use from_client_credentials helper
    client = Albert.from_client_credentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        base_url="https://app.albertinvent.com"
    )
    ```

3. **Static Token (environment or direct)**

    ```python
    from albert import Albert

    # alpha: passed token=... directly to constructor
    # client = Albert(token="MY_STATIC_TOKEN")

    # v1.0.0: use from_token helper or still pass token
    client = Albert.from_token(
        base_url="https://app.albertinvent.com",
        token="MY_STATIC_TOKEN"
    )
    ```

*For advanced scenarios, you can still construct an auth manager manually and pass it to* `Albert(auth_manager=...)`.

For complete details, see the [Authentication Guide](./authentication.md).

---

## Changes to Collections

### Behavior change to `create()` and new `get_or_create()`

**What changed:**

* `create()` no longer checks for existing entities and will raise an error if the entity already exists.
* A new method `get_or_create(...)` has been introduced to support idempotent creation behavior.

**How to migrate:**

```diff
- location = client.locations.create(location=new_location)
+ location = client.locations.get_or_create(location=new_location)
```

Use `create()` only when you are confident the entity does not already exist.

### TagsCollection: `get_by_tag()` renamed to `get_by_name()`

**What changed:**

* Renamed `tags.get_by_tag(tag=...)` to `tags.get_by_name(name=...)` for clearer semantics and naming consistency.

**How to migrate:**

```diff
- tag = client.tags.get_by_tag(tag="sustainability")
+ tag = client.tags.get_by_name(name="sustainability")
```

### NotesCollection: `list()` replaced with `get_by_parent_id()`

**What changed:**

* The `list()` method has been removed from `NotesCollection`.
* Use `get_by_parent_id(parent_id=...)` to retrieve notes for a specific parent object.

**How to migrate:**

```diff
- results = list(client.notes.list(parent_id=parent_id))
+ results = list(client.notes.get_by_parent_id(parent_id=parent_id))
```

### Standardized `exists()` method across collections

**What changed:**

* Renamed all `collection.collection_exists()` methods to `collection.exists()` for consistency.
* For example, `tags.tags_exists()` is now `tags.exists()`.

**How to migrate:**

```diff
- company_exists = client.companies.company_exists(name="ACME", exact_match=True)
+ company_exists = client.companies.exists(name="ACME", exact_match=True)
```

### Deprecation of `list()` methods

**What changed:**

* Deprecated all `list()` methods across collections in favor of two new patterns:
  * `get_all()` returns **detailed** (hydrated) resource entities.
  * `search()` returns **partial** (unhydrated) entities optimized for performance.
* Added support for `.hydrate()` on search results to convert partial resources into fully populated ones.

**How to migrate:**

```diff
- project_list = list(client.projects.list())
+ project_list = list(client.projects.get_all(max_items=10))

- project_matches = list(client.projects.list(status="Active"))
+ project_matches = list(client.projects.search(status="Active", max_items=10))
```

**Optional:** Hydrate individual items from `search()` results:

```python
project = list(client.projects.search(max_items=1))[0]
project_full = project.hydrate()
```

---

### Pagination behavior change

**What changed:**

* Added a `max_items` parameter to all `get_all()` and `search()` methods:
  * `max_items` : int, optional
    Maximum number of items to return in total. If `None`, fetches all available items.
* You no longer need to slice iterators or use `itertools.islice` to control result length.

**How to migrate:**

```python
# Fetch up to 10 items, fetching results in pages of 5
projects = list(client.projects.get_all(max_items=10))

# The same applies to search() as well
search_results = list(client.projects.search(status="Active", max_items=20))
```

### BatchDataCollection: `get` renamed to `get_by_id`

**What changed:**

* The `BatchDataCollection.get(id)` method has been renamed to `get_by_id(id)` for clarity and consistency.

**How to migrate:**

```diff
- item = client.batch_data.get(id="123")
+ item = client.batch_data.get_by_id(id="123")
```

---

## Changes to Resources

### Renamed `InventoryInformation` model

**What changed:**

* The `InventoryInformation` model was split into two more specific models:
  * `TaskInventoryInformation`
  * `PropertyDataInventoryInformation`

**How to migrate:**

* Replace all references to `InventoryInformation` with the appropriate specific model.
* Choose `TaskInventoryInformation` for task-based inventory data.
* Choose `PropertyDataInventoryInformation` for property-based inventory data.

---

## Other Changes

### `resource.hydrate()` for partial resource enrichment

**What changed:**

* Added `hydrate()` method to partial resources returned from `search()`.
* This allows upgrading an unhydrated object (e.g., `ProjectSearchItem`) into its full hydrated form (e.g., `Project`) using its `id`.

**How to use:**

```python
# Perform a search (returns partial/unhydrated resources)
project_stub = list(client.projects.search(max_items=1))[0]

# Hydrate it to get full project details
full_project = project_stub.hydrate()

print(full_project.name)
print(full_project.description)
```

**Notes:**

* `hydrate()` requires the resource to have a valid `id` and a bound collection.
* Only collections that implement `get_by_id(id=...)` support hydration.

### Renamed `templates` module to `custom_templates`

**What changed:**

The `templates` module is now `custom_templates`.

**How to use:**

```diff
- client.templates.get_by_id(id="xxx")
+ client.custom_templates.get_by_id(id="xxx")
```
