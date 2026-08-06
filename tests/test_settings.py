from pathlib import Path

import pytest

from nolito.settings import NolitoSettings, _normalized_api_base_url, _required_env


@pytest.mark.parametrize("value", [None, ""])
def test_required_env_rejects_missing_or_empty_values(monkeypatch, value):
    monkeypatch.delenv("TEST_REQUIRED", raising=False)
    if value is not None:
        monkeypatch.setenv("TEST_REQUIRED", value)
    with pytest.raises(RuntimeError, match="TEST_REQUIRED"):
        _required_env("TEST_REQUIRED")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://example.test/api", "https://example.test/api/"),
        ("https://example.test/api///", "https://example.test/api/"),
    ],
)
def test_normalized_api_base_url(value, expected):
    assert _normalized_api_base_url(value) == expected


def test_settings_from_env_uses_defaults_and_home_config(monkeypatch, tmp_path):
    monkeypatch.setenv("NOLIO_CLIENT_ID", "id")
    monkeypatch.setenv("NOLIO_CLIENT_SECRET", "secret")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for name in (
        "NOLIO_REDIRECT_URI",
        "NOLIO_API_BASE_URL",
        "NOLITO_KEYRING_SERVICE",
        "NOLITO_KEYRING_USERNAME",
        "XDG_CONFIG_HOME",
    ):
        monkeypatch.delenv(name, raising=False)

    result = NolitoSettings.from_env()

    assert result.redirect_uri == "http://127.0.0.1:8765/callback"
    assert result.api_base_url == "https://www.nolio.io/api/"
    assert result.metadata_file == tmp_path / ".config/nolito/tokens.metadata.json"


def test_settings_from_env_honors_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("NOLIO_CLIENT_ID", "id")
    monkeypatch.setenv("NOLIO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("NOLIO_REDIRECT_URI", "https://client.example.test/callback")
    monkeypatch.setenv("NOLIO_API_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("NOLITO_KEYRING_SERVICE", "service")
    monkeypatch.setenv("NOLITO_KEYRING_USERNAME", "user")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = NolitoSettings.from_env()

    assert (result.redirect_uri, result.api_base_url) == (
        "https://client.example.test/callback",
        "https://api.example.test/",
    )
    assert (result.keyring_service, result.keyring_username) == ("service", "user")
    assert result.metadata_file == tmp_path / "nolito/tokens.metadata.json"
