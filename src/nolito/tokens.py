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
    """Set of tokens used by the API

    :param access_token: The access token
    :param refresh_token: The refresh token
    :param expires_at: The expiration time
    :param token_type: The token type (defaults to ``"Bearer"``
    :param scope: The token scope (defaults to ``None``)
    """

    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str = "Bearer"
    scope: str | None = None

    @classmethod
    def from_oauth_payload(
        cls, payload: dict[str, Any], now: int | None = None
    ) -> TokenSet:
        """Extract the token set from an OAuth paylot

        :param payload: The oauth payload as returned by a ``POST``
                        request to the ``token/`` endpoint.
        :param now: Current time in seconds (defaults ``time.time()`` when ``None``).
        :raises RuntimeError: Raised if no ``expires_in`` key is found``
        """
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
        """Check if the token is expired or expires soon

        :param leeway_seconds: How soon is the token allowed to expire (in sec)
        :return: True if the token is expired, False otherwise.
        """
        return int(time.time()) >= self.expires_at - leeway_seconds


class KeyringTokenStore:
    """Create a token store using the Keyring

    :param service: The name of the keyring service
    :param username: The username for the keyring service
    :param metadata_file: The path to the metadata file
    """

    def __init__(self, *, service: str, username: str, metadata_file: Path):
        self._service = service
        self._username = username
        self._metadata_file = metadata_file
        self._lock = threading.Lock()

    @classmethod
    def from_settings(cls, settings: NolitoSettings) -> KeyringTokenStore:
        """Create the token store based on Nolito settings

        :param settings: The Nolito settings
        """
        return cls(
            service=settings.keyring_service,
            username=settings.keyring_username,
            metadata_file=settings.metadata_file,
        )

    def load(self) -> TokenSet | None:
        """Load a token set keyring secrets and metadata

        :return: The token set based on the current store
        """
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
        """Save the tokens to the keyring and metadata

        :param tokens: The token set to store
        """
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

            keyring.set_password(
                self._service, self._username, json.dumps(secrets_payload)
            )
            self._write_metadata(metadata_payload)

    def clear(self) -> None:
        """Clear the information stored in the keyring or the datadata file"""
        with self._lock:
            try:
                keyring.delete_password(self._service, self._username)
            except keyring.errors.PasswordDeleteError:
                pass
            if self._metadata_file.exists():
                self._metadata_file.unlink()

    def _read_metadata(self) -> dict[str, Any] | None:
        """Read the metadata file

        :return: The JSON data if the file exists, ``None`` otherwise.
        """
        if not self._metadata_file.exists():
            return None
        return json.loads(self._metadata_file.read_text(encoding="utf-8"))

    def _write_metadata(self, payload: dict[str, Any]) -> None:
        """Write the metadata file

        :param payload: Dictionary with the desired metadata keys
        """
        self._metadata_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self._metadata_file.with_suffix(self._metadata_file.suffix + ".tmp")
        tmp_file.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        os.replace(tmp_file, self._metadata_file)


def _required_string(payload: dict[str, Any], key: str) -> str:
    """Get a required string value from the payload dict

    :param payload: Payload dictionary
    :param key: The payload key to look for
    :raises RuntimeError: Raised if the key is missing or if the value is not a string
    :return: The value extracted from ``payload``
    """
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    raise RuntimeError(f"Missing required OAuth field: {key}")
