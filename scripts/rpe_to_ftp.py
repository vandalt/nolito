# %%
from pathlib import Path

from nolito import NolioApiClient
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
example_hr_training = rpe_plan[-1].copy()
example_hr_training_cadence = rpe_plan[36].copy()
example_rpe_training = rpe_plan[30].copy()

# %%
example_hr_training.to_power(athlete)
