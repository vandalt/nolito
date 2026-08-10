# %%
from nolito import NolioApiClient

# %%
client = NolioApiClient()
athlete = client.get_athlete()

# %%
nolio_id = 30739770
training = client.get_planned_trainings(training_id=nolio_id)[0]

# %%
training.name = "Endurance copy"
training.date_start = "2026-08-07"
training.id_partner = 12345

# %%
out = client.create_training(training)

# %%
training_update = training.copy()
training_update.name = "Endurance updated"
out = client.update_training(training_update)

# %%
client.delete_training(training)
