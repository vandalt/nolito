import sqlite3
from datetime import date
from unittest.mock import Mock, patch

import pytest

from nolito.client import NolioApiClient, _error_message
from nolito.errors import NolioApiError
from nolito.tokens import TokenSet
from nolito.training import Training


@pytest.fixture
def client(settings):
    return NolioApiClient(
        settings=settings,
        oauth=Mock(),
        session=Mock(),
    )


def test_get_athlete_requests_user(client):
    payload = {"id": 123, "email": "athlete@example.test"}

    with patch.object(
        NolioApiClient, "get", autospec=True, return_value=payload
    ) as mock_get:
        result = client.get_athlete()

    assert result is payload
    mock_get.assert_called_once_with(client, "user/")


def test_constructor_creates_default_dependencies(settings):
    session = Mock()
    token_store = Mock()
    with (
        patch(
            "nolito.client.NolitoSettings.from_env", return_value=settings
        ) as from_env,
        patch(
            "nolito.tokens.KeyringTokenStore.from_settings", return_value=token_store
        ) as store,
        patch("nolito.client.OAuthManager") as oauth_manager,
        patch("nolito.client.requests.Session", return_value=session),
    ):
        client = NolioApiClient()

    assert client._settings is settings
    assert client._oauth is oauth_manager.return_value
    assert client._session is session
    from_env.assert_called_once_with()
    store.assert_called_once_with(settings)
    oauth_manager.assert_called_once_with(settings=settings, token_store=token_store)


def test_get_forwards_endpoint_and_params(client):
    response = Mock()
    response.json.return_value = {"id": 1}
    with patch.object(client, "_request", return_value=response) as request:
        assert client.get("training/", params={"limit": 10}) == {"id": 1}
    request.assert_called_once_with("GET", "get/training/", params={"limit": 10})


@pytest.mark.parametrize(
    ("content", "json_payload", "expected"),
    [(b'{"nolio_id": 1}', {"nolio_id": 1}, {"nolio_id": 1}), (b"", {}, None)],
)
def test_post_returns_json_or_none_for_an_empty_response(
    client, content, json_payload, expected
):
    response = Mock()
    response.content = content
    response.json.return_value = json_payload
    with patch.object(client, "_request", return_value=response) as request:
        assert client.post("delete/training/", payload={"id_partner": 1}) == expected

    request.assert_called_once_with(
        "POST", "delete/training/", params=None, json={"id_partner": 1}
    )


@pytest.mark.parametrize(
    ("method", "planned", "payload", "response", "endpoint"),
    [
        (
            "create_training",
            planned,
            {
                "id_partner": 42,
                "sport_id": 2,
                "name": "Intervals",
                "date_start": "2026-08-07",
                "duration": 3600,
                "rpe": 8,
                "athlete_id": 99,
            },
            {"nolio_id": 123},
            f"create/{'planned/' if planned else ''}training/",
        )
        for planned in (True, False)
    ]
    + [
        (
            "update_training",
            planned,
            {
                "id_partner": 42,
                "sport_id": 2,
                "name": "Recovery",
                "date_start": "2026-08-08",
                "distance": 5,
            },
            {"nolio_id": 123, "name": "Recovery"},
            f"update/{'planned/' if planned else ''}training/",
        )
        for planned in (True, False)
    ]
    + [
        (
            "delete_training",
            planned,
            {"id_partner": 42, "athlete_id": 99},
            None,
            f"delete/{'planned/' if planned else ''}training/",
        )
        for planned in (True, False)
    ],
)
def test_training_post_builds_documented_payload(
    client, method, planned, payload, response, endpoint
):
    training = Training(**payload, planned=planned)

    with patch.object(client, "post", return_value=response) as post:
        result = getattr(client, method)(training)

    if method == "create_training":
        assert result.id_partner == payload["id_partner"]
        assert result.nolio_id == response["nolio_id"]
        assert result.planned is planned
    elif result is None:
        assert result is response
    else:
        assert result.id_partner == payload["id_partner"]
        assert result.name == response["name"]
        assert result.planned is planned
    post.assert_called_once_with(endpoint, payload=payload)


