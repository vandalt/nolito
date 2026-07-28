# %%
import pprint

# %%
from nolito.client import NolioApiClient
client = NolioApiClient()

# %%
athlete = client.get_athlete()
name = f"{athlete.get('first_name', '')} {athlete.get('last_name', '')}".strip() or "(unnamed)"
athlete_id = athlete.get("id", "?")
email = athlete.get("email", "")
print(f"[{athlete_id}] {name}" + (f" <{email}>" if email else ""))

# %%
meta = client.get("user/meta")
meta

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
