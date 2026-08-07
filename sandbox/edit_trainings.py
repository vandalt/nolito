# %%
from importlib import reload
import nolito
import nolito.client
reload(nolito)
reload(nolito.client)
from nolito import NolioApiClient
from copy import deepcopy


# %%
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


# %%
client = NolioApiClient()
athlete = client.get_athlete()

# %%
nolio_id = 30739770
training = client.get_planned_trainings(training_id=nolio_id)[0]

# %%
training["name"] = "Endurance copy"
training["date_start"] = "2026-08-07"

# %%
payload = {
    "id_partner": 12345,
    "sport_id": training["sport_id"],
    "name": training["name"],
    "date_start": training["date_start"],
    "description": training["description"],
    "duration": training["duration"],
    "rpe" : training["rpe"],
    "distance" : int(training["distance"]),
    "elevation_gain" : training["elevation_gain"],
    "structured_workout": with_step_types(training["structured_workout"]),
    "athlete_id": athlete["id"],
}

# %%
# TODO: Keep a record of the id_partner?
out = client.post("create/planned/training/", payload=payload)

# %%
payload_update = deepcopy(payload)
payload_update["name"] = "Endurance updated"
out = client.post("update/planned/training/", payload=payload_update)

# %%
payload_del = {
    "id_partner": payload["id_partner"],
    "athlete_id": payload["athlete_id"],
}
out = client.post("delete/planned/training/", payload=payload_del)
