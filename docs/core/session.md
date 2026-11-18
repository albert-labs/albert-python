# Session

Every `Albert` client communicates through an `AlbertSession`, which owns the transport behavior for everything the SDK does: authentication, retries, timeouts, and proxy routing. This includes file uploads to pre-signed storage URLs, so transport configuration applies uniformly.

Most users never construct a session directly; the `Albert` client builds one and forwards `retries`, `timeout`, `headers`, `proxies`, and `pac_url` to it. Construct an `AlbertSession` yourself only when you need full control, then pass it to `Albert(session=...)`.

::: albert.core.session.AlbertSession
    options:
      show_bases: false

## Proxy configuration

Proxy routing is configured when constructing the client or session. Both options below apply to every call the SDK makes, including file uploads.

### Static proxies

If your network requires a fixed proxy, pass its URLs keyed by scheme:

```python
from albert import Albert

client = Albert(proxies={"https": "http://proxy.company.com:8080"})
```

Environment variables such as `HTTPS_PROXY` are also honored by default, so explicit `proxies` are only needed when the environment is not already configured.

### PAC (Proxy Auto-Configuration)

Some enterprise networks decide routing per destination with a PAC file instead of a single static proxy. PAC support requires the optional `pac` extra (see [Installation](../installation.md#optional-extras)):

```python
from albert import Albert

# Discover the PAC configuration from the operating system proxy settings
# or network auto-discovery (WPAD):
client = Albert(pac_url="auto")

# Or point at a specific PAC file:
client = Albert(pac_url="https://proxy.company.com/proxy.pac")
```

With `pac_url` set, the PAC file's `FindProxyForURL` rules decide the proxy for each call, including a `DIRECT` decision that bypasses any proxy inherited from the environment. A `pac_url` that cannot be found or parsed raises an error at client construction.

When both are provided, the PAC file's per-call decision takes precedence over static `proxies`.

!!! note
    Proxy configuration currently applies to the synchronous `Albert` client. The `AsyncAlbert` client does not support it yet.
