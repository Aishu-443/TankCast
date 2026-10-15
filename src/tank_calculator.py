"""Tank water-balance logic for TANKCAST.

This module is pure Python: it does not import Streamlit, pandas or any ML
library, so it can be tested and explained on its own.

Core idea (a simple water balance, per time interval):

    new_level = old_level - (demand - supply) * interval_hours

capped between 0 (empty) and tank capacity (full / overflowing).

All rates are in LITRES PER HOUR internally. Use `convert_to_litres_per_hour`
to bring other units into that form first.
"""
from __future__ import annotations

import math
import numbers
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

# Multiply a value in the given unit by this factor to get litres per hour.
# NOTE: this is only a UNIT conversion. It does NOT scale a city's demand
# (e.g. Pune in MLD) down to a hostel's demand -- that would need explicit
# population/occupancy assumptions.
UNIT_TO_LITRES_PER_HOUR: dict[str, float] = {
    "L/hour": 1.0,
    "L/day": 1.0 / 24.0,
    "m3/day": 1000.0 / 24.0,
    "MLD": 1_000_000.0 / 24.0,  # million litres per day
}


class TankInputError(ValueError):
    """Raised when a tank input is missing, non-numeric, or physically impossible."""


class EnduranceStatus(str, Enum):
    DEPLETES = "depletes"              # tank runs empty at a calculated time
    EMPTY_NOW = "empty_now"            # tank already has 0 litres
    NOT_DEPLETING = "not_depleting"    # supply >= demand (or demand is zero)
    BEYOND_FORECAST = "beyond_forecast"  # not empty by the end of the forecast


@dataclass(frozen=True)
class EnduranceResult:
    status: EnduranceStatus
    available_litres: float
    hours_until_empty: Optional[float]  # None unless status == DEPLETES (or 0 if EMPTY_NOW)
    message: str                        # plain-English explanation for the UI
    depletion_interval: Optional[int] = None  # 0-based forecast interval (hourly mode only)
    levels_litres: tuple[float, ...] = ()     # litres at the END of each interval (hourly mode)


