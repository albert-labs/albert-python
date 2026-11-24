# Installation

Installation is as simple as:

=== "pip"

    ```bash
    pip install albert
    ```

=== "uv"

    ```bash
    uv add albert
    ```

---

## Dependencies

Albert has a few dependencies:

- [pydantic](https://pypi.org/project/pydantic/) — For model validation
- [pandas](https://pypi.org/project/pandas/) — For Data frames

If you’re on Python 3.10+ and already have **pip** or **uv** set up, you’re ready to go!

!!! warning "Python 3.10 deprecation"
    Python 3.10 reached end of life in October 2026. The SDK deprecation was announced on **2026-11-24**, and Python 3.10 will remain supported through **2027-02-28**, three months after the announcement. The first minor SDK release after that date will require Python 3.11 or later.

## Install from repository

And if you prefer to install albert directly from the repository:

=== "pip"

    ```bash
    pip install 'git+https://github.com/albert-labs/albert-python@main'
    ```

=== "uv"

    ```bash
    uv add 'git+https://github.com/albert-labs/albert-python@main'
    ```
