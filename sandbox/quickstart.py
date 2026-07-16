"""
This is a quickstart script provided by Nolio which I do not intent to use as-is but keep here for reference.
Ref: https://www.nolio.io/api/quickstart/
"""
import requests

# 1. Send the user to this URL. On approval, Nolio redirects to
#    your callback with ?code=YOUR_CODE
authorize_url = (
    "https://www.nolio.io/api/authorize/"
    "?response_type=code"
    "&client_id=7vvXmAwZtGeCIqLZkJR4POIRXRyK8GJT14losT5v"
    "&redirect_uri=YOUR_CALLBACK"
    "&state=RANDOM_STRING"
)

# 2. Exchange that code for an access token (HTTP Basic auth).
token = requests.post(
    "https://www.nolio.io/api/token/",
    auth=("7vvXmAwZtGeCIqLZkJR4POIRXRyK8GJT14losT5v", "YOUR_SECRET"),
    data={
        "grant_type": "authorization_code",
        "code": "YOUR_CODE",
        "redirect_uri": "YOUR_CALLBACK",
    },
).json()["access_token"]

# 3. First authenticated call.
user = requests.get(
    "https://www.nolio.io/api/get/user/",
    headers={"Authorization": f"Bearer {token}"},
).json()
print(user)
