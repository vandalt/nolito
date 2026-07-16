"""Manual script to verify OAuth and list planned sessions for today."""

from __future__ import annotations

from datetime import date

from nolito.client import NolioApiClient
from nolito.oauth import OAuthManager
from nolito.settings import NolitoSettings
from nolito.tokens import KeyringTokenStore


def main() -> None:
    settings = NolitoSettings.from_env()
    token_store = KeyringTokenStore.from_settings(settings)
    oauth = OAuthManager(settings=settings, token_store=token_store)
    client = NolioApiClient(settings=settings, oauth=oauth)

    today = date.today().isoformat()
    print(f"Fetching planned sessions for {today}...")
    sessions = client.get_planned_sessions_today()

    print(f"Found {len(sessions)} session(s).")
    for session in sessions:
        name = session.get("name") or "(unnamed)"
        session_date = session.get("date_start") or session.get("date") or "unknown-date"
        sport_id = session.get("sport_id", "unknown-sport")
        print(f"- {session_date} | sport={sport_id} | {name}")


if __name__ == "__main__":
    main()
