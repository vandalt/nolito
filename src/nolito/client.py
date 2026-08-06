"""Nolio API client focused on planned sessions retrieval."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

import requests

from .errors import NolioApiError
from .oauth import OAuthManager
from .settings import NolitoSettings


class NolioApiClient:
    """HTTP client the Nolio API

    :param settings: Settings for this instance of the API.
                        Create with :meth:`NolitoSettings.from_env() <nolito.settings.NolitoSettings.from_env>`
                        if ``None``.
                        Defaults to ``None``.
    :param oauth: OAuthManager to use for the API.
                    Created automatically from settings and system keyring if ``None``.
                    Defaults to ``None``.
    :param session: `requests.Session <https://requests.readthedocs.io/en/latest/api/#requests.Session>`_ object to attach to he client.
                    Plain session is created from scratch if ``None``.
                    Defaults to ``None``.
    """

    def __init__(
        self,
        settings: NolitoSettings | None = None,
        oauth: OAuthManager | None = None,
        session: requests.Session | None = None,
    ):
        self._settings = settings or NolitoSettings.from_env()
        if oauth is None:
            from .tokens import KeyringTokenStore

            token_store = KeyringTokenStore.from_settings(self._settings)
            self._oauth = OAuthManager(settings=self._settings, token_store=token_store)
        else:
            self._oauth = oauth
        self._session = session or requests.Session()

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> list | dict:
        """Send a ``GET`` request to any Nolio API endpoint

        The list of endpoints is available on `the Nolio API wiki
        <https://github.com/NolioApp/NolioAPI-Documentation/wiki/API-Routes>`_.

        :param endpoint: The name of the endpoint (everything that comes after ``get/``.
        :param params: Optional parameters for the request.
        :return: The decoded json response.
        """
        return self._request("GET", f"get/{endpoint}", params=params).json()

    def get_athlete(self) -> dict[str, Any]:
        """Get the user information for the logged-in athlete

        :return: The json dictionary with user information.
        """
        payload = self.get("user/")
        if isinstance(payload, dict):
            return payload
        raise NolioApiError("Unexpected athlete response format.")

    def get_metrics(self) -> dict[str, Any]:
        payload = self.get("user/meta")
        if not isinstance(payload, dict):
            raise NolioApiError("Unexpected athlete metadata response format.")
        return {
            key: {
                **metric,
                "data": max(metric["data"], key=lambda e: e["date"]),
            }
            for key, metric in payload.items()
            if isinstance(metric, dict) and metric.get("data")
        }

    def get_planned_trainings(
        self,
        start: date | str | None = None,
        end: date | str | None = None,
        limit: int | None = None,
    ):
        if start is not None:
            start = start if isinstance(start, str) else start.isoformat()
        if end is not None:
            end = end if isinstance(end, str) else end.isoformat()

        if limit is None and start is not None and end is not None:
            days_delta = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
            limit = days_delta * 2

        params = {
            k: v
            for k, v in {"from": start, "to": end, "limit": limit}.items()
            if v is not None
        }
        return self.get("planned/training/", params=params)

    def get_daily_trainings(
        self, day: date | str | None = None
    ) -> list[dict[str, Any]]:
        local_tz = (
            datetime.now().astimezone().tzinfo
        )  # Set timezone explicitely to avoid confusion
        day = day or datetime.now(local_tz).date()
        day_string = day if isinstance(day, str) else day.isoformat()
        payload = self.get(
            "planned/training/",
            params={"from": day_string, "to": day_string},
        )
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            return payload["results"]
        raise NolioApiError("Unexpected planned-training response format.")

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> requests.Response:
        tokens = self._oauth.load_or_authorize()
        response = self._session.request(
            method=method,
            url=urljoin(self._settings.api_base_url, endpoint),
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            timeout=self._settings.request_timeout_seconds,
        )
        if response.status_code == 401:
            tokens = self._oauth.refresh(tokens.refresh_token)
            response = self._session.request(
                method=method,
                url=urljoin(self._settings.api_base_url, endpoint),
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {tokens.access_token}"},
                timeout=self._settings.request_timeout_seconds,
            )
        if response.ok:
            return response
        raise NolioApiError(_error_message(response))


def _error_message(response: requests.Response) -> str:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
    else:
        detail = response.text
    return f"{response.status_code} {detail}"
