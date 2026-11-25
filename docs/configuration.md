# Configuration

This page describes all environment variables supported by the Albert Python SDK for customizing runtime behavior.

---

## ALBERT_LOG_LEVEL

Sets the log level for SDK output.

- Default: `WARNING`
- Supported values (case-insensitive):
    - `DEBUG`
    - `INFO`
    - `WARNING`
    - `ERROR`
    - `CRITICAL`

If an invalid value is provided, it falls back to `WARNING` and emits a warning.

### Examples

=== "macOS / Linux"

    ```bash
    export ALBERT_LOG_LEVEL=INFO

    ALBERT_LOG_LEVEL=DEBUG python my_script.py
    ```

=== "Windows (CMD)"

    ```cmd
    set ALBERT_LOG_LEVEL=DEBUG

    setx ALBERT_LOG_LEVEL INFO
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:ALBERT_LOG_LEVEL="DEBUG"
    ```

---

## ALBERT_BASE_URL

Overrides the default Albert backend base URL (defaults to `https://app.albertinvent.com`).

```bash
export ALBERT_BASE_URL=https://app.albertinvent.com
```

Used by all client authentication methods.

---

## ALBERT_CLIENT_ID and ALBERT_CLIENT_SECRET

Used for OAuth2 Client Credentials login.

```python
from albert import AlbertClientCredentials

client = Albert(client_credentials=AlbertClientCredentials.from_env())
```

These variables are only needed if you're authenticating using client credentials, not a token or SSO.

```bash
export ALBERT_CLIENT_ID=my-client-id
export ALBERT_CLIENT_SECRET=my-client-secret
```

---

## Proxy configuration

Proxy routing is configured in code when constructing the client, not through an environment variable.

If your network requires a fixed proxy, pass its URLs keyed by scheme:

```python
from albert import Albert

client = Albert(proxies={"https": "http://proxy.company.com:8080"})
```

If your network uses a PAC (Proxy Auto-Configuration) file to decide routing per destination, install the optional `pac` extra (see [Installation](installation.md#optional-extras)) and pass `pac_url`:

```python
client = Albert(pac_url="auto")  # discover from system settings or network auto-discovery
client = Albert(pac_url="https://proxy.company.com/proxy.pac")  # or an explicit PAC file
```

Proxy configuration applies to everything the SDK does, including file uploads. See [Session](core/session.md) for the full reference.

---

## Summary

| Variable               | Purpose                                 | Used By                   |
|------------------------|-----------------------------------------|---------------------------|
| `ALBERT_LOG_LEVEL`     | Controls SDK logging level              | All SDK users             |
| `ALBERT_BASE_URL`      | Overrides the base URL for API requests | All authentication modes  |
| `ALBERT_CLIENT_ID`     | OAuth2 client ID for authentication     | `AlbertClientCredentials` |
| `ALBERT_CLIENT_SECRET` | OAuth2 client secret for authentication | `AlbertClientCredentials` |

These variables are all optional but provide convenience for automation, CI pipelines, and local testing.