@pytest.mark.parametrize("planned", [True, False])
def test_create_training_allocates_and_registers_partner_id(client, settings, planned):
    training = Training(
        sport_id=2,
        name="Intervals",
        date_start="2026-08-07",
        athlete_id=99,
        planned=planned,
    )

    response = {
        "id_partner": 1,
        "name": "Intervals",
        "date_start": "2026-08-07T00:00:00",
        "rpe": 0,
        "duration": None,
        "distance": None,
        "elevation_gain": None,
        "plan_id": None,
    }
    with patch.object(client, "post", return_value=response) as post:
        created = client.create_training(training)

    assert training.id_partner == 1
    assert created.id_partner == 1
    assert created.nolio_id is None
    assert created.name == "Intervals"
    assert created.sport_id == 2
    assert created.planned is planned
    assert client.get_registered_training(1) == created
    post.assert_called_once_with(
        f"create/{'planned/' if planned else ''}training/",
        payload={
            "id_partner": 1,
            "sport_id": 2,
            "name": "Intervals",
            "date_start": "2026-08-07",
            "athlete_id": 99,
        },
    )
    with sqlite3.connect(settings.metadata_file.parent / "partner-ids.sqlite3") as db:
        assert db.execute(
            """
            SELECT id_partner, nolio_id, athlete_id, planned, status
            FROM partner_ids
            """
        ).fetchone() == (1, None, 99, int(planned), "registered")


def test_register_training_round_trips_complete_payload_without_http(client):
    training = Training(
        id_partner=42,
        nolio_id=123,
        name="Intervals",
        date_start="2026-08-07",
        sport_id=2,
        athlete_id=99,
        structured_workout=[{"step_duration_type": "duration"}],
    )

    client.register_training(training)

    assert client.get_registered_training(42) == training
    assert client._session.request.call_count == 0


def test_list_registered_trainings_orders_by_partner_id(client):
    later = Training(id_partner=42, name="Later")
    earlier = Training(id_partner=3, name="Earlier", planned=False)

    client.register_training(later)
    client.register_training(earlier)

    assert list(client.list_registered_trainings()) == [earlier, later]


def test_register_training_rejects_missing_or_duplicate_partner_id(client):
    training = Training(id_partner=42, name="Intervals")

    with pytest.raises(ValueError, match="id_partner"):
        client.register_training(Training(name="Missing ID"))

    client.register_training(training)
    with pytest.raises(NolioApiError, match="already registered"):
        client.register_training(training)


def test_get_registered_training_rejects_missing_partner_id(client):
    with pytest.raises(KeyError, match="42"):
        client.get_registered_training(42)


def test_registered_training_migrates_identifier_only_database(client, settings):
    database = settings.metadata_file.parent / "partner-ids.sqlite3"
    database.parent.mkdir(exist_ok=True)
    with sqlite3.connect(database) as db:
        db.execute(
            """
            CREATE TABLE partner_ids (
                id_partner INTEGER PRIMARY KEY AUTOINCREMENT,
                nolio_id INTEGER UNIQUE,
                athlete_id INTEGER,
                planned INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('reserved', 'registered'))
            )
            """
        )
        db.execute(
            """
            INSERT INTO partner_ids (
                id_partner, nolio_id, athlete_id, planned, status
            )
            VALUES (42, 123, 99, 1, 'registered')
            """
        )

    assert client.get_registered_training(42) == Training(
        id_partner=42,
        nolio_id=123,
        athlete_id=99,
    )
    with sqlite3.connect(database) as db:
        assert "training_json" in {
            row[1] for row in db.execute("PRAGMA table_info(partner_ids)")
        }


def test_create_training_registers_explicit_partner_id(client, settings):
    training = Training(
        id_partner=42,
        sport_id=2,
        name="Intervals",
        date_start="2026-08-07",
    )

    with patch.object(client, "post", return_value={"nolio_id": 123}):
        created = client.create_training(training)

    assert created.id_partner == 42
    with sqlite3.connect(settings.metadata_file.parent / "partner-ids.sqlite3") as db:
        assert db.execute(
            "SELECT id_partner, nolio_id, status FROM partner_ids"
        ).fetchone() == (42, 123, "registered")