# ----------------------------------------------------------------------------
# Validation helpers
# ----------------------------------------------------------------------------
def _as_number(name: str, value: object) -> float:
    """Return value as a finite float, or raise TankInputError."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TankInputError(f"{name} must be a number, got {value!r}.")
    value = float(value)
    if not math.isfinite(value):
        raise TankInputError(f"{name} must be a finite number, got {value}.")
    return value


def _non_negative(name: str, value: object) -> float:
    number = _as_number(name, value)
    if number < 0:
        raise TankInputError(f"{name} cannot be negative (got {number}).")
    return number


def _validate_tank(capacity_litres: object, level_percent: object) -> tuple[float, float]:
    capacity = _as_number("Tank capacity", capacity_litres)
    if capacity <= 0:
        raise TankInputError(f"Tank capacity must be greater than 0 litres (got {capacity}).")
    level = _as_number("Tank level", level_percent)
    if not 0 <= level <= 100:
        raise TankInputError(f"Tank level must be between 0 and 100 percent (got {level}).")
    return capacity, level


# ----------------------------------------------------------------------------
# Public functions
# ----------------------------------------------------------------------------
def convert_to_litres_per_hour(value: object, unit: str) -> float:
    """Convert a demand/supply rate in `unit` to litres per hour."""
    if unit not in UNIT_TO_LITRES_PER_HOUR:
        supported = ", ".join(UNIT_TO_LITRES_PER_HOUR)
        raise TankInputError(f"Unsupported unit {unit!r}. Supported units: {supported}.")
    return _non_negative("Rate", value) * UNIT_TO_LITRES_PER_HOUR[unit]


def available_litres(capacity_litres: float, level_percent: float) -> float:
    """Litres currently in the tank."""
    capacity, level = _validate_tank(capacity_litres, level_percent)
    return capacity * level / 100.0


def alert_level(level_percent: float, warning_below: float = 30.0,
                critical_below: float = 15.0) -> str:
    """Return 'ok', 'warning' or 'critical'.

    The 30% / 15% thresholds are adjustable defaults chosen for this prototype,
    not an engineering standard.
    """
    level = _as_number("Tank level", level_percent)
    if not 0 <= level <= 100:
        raise TankInputError(f"Tank level must be between 0 and 100 percent (got {level}).")
    if not 0 <= critical_below <= warning_below <= 100:
        raise TankInputError("Thresholds must satisfy 0 <= critical <= warning <= 100.")
    if level < critical_below:
        return "critical"
    if level < warning_below:
        return "warning"
    return "ok"


def format_hours(hours: float) -> str:
    """Turn 2.5 into '2 h 30 min' for display."""
    total_minutes = int(round(hours * 60))
    h, m = divmod(total_minutes, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def estimate_endurance_constant(capacity_litres: float, level_percent: float,
                                demand_lph: float, supply_lph: float = 0.0) -> EnduranceResult:
    """How long the tank lasts if demand and supply stay constant (litres/hour)."""
    capacity, level = _validate_tank(capacity_litres, level_percent)
    demand = _non_negative("Demand", demand_lph)
    supply = _non_negative("Supply", supply_lph)
    litres = capacity * level / 100.0

    if litres == 0:
        return EnduranceResult(EnduranceStatus.EMPTY_NOW, litres, 0.0, "The tank is already empty.")

    net_outflow = demand - supply  # litres lost per hour (negative => tank fills)
    if net_outflow <= 0:
        reason = "Demand is zero" if demand == 0 else "Incoming supply is at least as large as demand"
        return EnduranceResult(
            EnduranceStatus.NOT_DEPLETING, litres, None,
            f"{reason}, so the tank is not expected to run empty at these constant rates.")

    hours = litres / net_outflow
    return EnduranceResult(
        EnduranceStatus.DEPLETES, litres, hours,
        f"At a net loss of {net_outflow:.1f} L/hour, {litres:.0f} L lasts about {format_hours(hours)}.")


def estimate_endurance_hourly(capacity_litres: float, level_percent: float,
                              forecast_lph: Sequence[float], supply_lph: float = 0.0,
                              interval_hours: float = 1.0) -> EnduranceResult:
    """Walk through a forecast interval by interval and find when the tank empties.

    `forecast_lph` is the demand for each interval in litres/hour. Supply is
    assumed constant. If the tank is not empty at the end of the forecast the
    result says so instead of guessing beyond the data.
    """
    capacity, level_pct = _validate_tank(capacity_litres, level_percent)
    supply = _non_negative("Supply", supply_lph)
    step = _as_number("Interval length", interval_hours)
    if step <= 0:
        raise TankInputError("Interval length must be greater than 0 hours.")
    if len(forecast_lph) == 0:
        raise TankInputError("The demand forecast is empty; nothing to simulate.")
    demands = [_non_negative(f"Forecast demand [{i}]", d) for i, d in enumerate(forecast_lph)]

    level = capacity * level_pct / 100.0
    start_litres = level
    if level == 0:
        return EnduranceResult(EnduranceStatus.EMPTY_NOW, 0.0, 0.0, "The tank is already empty.")

    levels: list[float] = []
    for i, demand in enumerate(demands):
        net_rate = demand - supply  # litres per hour lost in this interval
        if net_rate > 0 and level - net_rate * step <= 0:
            # Empties inside this interval: time = hours elapsed + level / loss rate.
            hours = i * step + level / net_rate
            levels.append(0.0)
            return EnduranceResult(
                EnduranceStatus.DEPLETES, start_litres, hours,
                f"Forecast shows the tank running empty about {format_hours(hours)} from now.",
                depletion_interval=i, levels_litres=tuple(levels))
        level = min(capacity, level - net_rate * step)  # a full tank cannot hold more
        levels.append(level)

    horizon = len(demands) * step
    return EnduranceResult(
        EnduranceStatus.BEYOND_FORECAST, start_litres, None,
        f"The tank is not empty by the end of the {horizon:g}-hour forecast "
        f"({level:.0f} L left), so the depletion time cannot be calculated from this forecast.",
        levels_litres=tuple(levels))
