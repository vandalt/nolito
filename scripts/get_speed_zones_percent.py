"""
Convert pace strings to speeds and then calculate their percentage of the aerobic speed
"""
from nolito import NolioApiClient
from nolito.util import pace_to_speed, str_to_pace

client = NolioApiClient()
athlete = client.get_athlete()

paces_nolio = [
    "6:40",
    "4:45",
    "4:09",
    "3:47",
    "3:30",
    "3:10",
]

speeds_nolio = [pace_to_speed(str_to_pace(x)) for x in paces_nolio]
print("Speeds")
print(speeds_nolio)
print("Percentages")
print([x / athlete.aerobicspeed for x in speeds_nolio])

print("Athlete paces")
print(athlete.get_pace_zones())
print(athlete.get_pace_zones(fmt="str"))