def test_create_training_rejects_registered_partner_id(client):
    original = Training(
        id_partner=42,
        sport_id=2,
        name="Intervals",
        date_start="2026-08-07",
    )
    duplicate = original.copy()

    with patch.object(client, "post", return_value={"nolio_id": 123}):
        client.create_training(original)
    with (
        patch.object(client, "post") as post,
        pytest.raises(NolioApiError, match="already registered"),
    ):
        client.create_training(duplicate)

    post.assert_not_called()


def test_create_training_ids_are_monotonic_across_clients(settings):
    trainings = [
        Training(sport_id=2, name="One", date_start="2026-08-07"),
        Training(sport_id=2, name="Two", date_start="2026-08-08"),
    ]
    first = NolioApiClient(settings=settings, oauth=Mock(), session=Mock())
    second = NolioApiClient(settings=settings, oauth=Mock(), session=Mock())

    with patch.object(first, "post", return_value={"nolio_id": 123}):
        first.create_training(trainings[0])
    with patch.object(second, "post", return_value={"nolio_id": 124}):
        second.create_training(trainings[1])

    assert [training.id_partner for training in trainings] == [1, 2]


@pytest.mark.parametrize("response", [None, []])
def test_create_training_does_not_register_malformed_response(client, settings, response):
    training = Training(sport_id=2, name="Intervals", date_start="2026-08-07")

    with (
        patch.object(client, "post", return_value=response),
        pytest.raises(NolioApiError, match="response|nolio_id"),
    ):
        client.create_training(training)

    with sqlite3.connect(settings.metadata_file.parent / "partner-ids.sqlite3") as db:
        assert db.execute(
            "SELECT nolio_id, status FROM partner_ids WHERE id_partner = 1"
        ).fetchone() == (None, "reserved")


@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        ("create_training", {"id_partner": 42, "sport_id": 2, "name": "Intervals", "date_start": "2026-08-07"}),
        ("update_training", {"id_partner": 42, "sport_id": 2}),
    ],
)
def test_training_create_and_update_reject_empty_responses(
    client, method, kwargs
):
    training = Training(**kwargs)
    with (
        patch.object(client, "post", return_value=None),
        pytest.raises(NolioApiError, match="response format"),
    ):
        getattr(client, method)(training)


def test_delete_training_rejects_json_response(client):
    with (
        patch.object(client, "post", return_value={"nolio_id": 123}),
        pytest.raises(NolioApiError, match="deleted-training"),
    ):
        client.delete_training(Training(id_partner=42))


def test_request_preserves_api_path_for_leading_slash_endpoint(
    client, settings, tokens, make_response
):
    client._oauth.load_or_authorize.return_value = tokens
    client._session.request.return_value = make_response(payload={})

    client._request("POST", "/create/planned/training/", json={"id_partner": 1234})

    assert client._session.request.call_args.kwargs["url"] == (
        f"{settings.api_base_url}create/planned/training/"
    )


@pytest.mark.parametrize("payload", [[], "not a user"])
def test_get_athlete_rejects_unexpected_payload(client, payload):
    with (
        patch.object(client, "get", return_value=payload),
        pytest.raises(NolioApiError, match="Unexpected athlete"),
    ):
        client.get_athlete()


def test_get_metrics_selects_only_latest_populated_metrics(client):
    with patch.object(
        client,
        "get",
        return_value={
            "weight": {"data": [{"date": "2026-01-01"}, {"date": "2026-01-02"}]},
            "empty": {"data": []},
            "other": "ignored",
        },
    ):
        assert client.get_metrics() == {"weight": {"data": {"date": "2026-01-02"}}}


@pytest.mark.parametrize("payload", [[], "invalid"])
def test_get_metrics_rejects_non_mapping_response(client, payload):
    with (
        patch.object(client, "get", return_value=payload),
        pytest.raises(NolioApiError, match="metadata"),
    ):
        client.get_metrics()


