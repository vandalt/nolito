import re
from pathlib import Path

import pytest

from nolito.training import Training, TrainingSet


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
        "nolio_id": None,
        "id_partner": 42,
        "name": None,
        "date_start": None,
        "date_end": None,
        "hour_start": None,
        "description": None,
        "sport": None,
        "sport_id": None,
        "duration": None,
        "distance": None,
        "feeling": None,
        "rpe": None,
        "elevation_gain": None,
        "elevation_loss": None,
        "load_foster": None,
        "load_coggan": None,
        "is_competition": None,
        "kilojoules": None,
        "avg_watt": None,
        "max_watt": None,
        "athlete_id": None,
        "structured_workout": None,
    }


def test_extra_api_fields_raise_error():
    with pytest.raises(
        TypeError,
        match=re.escape(
            "Training.__init__() got an unexpected keyword argument 'coach'"
        ),
    ):
        Training(
            id_partner=42,
            name="Intervals",
            nolio_id=123,
            coach={"id": 9},
        )


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


def test_training_sets_compare_training_values():
    first = TrainingSet([Training(name="FTP", duration=60)])
    second = TrainingSet([Training(name="FTP", duration=60)])

    assert first == second
    assert first.trainings[0] is not second.trainings[0]


def test_training_json_round_trip(tmp_path):
    output_path = tmp_path / "workout.json"

    training = Training(name="FTP", duration=60)
    training.to_json(output_path)
    assert Training.from_json(output_path) == training


def test_training_set_json_round_trip(tmp_path):
    output_path = tmp_path / "workouts.json"

    trainings = TrainingSet(
        [Training(name="FTP", duration=60), Training(name="Skibidi", distance=10)]
    )
    trainings.to_json(output_path)
    assert TrainingSet.from_json(output_path) == trainings


def test_training_from_json_rejects_non_dictionary_data(tmp_path):
    path = tmp_path / "training.json"
    path.write_text('["not", "a", "training"]', encoding="utf-8")

    with pytest.raises(TypeError, match="JSON training data must be a dictionary"):
        Training.from_json(path)


@pytest.mark.parametrize("data_str", ['["not", "a", "training"]', '{"name": "allo"}'])
def test_training_set_from_json_rejects_bad_format(tmp_path, data_str):
    path = tmp_path / "training.json"
    path.write_text(data_str, encoding="utf-8")

    with pytest.raises(
        TypeError, match="JSON training data must be a list of dictionaries"
    ):
        TrainingSet.from_json(path)


def test_training_real_nolio_json(tmp_path: Path):
    data_file = Path("tests/data/ftp_example_dict.json")
    training = Training.from_json(data_file)
    assert training.name == "3x10min avec 30s-30s"


def test_training_set_real_nolio_json(tmp_path: Path):
    data_file = Path("tests/data/ftp_example_list.json")
    training_set = TrainingSet.from_json(data_file)
    assert training_set[0].name == "3x10min avec 30s-30s"

