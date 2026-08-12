import copy
import json
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Self, overload


@dataclass
class Training:
    """A training payload for the Nolio API

    Full reference: https://github.com/NolioApp/NolioAPI-Documentation/wiki/Training-Object

    This is a `Data Class <https://docs.python.org/3/library/dataclasses.html>_` so all parameters are also attributes.

    :param nolio_id: ID assigned by the nolio website
    :param id_partner: ID assigned by the local "partner" app
    :param name: Name of the training
    :param date_start: Start date (YYYY-MM-DD)
    :param date_end: End date (YYYY-MM-DD)
    :param hour_start: Start time
    :param description: Training description
    :param sport: Sport name
    :param sport_id: Nolio sport ID (https://github.com/NolioApp/NolioAPI-Documentation/wiki/Training-Object#sport-map)
    :param duration: Workout duration in min
    :param distance: Workout distance in km
    :param feeling: Athlete feeling
    :param rpe: Athlete RPE
    :param elevation_gain: Elevation gain
    :param elevation_loss: Elevation loss
    :param load_foster: Foster load
    :param load_coggan: Coggan load
    :param is_competition: ``True`` if the workout is a competition
    :param kilojoules: Kilojoules spent
    :param avg_watt: Average power in watts
    :param max_watt: Max power in watts
    :param athlete_id: Athlete ID (assigned by Nolio)
    :param structured_workout: Structured workout dictionary
    :param planned: Whether this is a planned workout. Not sent to the Nolio API, for local use only.
    """

    nolio_id: int | None = None
    id_partner: int | None = None
    name: str | None = None
    date_start: str | None = None
    date_end: str | None = field(default=None, repr=False)
    hour_start: str | None = field(default=None, repr=False)
    description: str | None = field(default=None, repr=False)
    sport: str | None = None
    sport_id: int | None = field(default=None, repr=False)
    duration: int | None = field(default=None, repr=False)
    distance: int | float | None = field(default=None, repr=False)
    feeling: int | None = field(default=None, repr=False)
    rpe: int | None = field(default=None, repr=False)
    elevation_gain: int | None = field(default=None, repr=False)
    elevation_loss: int | None = field(default=None, repr=False)
    load_foster: float | None = field(default=None, repr=False)
    load_coggan: float | None = field(default=None, repr=False)
    is_competition: bool | None = field(default=None, repr=False)
    kilojoules: int | None = field(default=None, repr=False)
    avg_watt: int | None = field(default=None, repr=False)
    max_watt: int | None = field(default=None, repr=False)
    athlete_id: int | None = field(default=None, repr=False)
    structured_workout: list | None = field(default=None, repr=False)
    planned: bool = field(default=True, metadata={"api": False})

    def __post_init__(self):
        """Post-init ensuring the structured workout has step types everywhere"""
        if self.structured_workout is not None:
            self.structured_workout = with_step_types(self.structured_workout)

        def _extract_date(datetime_str: str):
            return datetime.fromisoformat(self.date_start).date().isoformat()

        if self.date_start:
            self.date_start = _extract_date(self.date_start)
        if self.date_end:
            self.date_end = _extract_date(self.date_end)

    def copy(self) -> "Training":
        """Return a deepcopy of the training"""
        return copy.deepcopy(self)

    def __copy__(self) -> "Training":
        """Alias to ``self.copy()``"""
        return self.copy()

    @property
    def completed(self) -> bool:
        """Is the training a completed workout?

        return: Returns the opposite of ``Training.planned``
        """
        return not self.planned

    def to_dict(self, keep_none: bool = False) -> dict[str, Any]:
        """Convert the training object to a dictionary

        This is useful to interact with the Nolio API or to save trainings to JSON files.

        :param keep_none: Keep fields that have a none value if ``True`` (defaults to ``False``)
        :return: The training dictionary
        """
        values = asdict(self)
        return {
            f.name: values[f.name]
            for f in fields(self)
            if f.metadata.get("api", True) and (keep_none or values[f.name] is not None)
        }

    def to_edit_dict(self) -> dict:
        """Convert the training object to a dictioanry for ``POST`` requests

        Only keys compatible with the API's ``POST`` requests are included,
        when they are not None.

        :return: The ``POST`` ready dictionary
        """
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

    def to_json(self, path: Path | str, overwrite: bool = False):
        """Save the training to a json file

        Uses :meth:`Training.to_dict()`

        :param path: Path to the JSON file
        :param overwrite: Overwrite the file if it exists
        :raises FileExistsError: If the file exists and ``ovewrite`` is ``False``
        """
        path = Path(path)
        if path.exists() and not overwrite:
            raise FileExistsError(f"The output file {path} exists and overwrite is False")
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: Path | str) -> Self:
        """Load the training from a JSON file

        :param path: Path to the JSON file
        :raises TypeError: Raised if the JSON data is not a dictionary
        :return: The training object read from the file
        """
        path = Path(path)
        json_dict = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(json_dict, dict):
            raise TypeError("JSON training data must be a dictionary")
        return cls(**json_dict)


class TrainingSet(Sequence[Training]):
    """A set of :class:`Training` objects

    Useful to construct a training calendar or a training plan

    :param trainings: List of training objects or dictionaries used as input
                      If ``trainings`` contains dictionaries,
                      they are converted to :class:`Training` instances
    :ivar trainings: List of training objects stored internally
    :vartype trainings: ``list`` [:class:`Training`]
    """

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
        trainings_str = "\n".join([f"{i}: {training}" for i, training in enumerate(self.trainings)])
        return f"Trainings:\n{trainings_str}\n(Training set with {len(self)} trainings)\n"

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
        """Convert the objects to a list of dictionaries

        Converts the trainings with :meth:`Training.to_dict()`

        :return: List of dictionaries with training info
        """
        training_dicts = []
        for training in self.trainings:
            training_dicts.append(training.to_dict())
        return training_dicts

    def to_json(self, path: Path | str, overwrite: bool = False):
        """Save the trainings to JSON a list of dictionaries

        :param path: Path to the JSON file
        :param overwrite: Overwrite the file if it exists
        :raises FileExistsError: If the file exists and ``ovewrite`` is ``False``
        """
        path = Path(path)
        if path.exists() and not overwrite:
            raise FileExistsError(f"The output file {path} exists and overwrite is False")
        path.write_text(
            json.dumps(self.to_dicts(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: Path | str) -> Self:
        """Create a training set from a JSON file

        :param path: Path to the JSON file
        :raises TypeError: Raised if the JSON is not a list of dictionaries
        :return: The newly create training set
        """
        path = Path(path)
        training_dicts = json.loads(path.read_text(encoding="utf-8"))
        if not (
            isinstance(training_dicts, list)
            and all(isinstance(training, dict) for training in training_dicts)
        ):
            raise TypeError("JSON training data must be a list of dictionaries")
        return cls(training_dicts)


def with_step_types(steps: list[dict]) -> list[dict]:
    """Ensure that each step in a structured workout has a ``"type"`` field

    The default type ``"step"``.

    :param steps: The structured workout dictionary
    :return: The normalized structured workout dictionary
    """
    normalized_steps = []
    for original_step in steps:
        step = original_step.copy()
        if step.get("type") == "repetition":
            step["steps"] = with_step_types(step["steps"])
        elif "type" not in step:
            step["type"] = "step"
        normalized_steps.append(step)
    return normalized_steps
