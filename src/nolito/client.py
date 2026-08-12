from __future__ import annotations

import json
import sqlite3
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from nolito.athlete import Athlete
from nolito.training import Training, TrainingSet

from .errors import NolioApiError
from .oauth import OAuthManager
from .settings import NolitoSettings


class _PartnerIdRegistry:
    """Persist partner IDs assigned to trainings created by this client."""

    def __init__(self, path: Path):
        self._path = path

    def reserve(
        self,
        id_partner: int | None,
        *,
        athlete_id: int | None,
        planned: bool,
    ) -> int:
        """Reserve an existing or automatically allocated partner ID."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as connection:
            self._create_table(connection)
            if id_partner is None:
                cursor = connection.execute(
                    """
                    INSERT INTO partner_ids (athlete_id, planned, status)
                    VALUES (?, ?, 'reserved')
                    """,
                    (athlete_id, planned),
                )
                return int(cursor.lastrowid)

            row = connection.execute(
                """
                SELECT athlete_id, planned, status
                FROM partner_ids
                WHERE id_partner = ?
                """,
                (id_partner,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO partner_ids (id_partner, athlete_id, planned, status)
                    VALUES (?, ?, ?, 'reserved')
                    """,
                    (id_partner, athlete_id, planned),
                )
            elif row != (athlete_id, int(planned), "reserved"):
                raise NolioApiError(
                    f"Partner ID {id_partner} is already registered locally."
                )
            return id_partner

    def complete_reservation(self, training: Training) -> None:
        """Record a successful creation for a reserved partner ID."""
        with sqlite3.connect(self._path) as connection:
            self._create_table(connection)
            cursor = connection.execute(
                """
                UPDATE partner_ids
                SET nolio_id = ?, training_json = ?, status = 'registered'
                WHERE id_partner = ?
                  AND athlete_id IS ?
                  AND planned = ?
                  AND status = 'reserved'
                """,
                (
                    training.nolio_id,
                    _training_json(training),
                    training.id_partner,
                    training.athlete_id,
                    training.planned,
                ),
            )
            if cursor.rowcount != 1:
                raise NolioApiError(
                    f"Partner ID {training.id_partner} is not an active local reservation."
                )

    def register(self, training: Training) -> None:
        """Register a training that has not already been recorded locally."""
        id_partner = _required_partner_id(training)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as connection:
            self._create_table(connection)
            if connection.execute(
                "SELECT 1 FROM partner_ids WHERE id_partner = ?", (id_partner,)
            ).fetchone():
                raise NolioApiError(
                    f"Partner ID {id_partner} is already registered locally."
                )
            connection.execute(
                """
                INSERT INTO partner_ids (
                    id_partner, nolio_id, athlete_id, planned, status, training_json
                )
                VALUES (?, ?, ?, ?, 'registered', ?)
                """,
                (
                    id_partner,
                    training.nolio_id,
                    training.athlete_id,
                    training.planned,
                    _training_json(training),
                ),
            )

    def get(self, id_partner: int) -> Training:
        """Return a registered training by its partner ID."""
        with sqlite3.connect(self._path) as connection:
            self._create_table(connection)
            row = connection.execute(
                """
                SELECT id_partner, nolio_id, athlete_id, planned, training_json
                FROM partner_ids
                WHERE id_partner = ? AND status = 'registered'
                """,
                (id_partner,),
            ).fetchone()
        if row is None:
            raise KeyError(id_partner)
        return _training_from_registry_row(row)

    def list(self) -> list[Training]:
        """Return all registered trainings in partner-ID order."""
        with sqlite3.connect(self._path) as connection:
            self._create_table(connection)
            rows = connection.execute(
                """
                SELECT id_partner, nolio_id, athlete_id, planned, training_json
                FROM partner_ids
                WHERE status = 'registered'
                ORDER BY id_partner
                """
            ).fetchall()
        return [_training_from_registry_row(row) for row in rows]

    @staticmethod
    def _create_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_ids (
                id_partner INTEGER PRIMARY KEY AUTOINCREMENT,
                nolio_id INTEGER UNIQUE,
                athlete_id INTEGER,
                planned INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('reserved', 'registered')),
                training_json TEXT
            )
            """
        )
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(partner_ids)")
        }
        if "training_json" not in columns:
            connection.execute("ALTER TABLE partner_ids ADD COLUMN training_json TEXT")


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
        self._partner_ids = _PartnerIdRegistry(
            self._settings.metadata_file.parent / "partner-ids.sqlite3"
        )
        self._user = self.get_athlete()

    def __repr__(self):
        return f"NolioApiClient authenticated for {self._user.full_name}"

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

    def create_training(self, training: Training) -> Training:
        """Create a training and register its Nolio and partner identifiers.

        A missing ``Training.id_partner`` is allocated locally and stored in
        SQLite beside Nolito's token metadata. Explicit partner IDs are also
        registered, allowing later updates and deletes to use the same ID.

        :param training: Training object with all the workout information.
        :return: The created training.
        """
        training.id_partner = self._partner_ids.reserve(
            training.id_partner,
            athlete_id=training.athlete_id,
            planned=training.planned,
        )
        endpoint = (
            "create/planned/training/" if training.planned else "create/training/"
        )
        response = _require_mapping(
            self.post(endpoint, payload=training.to_edit_dict()), "create"
        )
        created = _training_from_response(training, response)
        self._partner_ids.complete_reservation(created)
        return created

    def register_training(self, training: Training) -> None:
        """Register a complete local training snapshot.

        :param training: Training to register. It must have an ``id_partner``.
        :raises ValueError: If ``training.id_partner`` is missing or invalid.
        :raises NolioApiError: If the partner ID is already registered.
        """
        self._partner_ids.register(training)

    def get_registered_training(self, id_partner: int) -> Training:
        """Return a registered training by its partner ID.

        :raises KeyError: If the partner ID is not registered.
        """
        return self._partner_ids.get(id_partner)

    def list_registered_trainings(self) -> TrainingSet:
        """Return all registered trainings in ascending partner-ID order."""
        return TrainingSet(self._partner_ids.list())

    def update_training(self, training: Training) -> Training:
        """Create a completed training.

        Training can be planned or non-planned.
        The ``Training.planned`` attribute will be used to determine this.

        :param training: Training object with all the workout information.
        :return: The created training.
        """
        endpoint = (
            "update/planned/training/" if training.planned else "update/training/"
        )
        return _training_from_response(
            training,
            _require_mapping(
                self.post(endpoint, payload=training.to_edit_dict()), "update"
            ),
        )

    def delete_training(self, training: Training) -> None:
        """Delete a completed training created by this OAuth application.

        :param id_partner: Integrator-owned training identifier.
        :param athlete_id: Optional athlete owning the training.
        :return: ``None`` after Nolio's empty successful response.
        :raises NolioApiError: If Nolio returns an unexpected response format.
        """
        delete_keys = ["id_partner", "athlete_id"]
        payload = {k: v for k, v in training.to_dict().items() if k in delete_keys}
        endpoint = (
            "delete/planned/training/" if training.planned else "delete/training/"
        )
        response = self.post(endpoint, payload=payload)
        if response is not None:
            raise NolioApiError("Unexpected deleted-training response format.")

    def get_athlete(self) -> Athlete:
        """Get the user information for the logged-in athlete

        This queries both "user/" and "user/meta" to get the main athlete info
        along health and performance metrics.

        :return: The json dictionary with user information.
        """
        user_payload = self.get("user/")
        if not isinstance(user_payload, dict):
            raise NolioApiError("Unexpected athlete response format.")
        return Athlete(**user_payload, metrics=self.get_metrics())

    def get_metrics(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Get the latest value for each populated athlete metric."""
        meta_payload = self.get("user/meta")
        if not isinstance(meta_payload, dict):
            raise NolioApiError("Unexpected athlete metadata response format.")
        return {
            key: {
                **metric,
                "data": max(metric["data"], key=lambda e: e["date"]),
            }
            for key, metric in meta_payload.items()
            if isinstance(metric, dict) and metric.get("data")
        }

    def get_planned_trainings(
        self,
        training_id: int | str | None = None,
        start: date | str | None = None,
        end: date | str | None = None,
        limit: int | None = None,
    ) -> TrainingSet:
        """Get planned trainings for a given time frame.

        The returned list is ordered in decreasing order of date.

        Front-end for `/get/planned/training/ <https://github.com/NolioApp/NolioAPI-Documentation/wiki/Retrieve-Planned-Workouts>`_.

        :param training_id: Return only the training corresponding to this ID.
        :param start: Start date (defaults to ``None``)
        :param end: End date (defaults to ``None``)
        :param limit: Maximum number of trainings returned.
                      If ``start`` and ``end`` are specified, defaults to twice the number of days.
                      Otherwise, uses the API default of 30.
        :return: Training set
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
        return TrainingSet(self.get("planned/training/", params=params))

    def get_daily_trainings(self, day: date | str | None = None) -> TrainingSet:
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
        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            payload = payload["results"]
        elif not isinstance(payload, list):
            raise NolioApiError("Unexpected planned-training response format.")
        return TrainingSet(payload)

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


def _require_mapping(
    response: dict[str, Any] | None, response_name: str
) -> dict[str, Any]:
    """Ensure an endpoint that documents JSON returns a JSON mapping."""
    if isinstance(response, dict):
        return response
    raise NolioApiError(f"Unexpected {response_name} response format.")


def _training_from_response(training: Training, response: dict[str, Any]) -> Training:
    """Merge Nolio's known response fields onto a submitted training."""
    values = {field.name: getattr(training, field.name) for field in fields(Training)}
    values.update({key: value for key, value in response.items() if key in values})
    values["id_partner"] = training.id_partner
    values["planned"] = training.planned
    return Training(**values)


def _required_partner_id(training: Training) -> int:
    """Return a valid partner ID from a local training."""
    if isinstance(training.id_partner, int) and not isinstance(
        training.id_partner, bool
    ):
        return training.id_partner
    raise ValueError("Registered trainings require an integer id_partner.")


def _training_json(training: Training) -> str:
    """Serialize a complete local training for the partner-ID registry."""
    values = {field.name: getattr(training, field.name) for field in fields(Training)}
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def _training_from_registry_row(
    row: tuple[int, int | None, int | None, int, str | None],
) -> Training:
    """Deserialize a registry row, including rows from the pre-payload schema."""
    id_partner, nolio_id, athlete_id, planned, training_json = row
    if training_json is None:
        return Training(
            id_partner=id_partner,
            nolio_id=nolio_id,
            athlete_id=athlete_id,
            planned=bool(planned),
        )
    values = json.loads(training_json)
    if not isinstance(values, dict):
        raise TypeError(f"Invalid training data for partner ID {id_partner}.")
    values.update(
        {
            "id_partner": id_partner,
            "nolio_id": nolio_id,
            "athlete_id": athlete_id,
            "planned": bool(planned),
        }
    )
    return Training(**values)
