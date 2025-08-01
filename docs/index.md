# Albert Python

<div class="logo-wrapper">
  <img src="assets/Wordmark_White.png" class="logo only-dark" alt="Albert Logo">
  <img src="assets/Wordmark_Black.png" class="logo only-light" alt="Albert Logo">
</div>

[![CI](https://img.shields.io/circleci/build/github/albert-labs/albert-python/main?label=CI)](https://app.circleci.com/pipelines/github/albert-labs/albert-python?branch=main)
[![pypi](https://img.shields.io/pypi/v/albert.svg)](https://pypi.python.org/pypi/albert)
[![downloads](https://img.shields.io/pypi/dm/albert.svg)](https://pypi.org/project/albert/)<br>
[![license](https://img.shields.io/github/license/albert-labs/albert-python.svg)](https://github.com/albert-labs/albert-python/blob/main/LICENSE)

## Overview

Albert Python is the official Albert Invent Software Development Kit (SDK) for Python
that provides a comprehensive and easy-to-use interface for interacting with the Albert Platform.
The SDK allows Python developers to write software that interacts with various platform resources,
such as inventories, projects, companies, tags, and many more.

It provides:

- **Typed Resource Models** via Pydantic for entities like `Project`, `InventoryItem`, `Company`, and more.
- **Resource Collections** with CRUD and search methods for each model (e.g., `client.projects`, `client.inventory`).
- **Multiple Authentication** options: static token, OAuth2 client credentials, or browser-based SSO.
- **Automatic Pagination** and configurable logging.

## Quick Start

Install the package:

```bash
pip install albert
```

Get all projects:

```python
from albert import Albert

# Initialize with a static JWT token
client = Albert.from_token(
    base_url="https://app.albertinvent.com",
    token="YOUR_JWT_TOKEN"
)

for project in client.projects.get_all(max_items=10):
    print(project.name)
```

## Next Steps

- Learn core concepts: see [Concepts](concepts.md)
- Explore Authentication methods: see [Authentication](authentication.md)
- Explore detailed references: see [Albert](albert.md)
