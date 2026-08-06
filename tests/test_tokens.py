import json
from unittest.mock import patch

import pytest

from nolito.tokens import KeyringTokenStore, TokenSet


def test_token_set_from_payload_calculates_expiration_and_optional_fields():
    result = TokenSet.from_oauth_payload(
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": "3600",
            "token_type": "Custom",
            "scope": "read write",
        },
        now=100,
    )
    assert result == TokenSet("access", "refresh", 3700, "Custom", "read write")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"access_token": "", "refresh_token": "refresh", "expires_in": 1},
        {"access_token": "access", "refresh_token": "", "expires_in": 1},
        {"access_token": "access", "refresh_token": "refresh", "expires_in": 0},
    ],
)
def test_token_set_rejects_invalid_oauth_payload(payload):
    with pytest.raises(RuntimeError):
        TokenSet.from_oauth_payload(payload, now=100)


@pytest.mark.parametrize(
    ("now", "leeway", "expected"), [(939, 60, False), (940, 60, True), (1_000, 0, True)]
)
def test_token_set_expiration_honors_leeway(now, leeway, expected):
    with patch("nolito.tokens.time.time", return_value=now):
        assert TokenSet("access", "refresh", 1_000).is_expired(leeway) is expected


def test_token_store_from_settings(settings):
    assert (
        KeyringTokenStore.from_settings(settings)._metadata_file
        == settings.metadata_file
    )


def test_token_store_returns_none_when_secret_or_metadata_is_missing(settings):
    store = KeyringTokenStore.from_settings(settings)
    with patch("nolito.tokens.keyring.get_password", return_value=None):
        assert store.load() is None

    with patch(
        "nolito.tokens.keyring.get_password", return_value='{"access_token": "a"}'
    ):
        assert store.load() is None


def test_token_store_saves_and_loads_tokens(settings, tokens):
    store = KeyringTokenStore.from_settings(settings)
    with (
        patch("nolito.tokens.keyring.set_password") as set_password,
        patch("nolito.tokens.keyring.get_password", return_value=None),
        patch("nolito.tokens.time.time", return_value=1234),
    ):
        store.save(tokens)
        secret_json = set_password.call_args.args[2]
        assert json.loads(secret_json) == {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
        }
        assert json.loads(settings.metadata_file.read_text()) == {
            "expires_at": tokens.expires_at,
            "scope": None,
            "token_type": "Bearer",
            "updated_at": 1234,
        }

    with patch("nolito.tokens.keyring.get_password", return_value=secret_json):
        assert store.load() == tokens


def test_token_store_load_rejects_incomplete_saved_secret(settings):
    store = KeyringTokenStore.from_settings(settings)
    settings.metadata_file.write_text('{"expires_at": 100}', encoding="utf-8")
    with (
        patch(
            "nolito.tokens.keyring.get_password", return_value='{"access_token": "a"}'
        ),
        pytest.raises(RuntimeError, match="refresh_token"),
    ):
        store.load()


def test_token_store_clear_removes_secret_and_metadata(settings):
    store = KeyringTokenStore.from_settings(settings)
    settings.metadata_file.write_text("{}", encoding="utf-8")
    with patch("nolito.tokens.keyring.delete_password") as delete:
        store.clear()
    delete.assert_called_once_with(settings.keyring_service, settings.keyring_username)
    assert not settings.metadata_file.exists()


def test_token_store_clear_ignores_absent_keyring_secret(settings):
    import keyring.errors

    store = KeyringTokenStore.from_settings(settings)
    with patch(
        "nolito.tokens.keyring.delete_password",
        side_effect=keyring.errors.PasswordDeleteError("missing"),
    ):
        store.clear()
