from pathlib import Path

from nolito import NolioApiClient
from nolito.training import TrainingSet

try:
    scripts_dir = data_dir = Path(__file__).parent
except NameError:
    scripts_dir = Path("scripts")
data_dir = scripts_dir / "data"
rpe_plan_file = data_dir / "bike_rpe.json"

rpe_plan = TrainingSet.from_json(rpe_plan_file)

client = NolioApiClient()
athlete = client.get_athlete()

example_hr_training = rpe_plan[-1].copy()
example_cadence_hr_training = rpe_plan[36].copy()
example_rpe_training = rpe_plan[30].copy()

example_hr_training.to_json(data_dir / "hr_training.json")
example_cadence_hr_training.to_json(data_dir / "cadence_hr_training.json")
example_rpe_training.to_json(data_dir / "rpe_training.json")
