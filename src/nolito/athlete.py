from dataclasses import dataclass, field

from nolito.util import pace_to_str, speed_to_pace


@dataclass
class Athlete:
    id: int
    first_name: str
    last_name: str
    email: str | None = None
    birthday: str | None = field(default=None, repr=False)
    metrics: dict[str, dict[str, any]] | None = field(default=None, repr=False)

    def get_metric_value(self, metric: str) -> float:
        return self.metrics[metric]["data"]["value"]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def hrmax(self) -> float:
        return self.get_metric_value("hrmax")

    @property
    def ftp(self) -> float:
        return self.get_metric_value("ftp")

    @property
    def vo2max(self) -> float:
        return self.get_metric_value("vo2max")

    @property
    def aerobicspeed(self) -> float:
        return self.get_metric_value("aerobicspeed")

    def get_hr_zones(self):
        limits = {
            "1": (65.625, 79.6875),
            "2": (79.6875, 86.4583),
            "3": (86.4583, 93.2292),
            "4": (93.2292, 96.3542),
            "5": (96.3542, 100),
        }
        zones = {}
        for zone, (lo, hi) in limits.items():
            zones[zone] = tuple(
                float(round(x)) for x in (self.hrmax * lo / 100, self.hrmax * hi / 100)
            )
        return zones

    def get_speed_zones(self):
        limits = {
            "1": (47.87234042553191, 67.18924972004479),
            "2": (67.18924972004479, 76.90335811330427),
            "3": (76.90335811330427, 84.35654700534259),
            "4": (84.35654700534259, 91.1854103343465),
            "5": (91.1854103343465, 100.7838745800672),
        }
        zones = {}
        for zone, (lo, hi) in limits.items():
            zones[zone] = (self.aerobicspeed * lo / 100, self.aerobicspeed * hi / 100)
        return zones

    def get_pace_zones(self, fmt: str = "float"):
        speed_zones = self.get_speed_zones()
        zones = {}
        # TODO: Figure out exact format by looking at ottawa plan
        if fmt == "float":
            converter = speed_to_pace
        elif fmt == "str":
            converter = lambda x: pace_to_str(speed_to_pace(x))
        for zone, limits in speed_zones.items():
            zones[zone] = tuple(converter(x) for x in limits)
        return zones

    def get_power_zones(self):
        limits = {
            "1": (0, 55),
            "2": (55, 75),
            "3": (75, 90),
            "4": (90, 105),
            "5": (105, 120),
            "6": (120, 250),
            "7": (250, 500),
        }
        zones = {}
        for zone, (lo, hi) in limits.items():
            zones[zone] = tuple(round(self.ftp * lim / 100) for lim in [lo, hi])
        return zones
