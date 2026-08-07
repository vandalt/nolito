from nolito.training import Training


def test_to_dict_excludes_local_fields():
    training = Training(
        id_partner=42,
        sport_id=2,
        name="Intervals",
        date_start="2026-08-07",
        planned=True,
    )

    assert training.to_dict() == {
        "id_partner": 42,
        "sport_id": 2,
        "name": "Intervals",
        "date_start": "2026-08-07",
    }


def test_to_dict_can_retain_none_api_fields():
    training = Training(id_partner=42, planned=False)

    assert training.to_dict(keep_none=True) == {
        "id_partner": 42,
        "sport_id": None,
        "name": None,
        "date_start": None,
        "description": None,
        "duration": None,
        "feeling": None,
        "rpe": None,
        "distance": None,
        "elevation_gain": None,
        "athlete_id": None,
        "structured_workout": None,
    }