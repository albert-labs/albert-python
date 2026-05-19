# Authentication

Albert Python SDK supports four authentication methods:

* **Single Sign-On (SSO)** via browser-based OAuth2
* **Azure AD SSO Token Exchange** for server-to-server integrations using Azure AD
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

## 🔄 Azure AD SSO Token Exchange

This method is for applications that already authenticate users through **Azure Active Directory**
and want to access the Albert API on their behalf — without any browser interaction. Your
application obtains an Azure AD ID token and the SDK exchanges it for an Albert access token
automatically.

!!! warning "Tenant configuration required"
    This authentication method requires your Azure AD application's `aud` (audience/client ID)
    to be registered with Albert for your tenant. Without this, all requests will return `401 Unauthorized`.
    [Contact Albert support](https://support.albertinvent.com/en/contact-us) to enable this for your organisation.

### Prerequisites

- An Azure AD application registration with the Albert API audience registered by Albert support
- A mechanism in your application to obtain an Azure AD ID token (e.g. MSAL, Azure SDK)

### Usage

Provide a callable that returns a fresh Azure AD ID token on demand. The SDK calls it on the
first request and again whenever the Albert access token needs to be renewed.

```python
from albert import Albert, AlbertSSOTokenExchange
from msal import ConfidentialClientApplication

app = ConfidentialClientApplication(
    client_id="your-azure-app-id",
    client_credential="your-azure-client-secret",
    authority="https://login.microsoftonline.com/your-tenant-id",
)

def get_azure_token() -> str:
    result = app.acquire_token_for_client(scopes=["api://your-albert-audience/.default"])
    return result["id_token"]

client = Albert.from_sso_exchange(
    base_url="https://mycompany.albertinvent.com",
    subdomain="mycompany",
    oidc_token_provider=get_azure_token,
)
```

Or wire it up manually:

```python
auth = AlbertSSOTokenExchange(
    base_url="https://mycompany.albertinvent.com",
    subdomain="mycompany",
    oidc_token_provider=get_azure_token,
)
client = Albert(auth_manager=auth)
```

!!! warning "Use a callable, not a static token string"
    Passing `lambda: "my-static-token"` works only while that Azure AD token remains valid
    (typically 60–90 minutes). Once it expires and the Albert access token needs renewal,
    the exchange will fail. Always pass a callable that fetches a fresh token from Azure AD.

!!! warning "Token validity is your responsibility"
    The SDK passes the token returned by `oidc_token_provider` directly to Albert. If your
    callable returns an expired or invalid Azure AD token, the exchange will fail with
    `401 Unauthorized`. Ensure your token acquisition logic handles Azure AD token refresh.

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
