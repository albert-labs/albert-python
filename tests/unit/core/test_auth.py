import pytest
from pydantic import SecretStr

from albert import Albert, AlbertClientCredentials
from albert.core.session import DEFAULT_TIMEOUT


def test_from_env_requires_all_env_vars(monkeypatch):
    monkeypatch.setenv("ALBERT_CLIENT_ID", "id")
    monkeypatch.setenv("ALBERT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ALBERT_BASE_URL", "https://test.albertinvent.com")
    creds = AlbertClientCredentials.from_env()
    assert creds is not None
    assert creds.base_url == "https://test.albertinvent.com"

    monkeypatch.delenv("ALBERT_BASE_URL", raising=False)
    assert AlbertClientCredentials.from_env() is None


def test_client_uses_auth_manager_base_url():
    creds = AlbertClientCredentials(
        id="id",
        secret=SecretStr("xyz"),
        base_url="https://auth.albertinvent.com",
    )
    client = Albert(auth_manager=creds)
    assert client.session.base_url == "https://auth.albertinvent.com"


def test_client_base_url_mismatch_raises_error():
    creds = AlbertClientCredentials(
        id="id",
        secret=SecretStr("xyz"),
        base_url="https://foo.albertinvent.com",
    )
    with pytest.raises(ValueError):
        Albert(base_url="https://bar.albertinvent.com", auth_manager=creds)


def test_client_uses_env_base_url(monkeypatch):
    monkeypatch.setenv("ALBERT_BASE_URL", "https://test.albertinvent.com")
    client = Albert(token="t")
    assert client.session.base_url == "https://test.albertinvent.com"


def test_client_applies_default_timeout():
    """Test that the default timeout applies through the Albert client."""
    client = Albert(base_url="https://test.albertinvent.com", token="t")
    assert client.session._timeout == DEFAULT_TIMEOUT


def test_client_timeout_none_disables_timeout():
    """Test that passing timeout=None explicitly leaves client calls without a timeout."""
    client = Albert(base_url="https://test.albertinvent.com", token="t", timeout=None)
    assert client.session._timeout is None
