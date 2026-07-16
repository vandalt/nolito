"""Token model and secure persistence."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import keyring

from .settings import NolitoSettings


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str = "Bearer"
    scope: str | None = None

    @classmethod
    def from_oauth_payload(cls, payload: dict[str, Any], now: int | None = None) -> "TokenSet":
        access_token = _required_string(payload, "access_token")
        refresh_token = _required_string(payload, "refresh_token")
        expires_in = int(payload.get("expires_in", 0))
        if expires_in <= 0:
            raise RuntimeError("OAuth response is missing a valid expires_in value.")
        current = int(time.time()) if now is None else now
        expires_at = current + expires_in
        token_type = str(payload.get("token_type", "Bearer"))
        scope = payload.get("scope")
        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            token_type=token_type,
            scope=None if scope is None else str(scope),
        )

    def is_expired(self, leeway_seconds: int = 60) -> bool:
        return int(time.time()) >= self.expires_at - leeway_seconds


class KeyringTokenStore:
    """Persists OAuth secrets in keyring and metadata in JSON file."""

    def __init__(self, *, service: str, username: str, metadata_file: Path):
        self._service = service
        self._username = username
        self._metadata_file = metadata_file
        self._lock = threading.Lock()

    @classmethod
    def from_settings(cls, settings: NolitoSettings) -> "KeyringTokenStore":
        return cls(
            service=settings.keyring_service,
            username=settings.keyring_username,
            metadata_file=settings.metadata_file,
        )

    def load(self) -> TokenSet | None:
        with self._lock:
            secret_json = keyring.get_password(self._service, self._username)
            if not secret_json:
                return None
            metadata = self._read_metadata()
            if metadata is None:
                return None

            secrets = json.loads(secret_json)
            return TokenSet(
                access_token=_required_string(secrets, "access_token"),
                refresh_token=_required_string(secrets, "refresh_token"),
                expires_at=int(metadata["expires_at"]),
                token_type=str(metadata.get("token_type", "Bearer")),
                scope=None if metadata.get("scope") is None else str(metadata["scope"]),
            )

    def save(self, tokens: TokenSet) -> None:
        with self._lock:
            secrets_payload = {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
            }
            metadata_payload = {
                "expires_at": tokens.expires_at,
                "token_type": tokens.token_type,
                "scope": tokens.scope,
                "updated_at": int(time.time()),
            }

            keyring.set_password(self._service, self._username, json.dumps(secrets_payload))
            self._write_metadata(metadata_payload)

    def clear(self) -> None:
        with self._lock:
            try:
                keyring.delete_password(self._service, self._username)
            except keyring.errors.PasswordDeleteError:
                pass
            if self._metadata_file.exists():
                self._metadata_file.unlink()

    def _read_metadata(self) -> dict[str, Any] | None:
        if not self._metadata_file.exists():
            return None
        return json.loads(self._metadata_file.read_text(encoding="utf-8"))

    def _write_metadata(self, payload: dict[str, Any]) -> None:
        self._metadata_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self._metadata_file.with_suffix(self._metadata_file.suffix + ".tmp")
        tmp_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp_file, self._metadata_file)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    raise RuntimeError(f"Missing required OAuth field: {key}")
