from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from nolito.client import NolioApiClient
from nolito.training import Training, TrainingSet

pytestmark = pytest.mark.integration


def _today():
    return datetime.now().astimezone().date()


def test_get_requests_user(client: NolioApiClient) -> None:
    assert isinstance(client.get("user/"), dict)


def test_get_athlete_returns_mapping(client: NolioApiClient) -> None:
    assert isinstance(client.get_athlete(), dict)


def test_get_metrics_returns_mapping(client: NolioApiClient) -> None:
    assert isinstance(client.get_metrics(), dict)


def test_get_planned_trainings_returns_set(client: NolioApiClient) -> None:
    today = _today()

    assert isinstance(client.get_planned_trainings(start=today, end=today), TrainingSet)


def test_get_planned_trainings_max_30(client: NolioApiClient) -> None:
    assert len(client.get_planned_trainings()) > 0
    assert len(client.get_planned_trainings()) <= 30


def test_get_planned_trainings_max_expl(client: NolioApiClient) -> None:
    limit = 2
    assert len(client.get_planned_trainings(limit=limit)) == limit


def test_get_daily_trainings_returns_set(client: NolioApiClient) -> None:
    assert isinstance(client.get_daily_trainings(_today()), TrainingSet)


def test_get_daily_trainings_defaults_today(client: NolioApiClient) -> None:
    explicit = client.get_daily_trainings(_today())
    default = client.get_daily_trainings()
    assert explicit == default


def test_planned_training_lifecycle_uses_automatic_partner_id(
    client: NolioApiClient,
) -> None:
    training = Training(
        sport_id=2,
        name=f"Nolito integration {uuid4()}",
        date_start=(_today() + timedelta(days=1)).isoformat(),
    )
    created: Training | None = None
    deleted = False

    try:
        created = client.create_training(training)

        assert isinstance(created.id_partner, int)
        assert created.id_partner > 0

        updated_name = f"{created.name} updated"
        created.name = updated_name
        updated = client.update_training(created)
        assert updated.name == updated_name

        client.delete_training(created)
        deleted = True

        remaining = client.get_planned_trainings(
            start=training.date_start, end=training.date_start
        )
        assert all(item.name != updated_name for item in remaining)
    finally:
        if created is not None and not deleted:
            client.delete_training(created)
