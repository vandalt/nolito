import json
from pathlib import Path
from typing import Any


def save_workouts(workouts: list[dict[str, Any]], path: Path | str):
    path = Path(path)
    path.write_text(
        json.dumps(workouts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_workouts(path: Path | str) -> list[dict[str, Any]]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))
