from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass
class Training:
    id_partner: int | None = None
    sport_id: int | None = None
    name: str | None = None
    date_start: str | None = None
    description: str | None = None
    duration: int | None = None
    feeling: int | None = None
    rpe: int | None = None
    distance: int | None = None
    elevation_gain: int | None = None
    athlete_id: int | None = None
    structured_workout: list | None = None
    planned: bool = field(default=True, metadata={"api": False})

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
