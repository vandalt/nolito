from datetime import datetime

import pytest

from nolito.client import NolioApiClient

pytestmark = pytest.mark.integration


def _today():
    return datetime.now().astimezone().date()


def test_get_requests_user(client: NolioApiClient) -> None:
    assert isinstance(client.get("user/"), dict)


def test_get_athlete_returns_mapping(client: NolioApiClient) -> None:
    assert isinstance(client.get_athlete(), dict)


def test_get_metrics_returns_mapping(client: NolioApiClient) -> None:
    assert isinstance(client.get_metrics(), dict)


def test_get_planned_trainings_returns_list(client: NolioApiClient) -> None:
    today = _today()

    assert isinstance(client.get_planned_trainings(today, today), list)


def test_get_planned_trainings_max_30(client: NolioApiClient) -> None:
    assert len(client.get_planned_trainings()) > 0
    assert len(client.get_planned_trainings()) <= 30


def test_get_planned_trainings_max_expl(client: NolioApiClient) -> None:
    limit = 2
    assert len(client.get_planned_trainings(limit=limit)) == limit


def test_get_daily_trainings_returns_list(client: NolioApiClient) -> None:
    assert isinstance(client.get_daily_trainings(_today()), list)


def test_get_daily_trainings_defaults_today(client: NolioApiClient) -> None:
    explicit = client.get_daily_trainings(_today())
    default = client.get_daily_trainings()
    assert explicit == default
