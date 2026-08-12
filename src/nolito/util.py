def speed_to_pace(speed: float) -> float:
    if speed == 0.0:
        return 0.0
    return speed**-1 * 60


def pace_to_speed(pace: float) -> float:
    if pace == 0.0:
        return 0.0
    return pace**-1 * 60


def pace_to_str(pace: float) -> str:
    pace_min = int(pace)
    pace_sec = int(round((pace - pace_min) * 60, 2))
    return f"{pace_min}:{pace_sec:02}"


def str_to_pace(pace_str) -> float:
    pace_min, pace_sec = (int(x) for x in pace_str.split(":"))
    return pace_min + pace_sec / 60
