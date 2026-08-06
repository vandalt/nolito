from pathlib import Path
from unittest.mock import Mock

import pytest

from nolito.settings import NolitoSettings
from nolito.tokens import TokenSet


@pytest.fixture
def settings(tmp_path: Path) -> NolitoSettings:
    return NolitoSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://127.0.0.1:8765/callback",
        api_base_url="https://api.example.test/api/",
        keyring_service="nolito-tests",
        keyring_username="tokens",
        metadata_file=tmp_path / "tokens.metadata.json",
        request_timeout_seconds=12.5,
    )


@pytest.fixture
def tokens() -> TokenSet:
    return TokenSet(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_at=2_000_000_000,
    )


def response(
    *,
    payload: object = None,
    ok: bool = True,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    text: str = "",
    json_side_effect: Exception | None = None,
) -> Mock:
    result = Mock()
    result.ok = ok
    result.status_code = status_code
    result.headers = headers or {}
    result.text = text
    if json_side_effect is not None:
        result.json.side_effect = json_side_effect
    else:
        result.json.return_value = payload
    return result


@pytest.fixture
def make_response():
    return response
