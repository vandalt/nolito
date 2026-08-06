from datetime import date
from unittest.mock import Mock, patch

import pytest

from nolito.client import NolioApiClient, _error_message
from nolito.errors import NolioApiError
from nolito.tokens import TokenSet


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
    ("start", "end", "limit", "expected"),
    [
        (
            date(2026, 1, 1),
            date(2026, 1, 3),
            None,
            {"from": "2026-01-01", "to": "2026-01-03", "limit": 6},
        ),
        (
            "2026-01-01",
            "2026-01-02",
            99,
            {"from": "2026-01-01", "to": "2026-01-02", "limit": 99},
        ),
        (None, None, None, {}),
    ],
)
def test_get_planned_trainings_builds_params(client, start, end, limit, expected):
    with patch.object(client, "get", return_value=[]) as get:
        client.get_planned_trainings(start, end, limit)
    get.assert_called_once_with("planned/training/", params=expected)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [([{"id": 1}], [{"id": 1}]), ({"results": [{"id": 2}]}, [{"id": 2}])],
)
def test_get_daily_trainings_accepts_supported_response_formats(
    client, payload, expected
):
    with patch.object(client, "get", return_value=payload) as get:
        assert client.get_daily_trainings("2026-01-03") == expected
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
