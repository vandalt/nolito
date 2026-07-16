"""OAuth flow and token lifecycle management."""

from __future__ import annotations

import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests

from .errors import OAuthFlowError
from .settings import NolitoSettings
from .tokens import KeyringTokenStore, TokenSet


class OAuthManager:
    """Handles authorization code flow and refresh token rotation."""

    def __init__(
        self,
        settings: NolitoSettings,
        token_store: KeyringTokenStore,
        session: requests.Session | None = None,
    ):
        self._settings = settings
        self._token_store = token_store
        self._session = session or requests.Session()

    def load_or_authorize(self) -> TokenSet:
        tokens = self._token_store.load()
        if tokens is None:
            tokens = self.authorize_with_local_callback()
        if tokens.is_expired():
            tokens = self.refresh(tokens.refresh_token)
        return tokens

    def refresh(self, refresh_token: str) -> TokenSet:
        response = self._session.post(
            self._endpoint_url("token/"),
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(self._settings.client_id, self._settings.client_secret),
            timeout=self._settings.request_timeout_seconds,
        )
        payload = _read_json_or_raise(response, context="refresh token")
        tokens = TokenSet.from_oauth_payload(payload)
        self._token_store.save(tokens)
        return tokens

    def exchange_code(self, code: str) -> TokenSet:
        response = self._session.post(
            self._endpoint_url("token/"),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._settings.redirect_uri,
            },
            auth=(self._settings.client_id, self._settings.client_secret),
            timeout=self._settings.request_timeout_seconds,
        )
        payload = _read_json_or_raise(response, context="authorization code exchange")
        tokens = TokenSet.from_oauth_payload(payload)
        self._token_store.save(tokens)
        return tokens

    def authorize_with_local_callback(self, timeout_seconds: int = 180) -> TokenSet:
        state = secrets.token_urlsafe(32)
        authorize_url = self.authorization_url(state)
        code = _capture_code_from_local_callback(
            redirect_uri=self._settings.redirect_uri,
            authorize_url=authorize_url,
            expected_state=state,
            timeout_seconds=timeout_seconds,
        )
        return self.exchange_code(code)

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._settings.client_id,
            "response_type": "code",
            "redirect_uri": self._settings.redirect_uri,
            "state": state,
        }
        return f"{self._endpoint_url('authorize/')}?{urlencode(params)}"

    def _endpoint_url(self, path: str) -> str:
        return urljoin(self._settings.api_base_url, path)


def _capture_code_from_local_callback(
    *,
    redirect_uri: str,
    authorize_url: str,
    expected_state: str,
    timeout_seconds: int,
) -> str:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http":
        raise OAuthFlowError("Local callback flow requires an http:// redirect_uri.")
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise OAuthFlowError(
            "Local callback flow requires redirect_uri host to be localhost or 127.0.0.1."
        )
    if parsed.port is None:
        raise OAuthFlowError("redirect_uri must include an explicit localhost port.")

    callback_path = parsed.path or "/"
    callback_payload: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request_uri = urlparse(self.path)
            if request_uri.path != callback_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            query = parse_qs(request_uri.query)
            callback_payload["code"] = query.get("code", [""])[0]
            callback_payload["state"] = query.get("state", [""])[0]
            callback_payload["error"] = query.get("error", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OAuth completed. You can close this tab.")

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    with HTTPServer((parsed.hostname, parsed.port), CallbackHandler) as httpd:
        httpd.timeout = 0.5
        opened = webbrowser.open(authorize_url)
        if not opened:
            print("Open this URL in your browser to continue OAuth:")
            print(authorize_url)

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if callback_payload:
                break
            httpd.handle_request()

    if not callback_payload:
        raise OAuthFlowError("OAuth callback timed out.")
    if callback_payload.get("error"):
        raise OAuthFlowError(f"OAuth provider returned an error: {callback_payload['error']}")
    if callback_payload.get("state") != expected_state:
        raise OAuthFlowError("Invalid OAuth state received at callback.")

    code = callback_payload.get("code", "")
    if not code:
        raise OAuthFlowError("OAuth callback did not include an authorization code.")
    return code


def _read_json_or_raise(response: requests.Response, *, context: str) -> dict[str, Any]:
    if response.ok:
        return response.json()

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
    else:
        detail = response.text

    raise OAuthFlowError(f"Failed to {context}: {response.status_code} {detail}")
