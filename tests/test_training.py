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


def test_extra_api_fields_are_ignored():
    training = Training(
        id_partner=42,
        name="Intervals",
        nolio_id=123,
        coach={"id": 9},
    )

    assert training.to_dict() == {"id_partner": 42, "name": "Intervals"}
    assert not hasattr(training, "nolio_id")
    assert not hasattr(training, "coach")


def test_copy_creates_an_independent_deep_copy():
    training = Training(
        id_partner=42,
        structured_workout=[
            {
                "type": "repetition",
                "steps": [{"duration": 60, "targets": [{"power": 200}]}],
            }
        ],
    )

    copied = training.copy()
    copied.structured_workout[0]["steps"][0]["targets"][0]["power"] = 250

    assert copied == Training(
        id_partner=42,
        structured_workout=[
            {
                "type": "repetition",
                "steps": [
                    {
                        "type": "step",
                        "duration": 60,
                        "targets": [{"power": 250}],
                    }
                ],
            }
        ],
    )
    assert training.structured_workout[0]["steps"][0]["targets"][0]["power"] == 200