# Albert Python SDK

The Albert Python SDK provides a comprehensive and easy-to-use interface for interacting with the Albert API. The SDK is designed to simplify the process of working with various resources such as inventories, projects, companies, and tags by providing Resource Collections and Resource Models.

> [!WARNING]
> The Albert SDK is still in the early phases of development. As such, patterns may change, and methods may not work as expected. Do not use this package unless you are comfortable with these limitations.

## Installation

TODO: Add installation instructions from PyPI once published

For developers, please see the CONTRIBUTING.MD for local installation instructions.

## Overview
The SDK is built around two main concepts:

1. *Resource Models*: Represent individual entities like InventoryItem, Project, Company, and Tag. These are all controlled using Pydantic.

2. *Resource Collections*: Provide methods to interact with the API endpoints related to a specific resource, such as listing, creating, updating, and deleting resources.

### Resource Models
Resource Models represent the data structure of individual resources. They encapsulate the attributes and behaviors of a single resource. For example, an `InventoryItem` has attributes like `name`, `description`, `category`, and `tags`.
 page"
 
### Resource Collections
Resource Collections act as managers for Resource Models. They provide methods for performing CRUD operations (Create, Read, Update, Delete) on the resources. For example, the `InventoryCollection` class has methods like create, `get_by_id()`, `list()`, `update()`, and `delete()`. `list()` methods generally accept parameters to narrow the query to use it like a search.