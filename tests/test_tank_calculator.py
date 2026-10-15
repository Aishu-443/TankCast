"""Tests for src/tank_calculator.py. The numbers below are TEST FIXTURES chosen so the
expected answer can be checked by hand; the app itself never hardcodes results."""
import math

import pytest

from src.tank_calculator import (
    EnduranceStatus, TankInputError, alert_level, available_litres, convert_to_litres_per_hour,
    estimate_endurance_constant, estimate_endurance_hourly, format_hours)


def test_available_litres():
    assert available_litres(5000, 40) == 2000
    assert available_litres(5000, 0) == 0
    assert available_litres(5000, 100) == 5000


@pytest.mark.parametrize("capacity, level", [
    (0, 50), (-100, 50), (float("nan"), 50), (float("inf"), 50), ("5000", 50), (True, 50),
    (1000, -1), (1000, 100.5), (1000, float("nan")), (1000, None),
])
def test_invalid_tank_inputs_raise(capacity, level):
    with pytest.raises(TankInputError):
        available_litres(capacity, level)


def test_unit_conversion():
    assert convert_to_litres_per_hour(24, "L/day") == 1
    assert convert_to_litres_per_hour(500, "L/hour") == 500
    assert math.isclose(convert_to_litres_per_hour(24, "m3/day"), 1000)
    assert math.isclose(convert_to_litres_per_hour(1, "MLD"), 1_000_000 / 24)


def test_unit_conversion_rejects_bad_input():
    with pytest.raises(TankInputError):
        convert_to_litres_per_hour(10, "gallons/week")
    with pytest.raises(TankInputError):
        convert_to_litres_per_hour(-5, "L/hour")


def test_constant_endurance_basic():
    r = estimate_endurance_constant(1000, 50, demand_lph=100)  # 500 L at 100 L/h
    assert r.status == EnduranceStatus.DEPLETES
    assert math.isclose(r.hours_until_empty, 5.0)


def test_constant_endurance_with_supply():
    r = estimate_endurance_constant(1000, 50, demand_lph=100, supply_lph=50)  # net loss 50 L/h
    assert math.isclose(r.hours_until_empty, 10.0)


@pytest.mark.parametrize("demand, supply", [(0, 0), (100, 100), (100, 150)])
def test_constant_endurance_never_depletes(demand, supply):
    r = estimate_endurance_constant(1000, 50, demand, supply)
    assert r.status == EnduranceStatus.NOT_DEPLETING
    assert r.hours_until_empty is None
    assert r.message  # an explanation must always be provided


def test_constant_endurance_empty_tank():
    r = estimate_endurance_constant(1000, 0, demand_lph=100)
    assert r.status == EnduranceStatus.EMPTY_NOW
    assert r.hours_until_empty == 0


def test_hourly_depletes_inside_interval():
    # 250 L; demand 100 L/h per hour -> empties 2.5 h from now, inside interval index 2
    r = estimate_endurance_hourly(1000, 25, [100, 100, 100, 100])
    assert r.status == EnduranceStatus.DEPLETES
    assert math.isclose(r.hours_until_empty, 2.5)
    assert r.depletion_interval == 2
    assert r.levels_litres == (150.0, 50.0, 0.0)


def test_hourly_with_changing_demand_and_supply():
    # 300 L. Hour 0: net 100 -> 200. Hour 1: net 250 -> empties at 1 + 200/250 = 1.8 h
    r = estimate_endurance_hourly(1000, 30, [150, 300, 50], supply_lph=50)
    assert math.isclose(r.hours_until_empty, 1.8)


def test_hourly_tank_cannot_exceed_capacity():
    # Supply exceeds demand in hour 0; tank is already full so it must stay at 1000 L.
    r = estimate_endurance_hourly(1000, 100, [0, 100], supply_lph=500)
    assert r.levels_litres[0] == 1000
    assert r.status == EnduranceStatus.BEYOND_FORECAST


def test_hourly_beyond_forecast():
    r = estimate_endurance_hourly(1000, 100, [10, 10, 10])
    assert r.status == EnduranceStatus.BEYOND_FORECAST
    assert r.hours_until_empty is None
    assert "cannot be calculated" in r.message


def test_hourly_interval_length():
    # 30-minute intervals: 100 L, 400 L/h -> 200 L per interval -> empties after 0.25 h
    r = estimate_endurance_hourly(1000, 10, [400, 400], interval_hours=0.5)
    assert math.isclose(r.hours_until_empty, 0.25)


@pytest.mark.parametrize("forecast", [[], [10, -5], [10, float("nan")], [10, "x"]])
def test_hourly_invalid_forecast(forecast):
    with pytest.raises(TankInputError):
        estimate_endurance_hourly(1000, 50, forecast)


def test_alert_levels():
    assert alert_level(80) == "ok"
    assert alert_level(30) == "ok"
    assert alert_level(29.9) == "warning"
    assert alert_level(14.9) == "critical"
    with pytest.raises(TankInputError):
        alert_level(120)


def test_format_hours():
    assert format_hours(2.5) == "2 h 30 min"
    assert format_hours(0.25) == "15 min"
