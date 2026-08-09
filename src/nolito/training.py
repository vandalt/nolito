import copy
import json
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Self, overload


@dataclass
class Training:
    """A training payload.

    Unknown keyword arguments returned by Nolio's GET endpoints are ignored so
    that only supported fields can be sent to create and update endpoints.
    """

    nolio_id: int | None = None
    id_partner: int | None = None
    name: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    hour_start: str | None = None
    description: str | None = None
    sport: str | None = None
    sport_id: int | None = None
    duration: int | None = None
    distance: int | float | None = None
    feeling: int | None = None
    rpe: int | None = None
    elevation_gain: int | None = None
    elevation_loss: int | None = None
    load_foster: float | None = None
    load_coggan: float | None = None
    is_competition: bool | None = None
    kilojoules: int | None = None
    avg_watt: int | None = None
    max_watt: int | None = None
    athlete_id: int | None = None
    structured_workout: list | None = None
    planned: bool = field(default=True, metadata={"api": False})

    def __post_init__(self):
        if self.structured_workout is not None:
            self.structured_workout = with_step_types(self.structured_workout)

    def copy(self) -> "Training":
        return copy.deepcopy(self)

    def __copy__(self) -> "Training":
        return self.copy()

    @property
    def completed(self) -> bool:
        return not self.planned

    def to_dict(self, keep_none: bool = False) -> dict[str, Any]:
        values = asdict(self)
        return {
            f.name: values[f.name]
            for f in fields(self)
            if f.metadata.get("api", True) and (keep_none or values[f.name] is not None)
        }

    def to_edit_dict(self) -> dict:
        edit_keys = [
            "id_partner",
            "sport_id",
            "name",
            "date_start",
            "description",
            "duration",
            "rpe",
            "distance",
            "elevation_gain",
            "structured_workout",
            "athlete_id",
        ]
        edit_dict = {k: v for k, v in self.to_dict().items() if k in edit_keys}
        cast_keys = ["distance", "duration"]
        for key in cast_keys:
            if key in edit_dict:
                edit_dict[key] = int(edit_dict[key])
        return edit_dict

    def to_json(self, path: Path | str):
        path = Path(path)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: Path | str) -> Self:
        path = Path(path)
        json_dict = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(json_dict, dict):
            raise TypeError("JSON training data must be a dictionary")
        return cls(**json_dict)


class TrainingSet(Sequence[Training]):
    trainings: list[Training]

    def __init__(self, trainings: list[dict[str, Any] | Training]):
        new_trainings = []
        for training in trainings:
            if isinstance(training, Training):
                new_trainings.append(training)
            elif isinstance(training, dict):
                new_trainings.append(Training(**training))
            else:
                raise TypeError(
                    "Trainings can only be dictionaries or Training objects"
                )
        self.trainings = new_trainings

    def __repr__(self):
        return f"Training set with {len(self.trainings)} trainings"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TrainingSet) and self.trainings == other.trainings

    def __len__(self) -> int:
        return len(self.trainings)

    @overload
    def __getitem__(self, index: int) -> Training: ...

    @overload
    def __getitem__(self, index: slice) -> list[Training]: ...

    def __getitem__(self, index: int | slice) -> Training | list[Training]:
        return self.trainings[index]

    def __iter__(self) -> Iterator[Training]:
        return iter(self.trainings)

    def to_dicts(self) -> list[dict[str, Any]]:
        training_dicts = []
        for training in self.trainings:
            training_dicts.append(training.to_dict())
        return training_dicts

    def to_json(self, path: Path | str):
        path = Path(path)
        path.write_text(
            json.dumps(self.to_dicts(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: Path | str) -> Self:
        path = Path(path)
        training_dicts = json.loads(path.read_text(encoding="utf-8"))
        if not (isinstance(training_dicts, list) and all(
            isinstance(training, dict) for training in training_dicts
        )):
            raise TypeError("JSON training data must be a list of dictionaries")
        return cls(training_dicts)


def with_step_types(steps):
    normalized_steps = []
    for original_step in steps:
        step = original_step.copy()
        if step.get("type") == "repetition":
            step["steps"] = with_step_types(step["steps"])
        elif "type" not in step:
            step["type"] = "step"
        normalized_steps.append(step)
    return normalized_steps
