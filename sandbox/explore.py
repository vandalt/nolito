# %%
import pprint

from nolito.client import NolioApiClient
from nolito.io import load_workouts, save_workouts

# %%
client = NolioApiClient()

# %%
athlete = client.get_athlete()
name = f"{athlete.get('first_name', '')} {athlete.get('last_name', '')}".strip() or "(unnamed)"
athlete_id = athlete.get("id", "?")
email = athlete.get("email", "")
print(f"[{athlete_id}] {name}" + (f" <{email}>" if email else ""))

# %%
metrics = client.get_metrics()
print(metrics)

# %%
trainings = client.get("planned/training/")

# %%
TARGET_DATE = "2026-07-15"
print(f"Fetching planned sessions for {TARGET_DATE}...")
sessions = client.get_daily_trainings(day=TARGET_DATE)

print("Raw sessions:")
pprint.pprint(sessions)

print(f"Found {len(sessions)} session(s).")
for session in sessions:
    name = session.get("name") or "(unnamed)"
    session_date = session.get("date_start") or session.get("date") or "unknown-date"
    sport_id = session.get("sport", "Unknown")
    print(f"- {session_date} | sport={sport_id} | {name}")

# %%
trainings = client.get_planned_trainings(start="2026-07-28", end="2026-10-31")

from pathlib import Path

data_dir = Path("./sandbox/data")
running_plan_path = data_dir / "ottawa_2024.json"
save_workouts(trainings, running_plan_path)

# %%
ftp_training_example = client.get_daily_trainings("2026-07-27")
save_workouts(ftp_training_example, data_dir / "ftp_example.json")

rpe_training_example = client.get_daily_trainings("2026-07-23")
save_workouts(rpe_training_example, data_dir / "rpe_example.json")
