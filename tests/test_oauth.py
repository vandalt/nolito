from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from nolito.errors import OAuthFlowError
from nolito.oauth import (
    OAuthManager,
    _capture_code_from_local_callback,
    _read_json_or_raise,
)
from nolito.tokens import TokenSet


@pytest.fixture
def manager(settings):
    return OAuthManager(settings, Mock(), session=Mock())


def test_load_or_authorize_uses_saved_unexpired_tokens(manager, tokens):
    manager._token_store.load.return_value = tokens
    with (
        patch.object(TokenSet, "is_expired", return_value=False),
        patch.object(manager, "authorize_with_local_callback") as authorize,
    ):
        assert manager.load_or_authorize() is tokens
    authorize.assert_not_called()


def test_load_or_authorize_authorizes_missing_tokens(manager, tokens):
    manager._token_store.load.return_value = None
    manager.authorize_with_local_callback = Mock(return_value=tokens)
    assert manager.load_or_authorize() is tokens
    manager.authorize_with_local_callback.assert_called_once_with()


def test_load_or_authorize_refreshes_expired_tokens(manager, tokens):
    manager._token_store.load.return_value = tokens
    manager.refresh = Mock(return_value=tokens)
    with patch.object(TokenSet, "is_expired", return_value=True):
        assert manager.load_or_authorize() is tokens
    manager.refresh.assert_called_once_with(tokens.refresh_token)


@pytest.mark.parametrize(
    ("method", "argument", "expected_data"),
    [
        (
            "refresh",
            "old-refresh",
            {"grant_type": "refresh_token", "refresh_token": "old-refresh"},
        ),
        (
            "exchange_code",
            "code",
            {
                "grant_type": "authorization_code",
                "code": "code",
                "redirect_uri": "http://127.0.0.1:8765/callback",
            },
        ),
    ],
)
def test_token_exchange_posts_and_persists(
    manager, settings, method, argument, expected_data, make_response
):
    manager._session.post.return_value = make_response(
        payload={
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        }
    )
    with patch("nolito.tokens.time.time", return_value=100):
        result = getattr(manager, method)(argument)

    assert result == TokenSet("access", "refresh", 3700)
    manager._session.post.assert_called_once_with(
        "https://api.example.test/api/token/",
        data=expected_data,
        auth=(settings.client_id, settings.client_secret),
        timeout=settings.request_timeout_seconds,
    )
    manager._token_store.save.assert_called_once_with(result)


def test_refresh_reauthorizes_after_invalid_grant(manager, make_response, tokens):
    manager._session.post.return_value = make_response(
        ok=False,
        status_code=400,
        payload={"error": "invalid_grant"},
    )
    manager.authorize_with_local_callback = Mock(return_value=tokens)

    assert manager.refresh("consumed-refresh-token") is tokens
    manager._token_store.clear.assert_called_once_with()
    manager.authorize_with_local_callback.assert_called_once_with()
    manager._token_store.save.assert_not_called()


def test_authorization_url_encodes_params(manager):
    url = manager.authorization_url("state value")
    assert url.startswith("https://api.example.test/api/authorize/?")
    assert "client_id=client-id" in url
    assert "state=state+value" in url


@pytest.mark.parametrize(
    ("headers", "payload", "text", "json_error", "message"),
    [
        (
            {"content-type": "application/json"},
            {"detail": "denied"},
            "fallback",
            None,
            "403 denied",
        ),
        ({}, None, "denied", None, "403 denied"),
        (
            {"content-type": "application/json"},
            None,
            "invalid",
            ValueError(),
            "403 invalid",
        ),
    ],
)
def test_read_json_or_raise_formats_failure(
    make_response, headers, payload, text, json_error, message
):
    response = make_response(
        ok=False,
        status_code=403,
        headers=headers,
        payload=payload,
        text=text,
        json_side_effect=json_error,
    )
    with pytest.raises(OAuthFlowError, match=message):
        _read_json_or_raise(response, context="refresh token")


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "https://127.0.0.1:8765/callback",
        "http://example.test:8765/callback",
        "http://127.0.0.1/callback",
    ],
)
def test_local_callback_rejects_unsafe_redirect_uris(redirect_uri):
    with pytest.raises(OAuthFlowError):
        _capture_code_from_local_callback(
            redirect_uri=redirect_uri,
            authorize_url="https://authorize.example.test/",
            expected_state="state",
            timeout_seconds=1,
        )


def test_local_callback_returns_valid_code_without_real_server():
    class FakeServer:
        def __init__(self, address, handler):
            self.handler = handler
            self.timeout = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def handle_request(self):
            request = object.__new__(self.handler)
            request.path = "/callback?code=the-code&state=expected"
            request.wfile = BytesIO()
            request.send_response = Mock()
            request.send_header = Mock()
            request.end_headers = Mock()
            request.do_GET()

    with (
        patch("nolito.oauth.HTTPServer", FakeServer),
        patch("nolito.oauth.webbrowser.open", return_value=True),
        patch("nolito.oauth.time.time", side_effect=[0, 0, 0]),
    ):
        assert (
            _capture_code_from_local_callback(
                redirect_uri="http://127.0.0.1:8765/callback",
                authorize_url="https://authorize.example.test/",
                expected_state="expected",
                timeout_seconds=1,
            )
            == "the-code"
        )


def test_local_callback_times_out_without_request():
    class IdleServer:
        def __init__(self, *args):
            self.timeout = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def handle_request(self):
            pass

    with (
        patch("nolito.oauth.HTTPServer", IdleServer),
        patch("nolito.oauth.webbrowser.open", return_value=False),
        patch("nolito.oauth.time.time", side_effect=[0, 2]),
        pytest.raises(OAuthFlowError, match="timed out"),
    ):
        _capture_code_from_local_callback(
            redirect_uri="http://localhost:8765/callback",
            authorize_url="https://authorize.example.test/",
            expected_state="expected",
            timeout_seconds=1,
        )
