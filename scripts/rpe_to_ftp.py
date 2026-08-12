# %%
from copy import deepcopy
from pathlib import Path
from typing import Any

from nolito import NolioApiClient
from nolito.athlete import Athlete
from nolito.training import TrainingSet

try:
    rpe_plan_file = Path(__file__).parent / "data/bike_rpe.json"
except NameError:
    rpe_plan_file = "scripts/data/bike_rpe.json"
rpe_plan = TrainingSet.from_json(rpe_plan_file)

client = NolioApiClient()
athlete = client.get_athlete()
print(athlete.get_power_zones())

# %%
RPE_ZONE_UPPER_BOUNDS = (
    (2, "1"),
    (4, "2"),
    (6, "3"),
)
RPE_ZONE_VALUES = {7: "4", 8: "5", 9: "6"}

WorkoutStep = dict[str, Any]
Workout = list[WorkoutStep]

# %%
def convert_training_to_ftp(workout: Workout, athlete: Athlete) -> Workout:
    """Convert RPE and heart-rate targets in a structured workout to power targets."""
    power_zones = athlete.get_power_zones()

    def convert_steps(steps: Workout) -> Workout:
        converted_steps = []
        for step in steps:
            if step["type"] == "repetition":
                converted_step = {
                    key: deepcopy(value) for key, value in step.items() if key != "steps"
                }
                converted_step["steps"] = convert_steps(step["steps"])
            else:
                converted_step = _convert_step_to_ftp(step, power_zones)

            converted_steps.append(converted_step)
        return converted_steps

    return convert_steps(workout)


def _convert_step_to_ftp(
    step: WorkoutStep, power_zones: dict[str, tuple[float, float]]
) -> WorkoutStep:
    converted_step = deepcopy(step)

    power_zone = infer_power_zone(step)

    if power_zone is None:
        if "secondary_step" in step:
            converted_step["secondary_step"] = _convert_step_to_ftp(step["secondary_step"], power_zones)
        return converted_step

    if step["target_type"] == "rpe":
        del converted_step["rpe"]

    converted_step["target_type"] = "power"
    converted_step["name"] = f"Zone {power_zone}"
    converted_step["target_value_min"], converted_step["target_value_max"] = power_zones[
        power_zone
    ]
    return converted_step


def infer_power_zone(step: WorkoutStep) -> str | None:
    """Infer the power-zone identifier for a supported workout target."""
    match step["target_type"]:
        case "heartrate":
            return _infer_heart_rate_zone(step["name"])
        case "rpe":
            return _infer_rpe_zone(step["rpe"])
        case "rpm":
            return None
        case target_type:
            raise ValueError(f"Unsupported step target type {target_type}")


def _infer_heart_rate_zone(name: str) -> str:
    if name.startswith("Zone "):
        power_zone = name.removeprefix("Zone ").strip()
        if power_zone:
            return power_zone
    raise ValueError(
        f"Encountered an HR step without Zone in its name ({name})... Unsupported"
    )


def _infer_rpe_zone(rpe: float) -> str:
    for upper_bound, power_zone in RPE_ZONE_UPPER_BOUNDS:
        if rpe <= upper_bound:
            return power_zone
    return RPE_ZONE_VALUES.get(rpe, "7")

# %%
example_hr_training = rpe_plan[-1].copy()
example_hr_training_cadence = rpe_plan[36].copy()
example_rpe_training = rpe_plan[30].copy()
