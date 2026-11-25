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

---

## Optional extras

### PAC proxy support

If your network routes traffic through a PAC (Proxy Auto-Configuration) file, install the SDK with the `pac` extra:

=== "pip"

    ```bash
    pip install "albert[pac]"
    ```

=== "uv"

    ```bash
    uv add "albert[pac]"
    ```

Then pass `pac_url` when constructing the client. See [Session](core/session.md#pac-proxy-auto-configuration) for usage.

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
