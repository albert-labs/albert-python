# Albert Python SDK

[![PyPI version](https://img.shields.io/pypi/v/albert.svg)](https://pypi.org/project/albert/)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Downloads per month](https://img.shields.io/pypi/dm/albert.svg)](https://pypi.org/project/albert/)

Albert Python is the official Albert Invent Software Development Kit (SDK) for Python
that provides a comprehensive and easy-to-use interface for interacting with the Albert Platform.
The SDK allows Python developers to write software that interacts with various platform resources,
such as inventories, projects, companies, tags, and many more.
You can find the latest, most up-to-date documentation
on the supported resources and usage patterns [here](https://docs.developer.albertinvent.com/albert-python).

## Installation

`pip install albert`

This installs the latest stable release from [PyPI](https://pypi.org/project/albert/).

### Contribution

For developers, please see the [contributing guide](CONTRIBUTING.md), which includes setup instructions, testing, and linting guidelines.

## Quick Start

```python

from albert import Albert

client = Albert.from_client_credentials(
    base_url="https://app.albertinvent.com",
    client_id=YOUR_CLIENT_ID,
    client_secret=YOUR_CLIENT_SECRET
)
projects = client.projects.get_all()

```

## Documentation

[Full Documentation can be found here](https://docs.developer.albertinvent.com/albert-python/latest/)