@pytest.mark.parametrize(
    ("training_id", "start", "end", "limit", "expected"),
    [
        (
            "123455",
            date(2026, 1, 1),
            date(2026, 1, 3),
            None,
            {"from": "2026-01-01", "to": "2026-01-03", "limit": 6, "id": "123455"},
        ),
        (
            "123455",
            "2026-01-01",
            "2026-01-02",
            99,
            {"from": "2026-01-01", "to": "2026-01-02", "limit": 99, "id": "123455"},
        ),
        (None, None, None, None, {}),
    ],
)
def test_get_planned_trainings_builds_params(
    client, training_id, start, end, limit, expected
):
    with patch.object(client, "get", return_value=[]) as get:
        client.get_planned_trainings(training_id, start, end, limit)
    get.assert_called_once_with("planned/training/", params=expected)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [([{"nolio_id": 1}], [{"nolio_id": 1}]), ({"results": [{"nolio_id": 2}]}, [{"nolio_id": 2}])],
)
def test_get_daily_trainings_accepts_supported_response_formats(
    client, payload, expected
):
    with patch.object(client, "get", return_value=payload) as get:
        assert client.get_daily_trainings("2026-01-03").to_dicts() == expected
    get.assert_called_once_with(
        "planned/training/", params={"from": "2026-01-03", "to": "2026-01-03"}
    )


def test_get_daily_trainings_rejects_unexpected_response(client):
    with (
        patch.object(client, "get", return_value={"results": "invalid"}),
        pytest.raises(NolioApiError, match="planned-training"),
    ):
        client.get_daily_trainings("2026-01-03")


def test_request_refreshes_once_after_unauthorized_response(
    client, settings, tokens, make_response
):
    unauthorized = make_response(ok=False, status_code=401)
    success = make_response(payload={"id": 1})
    refreshed = TokenSet("new-access", "new-refresh", 2_000_000_000)
    client._oauth.load_or_authorize.return_value = tokens
    client._oauth.refresh.return_value = refreshed
    client._session.request.side_effect = [unauthorized, success]

    assert client._request("GET", "get/user/", params={"x": "y"}) is success
    expected_url = "https://api.example.test/api/get/user/"
    assert client._session.request.call_count == 2
    for request_call, access_token in zip(
        client._session.request.call_args_list,
        [tokens.access_token, refreshed.access_token],
        strict=True,
    ):
        assert request_call.kwargs == {
            "method": "GET",
            "url": expected_url,
            "params": {"x": "y"},
            "json": None,
            "headers": {"Authorization": f"Bearer {access_token}"},
            "timeout": settings.request_timeout_seconds,
        }
    client._oauth.refresh.assert_called_once_with(tokens.refresh_token)


def test_request_raises_for_non_success_response(client, make_response):
    failed = make_response(
        ok=False,
        status_code=400,
        headers={"content-type": "text/plain"},
        text="Bad request",
    )
    client._oauth.load_or_authorize.return_value = Mock()
    client._session.request.return_value = failed
    with pytest.raises(NolioApiError, match="400 Bad request"):
        client._request("GET", "get/user/")


@pytest.mark.parametrize(
    ("headers", "payload", "text", "json_error", "expected"),
    [
        (
            {"content-type": "application/json"},
            {"detail": "Nope"},
            "fallback",
            None,
            "401 Nope",
        ),
        ({"content-type": "application/json"}, {}, "fallback", None, "401 fallback"),
        ({}, None, "plain", None, "401 plain"),
        (
            {"content-type": "application/json"},
            None,
            "invalid",
            ValueError(),
            "401 invalid",
        ),
    ],
)
def test_error_message_handles_response_content(
    make_response, headers, payload, text, json_error, expected
):
    assert (
        _error_message(
            make_response(
                status_code=401,
                headers=headers,
                payload=payload,
                text=text,
                json_side_effect=json_error,
            )
        )
        == expected
    )
