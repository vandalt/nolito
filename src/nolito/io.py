import json
from pathlib import Path
from typing import Any


def save_workouts(workouts: list[dict[str, Any]], path: Path | str):
    """Save list of workout dictionaries to JSON

    :param workouts: The list of workouts as returned by :meth:`NolioApiClient.get_planned_trainings()
                     <nolito.client.NolioApiClient.get_planned_trainings>`
    :param path: Path where the output will be saved
    """
    path = Path(path)
    path.write_text(
        json.dumps(workouts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_workouts(path: Path | str) -> list[dict[str, Any]]:
    """Read a list of workout dictionaries from JSON

    :param path: Path of the JSON file
    :return: The list of workouts
    """
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))
