from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

import requests

from .errors import NolioApiError
from .oauth import OAuthManager
from .settings import NolitoSettings


class NolioApiClient:
    """HTTP client for the Nolio API

    :param settings: Settings for this instance of the API.
                        Create with :meth:`NolitoSettings.from_env() <nolito.settings.NolitoSettings.from_env>`
                        if ``None``.
                        Defaults to ``None``.
    :param oauth: OAuthManager to use for the API.
                    Created automatically from settings and system keyring if ``None``.
                    Defaults to ``None``.
    :param session: `requests.Session <https://requests.readthedocs.io/en/latest/api/#requests.Session>`_ object to attach to the client.
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

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> list | dict:
        """Send a ``GET`` request to any Nolio API endpoint

        The list of endpoints is available on `the Nolio API wiki
        <https://github.com/NolioApp/NolioAPI-Documentation/wiki/API-Routes>`_.

        :param endpoint: The name of the endpoint (everything that comes after ``get/``).
        :param params: Optional parameters for the request.
        :return: The decoded json response.
        """
        return self._request("GET", f"get/{endpoint}", params=params).json()

    def post(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        payload: dict | None = None,
    ) -> dict | None:
        """Send a ``POST`` request to any Nolio API endpoint

        The list of endpoints is available on `the Nolio API wiki
        <https://github.com/NolioApp/NolioAPI-Documentation/wiki/API-Routes>`_.

        :param endpoint: The full name of the endpoint
        :param params: Optional parameters for the request.
        :param payload: Optional json payload for the request
        :return: The response content (dictionary if valid json, None if empty)
        """
        response = self._request("POST", endpoint, params=params, json=payload)
        return response.json() if response.content else None

    def create_training(
        self,
        id_partner: int,
        sport_id: int,
        name: str,
        date_start: date | str,
        *,
        description: str | None = None,
        duration: int | None = None,
        feeling: int | None = None,
        rpe: int | None = None,
        distance: int | None = None,
        elevation_gain: int | None = None,
        athlete_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a completed training.

        ``id_partner`` is the stable, integrator-owned identifier used to
        update or delete this training later. Persist it in the caller's
        system: Nolio does not return it in training retrieval responses.

        :param id_partner: Integrator-owned training identifier.
        :param sport_id: Nolio sport identifier.
        :param name: Training name.
        :param date_start: Training date.
        :param description: Optional training description.
        :param duration: Optional duration in seconds.
        :param feeling: Optional feeling score from 1 to 5.
        :param rpe: Optional perceived-exertion score from 1 to 10.
        :param distance: Optional distance in meters.
        :param elevation_gain: Optional elevation gain in meters.
        :param athlete_id: Optional athlete receiving the training.
        :return: The created training.
        :raises NolioApiError: If Nolio returns an unexpected response format.
        """
        payload = _without_none(
            {
                "id_partner": id_partner,
                "sport_id": sport_id,
                "name": name,
                "date_start": _format_date(date_start),
                "description": description,
                "duration": duration,
                "feeling": feeling,
                "rpe": rpe,
                "distance": distance,
                "elevation_gain": elevation_gain,
                "athlete_id": athlete_id,
            }
        )
        response = self.post("create/training/", payload=payload)
        return _require_mapping(response, "created training")

    def update_training(
        self,
        id_partner: int,
        sport_id: int,
        *,
        name: str | None = None,
        date_start: date | str | None = None,
        description: str | None = None,
        duration: int | None = None,
        feeling: int | None = None,
        rpe: int | None = None,
        distance: int | None = None,
        elevation_gain: int | None = None,
        athlete_id: int | None = None,
    ) -> dict[str, Any]:
        """Update a completed training created by this OAuth application.

        ``id_partner`` is the stable, integrator-owned identifier assigned
        when creating the training. Nolio requires ``sport_id`` for updates.

        :param id_partner: Integrator-owned training identifier.
        :param sport_id: Nolio sport identifier.
        :param name: Optional replacement training name.
        :param date_start: Optional replacement training date.
        :param description: Optional replacement training description.
        :param duration: Optional replacement duration in seconds.
        :param feeling: Optional replacement feeling score from 1 to 5.
        :param rpe: Optional replacement perceived-exertion score from 1 to 10.
        :param distance: Optional replacement distance in meters.
        :param elevation_gain: Optional replacement elevation gain in meters.
        :param athlete_id: Optional athlete owning the training.
        :return: The updated training.
        :raises NolioApiError: If Nolio returns an unexpected response format.
        """
        payload = _without_none(
            {
                "id_partner": id_partner,
                "sport_id": sport_id,
                "name": name,
                "date_start": _format_date(date_start)
                if date_start is not None
                else None,
                "description": description,
                "duration": duration,
                "feeling": feeling,
                "rpe": rpe,
                "distance": distance,
                "elevation_gain": elevation_gain,
                "athlete_id": athlete_id,
            }
        )
        response = self.post("update/training/", payload=payload)
        return _require_mapping(response, "updated training")

    def delete_training(
        self, id_partner: int, *, athlete_id: int | None = None
    ) -> None:
        """Delete a completed training created by this OAuth application.

        :param id_partner: Integrator-owned training identifier.
        :param athlete_id: Optional athlete owning the training.
        :return: ``None`` after Nolio's empty successful response.
        :raises NolioApiError: If Nolio returns an unexpected response format.
        """
        response = self.post(
            "delete/training/",
            payload=_without_none(
                {"id_partner": id_partner, "athlete_id": athlete_id}
            ),
        )
        if response is not None:
            raise NolioApiError("Unexpected deleted-training response format.")

    def get_athlete(self) -> dict[str, Any]:
        """Get the user information for the logged-in athlete

        :return: The json dictionary with user information.
        """
        payload = self.get("user/")
        if isinstance(payload, dict):
            return payload
        raise NolioApiError("Unexpected athlete response format.")

    def get_metrics(self) -> dict:
        """Get health metrics for the logged-in user

        These include FTP, VO2 Max, sleep, etc.
        It retains only the latest for each.

        :return: The dictionary with metrics
        """
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
        training_id: int | str | None = None,
        start: date | str | None = None,
        end: date | str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Get planned trainings for a given time frame.

        The returned list is ordered in decreasing order of date.

        Front-end for `/get/planned/training/ <https://github.com/NolioApp/NolioAPI-Documentation/wiki/Retrieve-Planned-Workouts>`_.

        :param training_id: Return only the training corresponding to this ID.
        :param start: Start date (defaults to ``None``)
        :param end: End date (defaults to ``None``)
        :param limit: Maximum number of trainings (API default is 30)
        :return: List of planned trainings
        """
        if start is not None:
            start = start if isinstance(start, str) else start.isoformat()
        if end is not None:
            end = end if isinstance(end, str) else end.isoformat()

        if limit is None and start is not None and end is not None:
            days_delta = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
            limit = days_delta * 2

        params = {
            k: v
            for k, v in {
                "from": start,
                "to": end,
                "limit": limit,
                "id": training_id,
            }.items()
            if v is not None
        }
        return self.get("planned/training/", params=params)

    def get_daily_trainings(
        self, day: date | str | None = None
    ) -> list[dict[str, Any]]:
        """Get trainings for a given day (today by default)

        :param day: The day for which trainings are returned.
                    Defaults to today when ``None``.
        :return: List of trainings planned on the day
        """
        local_tz = (
            datetime.now().astimezone().tzinfo
        )  # Set timezone explicitly to avoid confusion
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
        """Send an authenticated request to the Nolio API

        :param method: API method (``GET``, ``POST``, etc.)
        :param endpoint: API endpoint to query (e.g. ``/get/user``)
        :param params: Parameters for the request
        :param json: JSON to add to the request
        :return: The `requests.Response <https://requests.readthedocs.io/en/latest/api/#requests.Response>`_ object.
        """
        tokens = self._oauth.load_or_authorize()
        response = self._session.request(
            method=method,
            url=urljoin(self._settings.api_base_url, endpoint.lstrip("/")),
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            timeout=self._settings.request_timeout_seconds,
        )
        if response.status_code == 401:
            tokens = self._oauth.refresh(tokens.refresh_token)
            response = self._session.request(
                method=method,
                url=urljoin(self._settings.api_base_url, endpoint.lstrip("/")),
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {tokens.access_token}"},
                timeout=self._settings.request_timeout_seconds,
            )
        if response.ok:
            return response
        raise NolioApiError(_error_message(response))


def _error_message(response: requests.Response) -> str:
    """Extract error message from a response

    :param response: The `requests.Response <https://requests.readthedocs.io/en/latest/api/#requests.Response>`_ object.
    :return: The error message string
    """
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
    else:
        detail = response.text
    return f"{response.status_code} {detail}"


def _format_date(value: date | str) -> str:
    """Return an API date string."""
    return value if isinstance(value, str) else value.isoformat()


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    """Exclude optional API parameters that callers did not provide."""
    return {key: value for key, value in values.items() if value is not None}


def _require_mapping(
    response: dict[str, Any] | None, response_name: str
) -> dict[str, Any]:
    """Ensure an endpoint that documents JSON returns a JSON mapping."""
    if isinstance(response, dict):
        return response
    raise NolioApiError(f"Unexpected {response_name} response format.")
