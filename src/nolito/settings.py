"""Runtime settings for Nolito."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NolitoSettings:
    """Configuration loaded from environment variables."""

    client_id: str
    client_secret: str
    redirect_uri: str
    api_base_url: str
    keyring_service: str
    keyring_username: str
    metadata_file: Path
    request_timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "NolitoSettings":
        client_id = _required_env("NOLIO_CLIENT_ID")
        client_secret = _required_env("NOLIO_CLIENT_SECRET")
        redirect_uri = os.getenv("NOLIO_REDIRECT_URI", "http://127.0.0.1:8765/callback")
        api_base_url = _normalized_api_base_url(
            os.getenv("NOLIO_API_BASE_URL", "https://www.nolio.io/api/")
        )
        keyring_service = os.getenv("NOLITO_KEYRING_SERVICE", "nolito")
        keyring_username = os.getenv("NOLITO_KEYRING_USERNAME", "oauth_tokens")
        metadata_file = _default_metadata_file()

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            api_base_url=api_base_url,
            keyring_service=keyring_service,
            keyring_username=keyring_username,
            metadata_file=metadata_file,
        )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


def _normalized_api_base_url(value: str) -> str:
    return value.rstrip("/") + "/"


def _default_metadata_file() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")
    if config_home:
        base = Path(config_home)
    else:
        base = Path.home() / ".config"
    return base / "nolito" / "tokens.metadata.json"
