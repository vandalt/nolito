import re
from dataclasses import fields
from pathlib import Path

import pytest

from nolito.training import (
    Training,
    TrainingSet,
    _convert_step_to_ftp,
    _infer_heart_rate_zone,
    _infer_power_zone,
    _infer_rpe_zone,
)


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


class TestPowerConversion:
    @pytest.mark.parametrize(
        ("rpe", "power_zone"),
        [
            (1, "1"),
            (2, "1"),
            (3, "2"),
            (4, "2"),
            (5, "3"),
            (6, "3"),
            (7, "4"),
            (8, "5"),
            (9, "6"),
            (10, "7"),
        ],
    )
    def test_infers_rpe_power_zone(self, rpe, power_zone):
        assert _infer_rpe_zone(rpe) == power_zone

    def test_infers_heart_rate_power_zone(self):
        assert _infer_heart_rate_zone("Zone 3") == "3"
        assert _infer_power_zone({"target_type": "heartrate", "name": "Zone 4"}) == "4"

    @pytest.mark.parametrize("name", ["Zone", "Zone ", "Tempo"])
    def test_rejects_heart_rate_step_without_zone(self, name):
        with pytest.raises(ValueError, match="HR step without Zone"):
            _infer_heart_rate_zone(name)

    def test_rejects_unsupported_target_type(self):
        with pytest.raises(ValueError, match="Unsupported step target type speed"):
            _infer_power_zone({"target_type": "speed"})

    def test_converts_rpe_step_without_mutating_source(self, athlete):
        step = {
            "type": "step",
            "target_type": "rpe",
            "rpe": 8,
            "name": "RPE 8/10",
            "comment": "Hard effort",
        }

        converted = _convert_step_to_ftp(step, athlete.get_power_zones())

        assert converted == {
            "type": "step",
            "target_type": "power",
            "name": "Zone 5",
            "comment": "Hard effort",
            "target_value_min": 210,
            "target_value_max": 240,
        }
        assert step == {
            "type": "step",
            "target_type": "rpe",
            "rpe": 8,
            "name": "RPE 8/10",
            "comment": "Hard effort",
        }

    def test_converts_rpm_secondary_target_without_changing_rpm(self, athlete):
        step = {
            "type": "step",
            "target_type": "rpm",
            "target_value_min": 90,
            "target_value_max": 100,
            "name": "cadence",
            "secondary_step": {
                "target_type": "heartrate",
                "name": "Zone 2",
            },
        }

        converted = _convert_step_to_ftp(step, athlete.get_power_zones())

        assert converted["target_type"] == "rpm"
        assert converted["target_value_min"] == 90
        assert converted["target_value_max"] == 100
        assert converted["secondary_step"] == {
            "target_type": "power",
            "name": "Zone 2",
            "target_value_min": 110,
            "target_value_max": 150,
        }
        assert step["secondary_step"]["target_type"] == "heartrate"

    def test_to_power_converts_nested_steps_without_mutating_training(self, athlete):
        training = Training(
            name="Intervals",
            structured_workout=[
                {
                    "type": "repetition",
                    "value": 2,
                    "steps": [
                        {"target_type": "heartrate", "name": "Zone 1"},
                        {"target_type": "rpe", "rpe": 9, "name": "RPE 9/10"},
                    ],
                }
            ],
        )

        converted = training.to_power(athlete)
        steps = converted.structured_workout[0]["steps"]

        assert converted is not training
        assert steps[0]["target_type"] == "power"
        assert steps[0]["target_value_min"] == 0
        assert steps[0]["target_value_max"] == 110
        assert steps[1]["target_type"] == "power"
        assert steps[1]["target_value_min"] == 240
        assert steps[1]["target_value_max"] == 500
        assert "rpe" not in steps[1]
        assert training.structured_workout[0]["steps"][1]["target_type"] == "rpe"
        assert training.structured_workout[0]["steps"][1]["rpe"] == 9

    def test_to_power_without_structured_workout_returns_independent_copy(self, athlete):
        training = Training(name="Rest day")

        converted = training.to_power(athlete)

        assert converted == training
        assert converted is not training

    @pytest.mark.parametrize(
        "fixture_name",
        ["hr_training.json", "rpe_training.json", "cadence_hr_training.json"],
    )
    def test_converts_real_training_fixture(self, fixture_name, athlete):
        training = Training.from_json(Path("tests/data") / fixture_name)

        converted = training.to_power(athlete)

        _assert_workout_conversion(
            training.structured_workout,
            converted.structured_workout,
            athlete.get_power_zones(),
        )


def _assert_workout_conversion(original_steps, converted_steps, power_zones):
    assert len(converted_steps) == len(original_steps)
    for original, converted in zip(original_steps, converted_steps, strict=True):
        if original.get("type") == "repetition":
            _assert_workout_conversion(original["steps"], converted["steps"], power_zones)
            continue

        if original["target_type"] in {"heartrate", "rpe"}:
            power_zone = _infer_power_zone(original)
            assert converted["target_type"] == "power"
            assert converted["name"] == f"Zone {power_zone}"
            assert (
                converted["target_value_min"],
                converted["target_value_max"],
            ) == power_zones[power_zone]
            assert ("rpe" in converted) is False
        else:
            assert converted["target_type"] == "rpm"
            for key in ("target_value_min", "target_value_max"):
                assert converted.get(key) == original.get(key)
            if "secondary_step" in original:
                _assert_workout_conversion(
                    [original["secondary_step"]],
                    [converted["secondary_step"]],
                    power_zones,
                )


def test_training_set_to_power_converts_bike_rpe_plan_without_mutating_source(athlete):
    training_set = TrainingSet.from_json(Path("tests/data/bike_rpe.json"))

    converted = training_set.to_power(athlete)

    assert converted is not training_set
    assert len(converted) == len(training_set)
    assert [training.name for training in converted] == [
        training.name for training in training_set
    ]
    for original, power_training in zip(training_set, converted, strict=True):
        if original.structured_workout is not None:
            _assert_workout_conversion(
                original.structured_workout,
                power_training.structured_workout,
                athlete.get_power_zones(),
            )
