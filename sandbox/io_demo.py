# %%
from pathlib import Path

from nolito.client import NolioApiClient
from nolito.io import save_workouts

# %%
client = NolioApiClient()

# %%
trainings = client.get_planned_trainings(start="2026-07-28", end="2026-10-31")

data_dir = Path("./sandbox/data")
running_plan_path = data_dir / "ottawa_2024.json"
save_workouts(trainings, running_plan_path)

# %%
ftp_training_example = client.get_daily_trainings("2026-07-27")
save_workouts(ftp_training_example, data_dir / "ftp_example.json")

rpe_training_example = client.get_daily_trainings("2026-07-23")
save_workouts(rpe_training_example, data_dir / "rpe_example.json")
