# Authentication

Albert Python SDK supports three authentication methods:

* **Single Sign-On (SSO)** via browser-based OAuth2
* **Client Credentials** using a client ID and secret
* **Static Token** using a pre-generated token (via the `ALBERT_TOKEN` environment variable)

These modes are supported via the `auth_manager` or `token` argument to the `Albert` client.

!!! warning
    Static token-based authentication is suitable for temporary or testing purposes and does not support token refresh.

---

## 🔐 SSO (Browser-Based Login)

This is the recommended method for users authenticating interactively. It opens a browser window to authenticate using your email address and automatically manages tokens.

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

!!! warning
    You **must call** `.authenticate()` before passing this client to `Albert(auth_manager=...)`
    to ensure the token is acquired and ready for use.

Alternatively, you can use the helper constructor:

```python
client = Albert.from_sso(
    base_url="https://app.albertinvent.com",
    email="your-name@albertinvent.com"
)
```

---

## 🔑 Client Credentials (Programmatic Access)

This method implements the OAuth2 Client Credentials flow and is suitable for non-interactive usage, like backend services or automation scripts. It manages token acquisition and refresh automatically via the `AlbertClientCredentials` class.

This method is ideal for server-to-server or CI/CD scenarios. You can authenticate using a client ID and secret, and the SDK will manage token fetching and refresh automatically.

```python
from pydantic import SecretStr

creds = AlbertClientCredentials(
    id="your-client-id",
    secret=SecretStr("your-client-secret"),
    base_url="https://app.albertinvent.com",
)
client = Albert(auth_manager=creds)
```

Or you can use the helper constructor:

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

Environment variables:

* `ALBERT_CLIENT_ID`
* `ALBERT_CLIENT_SECRET`
* `ALBERT_BASE_URL` (optional; defaults to `https://app.albertinvent.com`

---

## 🧪 Token-Based Auth (For Testing Only)

You can also use a static token (e.g., copied from browser dev tools or passed via env) for one-off access:

```python
client = Albert(
    base_url="https://app.albertinvent.com",
    token="your.jwt.token"
)
```

Or using the helper

```python

client = Albert.from_token(
    base_url="https://app.albertinvent.com",
    token="your.jwt.token"
)
```

!!! warning
    This method does not support auto-refresh and should be avoided for production use.

---
