from nolito import NolioApiClient
from nolito.training import TrainingSet

rpe_plan_file = "./scripts/data/bike_rpe.json"
rpe_plan = TrainingSet.from_json(rpe_plan_file)

client = NolioApiClient()
athlete = client.get_athlete()

power_plan = rpe_plan.to_power(athlete)
