from nolito.io import load_workouts, save_workouts


def test_save_and_load_workouts_round_trip(tmp_path):
    workouts = [{"name": "FTP", "steps": [{"duration": 60}]}]
    output_path = tmp_path / "workouts.json"

    save_workouts(workouts, str(output_path))

    assert load_workouts(str(output_path)) == workouts
