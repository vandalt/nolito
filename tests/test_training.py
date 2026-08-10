import re
from dataclasses import fields
from pathlib import Path

import pytest

from nolito.training import Training, TrainingSet


class TestTraining:
    def test_to_dict_excludes_local_fields(self):
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

    def test_to_dict_can_retain_none_api_fields(self):
        training = Training(id_partner=42, planned=False)

        api_fields = [f.name for f in fields(Training) if f.metadata.get("api", True)]
        expected_dict = {f: None for f in api_fields}
        expected_dict["id_partner"] = 42
        assert training.to_dict(keep_none=True) == expected_dict

    def test_extra_api_fields_raise_error(self):
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

    def test_copy_creates_an_independent_deep_copy(self):
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

    def test_json_round_trip(self, tmp_path):
        output_path = tmp_path / "workout.json"

        training = Training(name="FTP", duration=60)
        training.to_json(output_path)
        assert Training.from_json(output_path) == training

    def test_from_json_rejects_non_dictionary_data(self, tmp_path):
        path = tmp_path / "training.json"
        path.write_text('["not", "a", "training"]', encoding="utf-8")

        with pytest.raises(TypeError, match="JSON training data must be a dictionary"):
            Training.from_json(path)

    def test_real_nolio_json(self, tmp_path: Path):
        data_file = Path("tests/data/ftp_example_dict.json")
        training = Training.from_json(data_file)
        assert training.name == "3x10min avec 30s-30s"


class TestTrainingSet:
    def test_compare_training_values(self):
        first = TrainingSet([Training(name="FTP", duration=60)])
        second = TrainingSet([Training(name="FTP", duration=60)])

        assert first == second
        assert first.trainings[0] is not second.trainings[0]

    def test_json_round_trip(self, tmp_path):
        output_path = tmp_path / "workouts.json"

        trainings = TrainingSet(
            [Training(name="FTP", duration=60), Training(name="Skibidi", distance=10)]
        )
        trainings.to_json(output_path)
        assert TrainingSet.from_json(output_path) == trainings

    @pytest.mark.parametrize(
        "data_str", ['["not", "a", "training"]', '{"name": "allo"}']
    )
    def test_from_json_rejects_bad_format(self, tmp_path, data_str):
        path = tmp_path / "training.json"
        path.write_text(data_str, encoding="utf-8")

        with pytest.raises(
            TypeError, match="JSON training data must be a list of dictionaries"
        ):
            TrainingSet.from_json(path)

    def test_real_nolio_json(self, tmp_path: Path):
        data_file = Path("tests/data/ftp_example_list.json")
        training_set = TrainingSet.from_json(data_file)
        assert training_set[0].name == "3x10min avec 30s-30s"
