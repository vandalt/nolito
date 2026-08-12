import pytest

from nolito.athlete import Athlete


def test_full_name(athlete: Athlete):
    assert athlete.full_name == "Ada Lovelace"


def test_metric_values_and_properties(athlete: Athlete):
    assert athlete.get_metric_value("ftp") == 200
    assert athlete.hrmax == 200
    assert athlete.ftp == 200
    assert athlete.vo2max == 55
    assert athlete.aerobicspeed == 15


def test_hr_zones(athlete: Athlete):
    assert athlete.get_hr_zones() == {
        "1": (131.0, 159.0),
        "2": (159.0, 173.0),
        "3": (173.0, 186.0),
        "4": (186.0, 193.0),
        "5": (193.0, 200.0),
    }


def test_power_zones(athlete: Athlete):
    assert athlete.get_power_zones() == {
        "1": (0, 110),
        "2": (110, 150),
        "3": (150, 180),
        "4": (180, 210),
        "5": (210, 240),
        "6": (240, 500),
        "7": (500, 1000),
    }


def test_speed_zones(athlete: Athlete):
    expected = {
        "1": (7.180851063829786, 10.078387458006718),
        "2": (10.078387458006718, 11.53550371699564),
        "3": (11.53550371699564, 12.653482050801388),
        "4": (12.653482050801388, 13.677811550151976),
        "5": (13.677811550151976, 15.11758118701008),
    }

    for zone, limits in expected.items():
        assert athlete.get_speed_zones()[zone] == pytest.approx(limits)


def test_float_pace_zones(athlete: Athlete):
    expected = {
        "1": (8.355555555555556, 5.953333333333333),
        "2": (5.953333333333333, 5.201333333333334),
        "3": (5.201333333333334, 4.741777777777777),
        "4": (4.741777777777777, 4.386666666666667),
        "5": (4.386666666666667, 3.968888888888888),
    }

    for zone, limits in expected.items():
        assert athlete.get_pace_zones()[zone] == pytest.approx(limits)


def test_string_pace_zones(athlete: Athlete):
    assert athlete.get_pace_zones(fmt="str") == {
        "1": ("8:21", "5:57"),
        "2": ("5:57", "5:12"),
        "3": ("5:12", "4:44"),
        "4": ("4:44", "4:23"),
        "5": ("4:23", "3:58"),
    }
