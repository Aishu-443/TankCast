"""Schema detection and validation for TANKCAST (Phase 1).

Everything here only LOOKS at the data and reports what it finds. Heuristics
(guessing the date column, target column, units) are labelled as guesses and
can be overridden from the command line. Feature engineering and model-ready
cleaning arrive in Phase 2.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_object_dtype, is_string_dtype

DATE_NAME_HINTS = ("date", "time", "timestamp", "datetime", "day")
TARGET_KEYWORDS = ("consumption", "demand", "usage", "water", "volume",
                   "litre", "liter", "flow", "mld", "cons")
# Columns that would be useful model inputs IF (and only if) they exist.
EXOGENOUS_KEYWORDS = {
    "temperature": ("temp",),
    "occupancy": ("occupan", "resident", "headcount", "students", "inmates"),
}


class SchemaError(ValueError):
    """The data does not have the structure we need."""


def _norm(name: object) -> str:
    """'Total M.L.D' -> 'totalmld' (lowercase letters/digits only)."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


# ----------------------------------------------------------------------------
# Dates
# ----------------------------------------------------------------------------
def parse_dates(series: pd.Series) -> tuple[pd.Series, str]:
    """Parse text to datetimes. Returns (parsed, note).

    Dates like 03-04-2017 are ambiguous (3 April or 4 March?). We try both
    readings and keep the one that gives the most REGULAR spacing, because real
    daily/hourly data has one dominant step between rows. `note` is non-empty
    only when we could not decide.
    """
    if is_datetime64_any_dtype(series):
        return series, ""
    readings: dict[bool, pd.Series] = {}
    for dayfirst in (False, True):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            readings[dayfirst] = pd.to_datetime(series, errors="coerce", dayfirst=dayfirst, format="mixed")

    def score(parsed: pd.Series) -> tuple[int, int]:
        steps = parsed.dropna().sort_values().diff().dropna()
        modal_count = int(steps.value_counts().iloc[0]) if len(steps) else 0
        return int(parsed.notna().sum()), modal_count

    month_first, day_first = readings[False], readings[True]
    if month_first.equals(day_first):  # unambiguous (e.g. ISO 2017-03-04)
        return month_first, ""
    s_month, s_day = score(month_first), score(day_first)
    if s_month != s_day:
        return (month_first, "") if s_month > s_day else (day_first, "")
    return day_first, ("Date order (day-first vs month-first) is ambiguous; assumed day-first "
                       "(common in India). Check the parsed range below.")


def find_date_column(df: pd.DataFrame) -> Optional[str]:
    """Pick the column that looks like a timestamp, or None."""
    for col in df.columns:
        if is_datetime64_any_dtype(df[col]):
            return col
    text_cols = [c for c in df.columns if is_string_dtype(df[c]) or is_object_dtype(df[c])]
    hinted = [c for c in text_cols if any(h in str(c).lower() for h in DATE_NAME_HINTS)]
    for col in hinted + [c for c in text_cols if c not in hinted]:
        values = df[col].dropna()
        if values.nunique() < 2:
            continue
        parsed, _ = parse_dates(values)
        if parsed.notna().mean() >= 0.9:  # at least 90% of entries must parse as dates
            return col
    return None


# ----------------------------------------------------------------------------
# Frequency
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class FrequencyInfo:
    label: str                       # hourly / daily / weekly / monthly / irregular / unknown
    median_step: Optional[pd.Timedelta]
    regular_fraction: float          # share of steps equal to the median step
    n_gaps: int                      # steps much larger than the median (missing periods)


def infer_frequency(timestamps: pd.Series) -> FrequencyInfo:
    """Classify the sampling interval from the unique, sorted timestamps."""
    unique = timestamps.dropna().drop_duplicates().sort_values()
    steps = unique.diff().dropna()
    if steps.empty:
        return FrequencyInfo("unknown", None, 0.0, 0)
    median = steps.median()
    hours = median / pd.Timedelta(hours=1)
    if 0.5 <= hours <= 1.5:
        label = "hourly"
    elif 20 <= hours <= 28:
        label = "daily"
    elif 6 * 24 <= hours <= 8 * 24:
        label = "weekly"
    elif 27 * 24 <= hours <= 32 * 24:
        label = "monthly"
    else:
        label = "irregular"
    return FrequencyInfo(label, median, float((steps == median).mean()), int((steps > 1.5 * median).sum()))


# ----------------------------------------------------------------------------
# Target and units
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class TargetInfo:
    column: Optional[str]
    unit: str               # human-readable
    unit_source: str        # "inferred from column name" or "unknown"
    reason: str
    other_candidates: tuple[str, ...] = ()


def guess_unit(column: str) -> tuple[str, str]:
    """Guess a unit from a column NAME only. Returns (unit, how_we_know)."""
    n = _norm(column)
    if "mld" in n:
        return "MLD (million litres per day)", "inferred from column name"
    if "kld" in n:
        return "kL/day (kilolitres per day)", "inferred from column name"
    if "litre" in n or "liter" in n:
        return "litres (time period not stated in name)", "inferred from column name"
    if "m3" in n:
        return "cubic metres (time period not stated in name)", "inferred from column name"
    return "unknown - confirm from the dataset documentation", "unknown"


def guess_target(df: pd.DataFrame, date_column: Optional[str], override: Optional[str] = None) -> TargetInfo:
    """Find the most likely demand column. Never invents one."""
    if override is not None:
        if override not in df.columns:
            raise SchemaError(f"Target column {override!r} not found. Columns: {list(df.columns)}")
        unit, source = guess_unit(override)
        return TargetInfo(override, unit, source, "chosen by the user")

    numeric = [c for c in df.select_dtypes("number").columns if c != date_column]
    scored: list[tuple[int, str]] = []
    for col in numeric:
        n = _norm(col)
        if n in ("id", "index") or n.endswith("id"):
            continue
        score = sum(k in n for k in TARGET_KEYWORDS)
        if score and "total" in n:
            score += 2  # prefer an overall total over a single zone
        if score:
            scored.append((score, col))
    scored.sort(key=lambda t: -t[0])

    if scored:
        best = scored[0][1]
        unit, source = guess_unit(best)
        return TargetInfo(best, unit, source, "column name looks like water demand",
                          tuple(c for _, c in scored[1:]))
    if len(numeric) == 1:
        unit, source = guess_unit(numeric[0])
        return TargetInfo(numeric[0], unit, source, "only numeric column in the file")
    return TargetInfo(None, "unknown", "unknown",
                      "no column name looks like water demand; pass --target-column")


def detect_total_relationship(df: pd.DataFrame, date_column: Optional[str]) -> Optional[tuple[str, list[str]]]:
    """Detect a 'Total' column that is (roughly) the sum of the other numeric columns.

    Why it matters: if Total = zone1 + zone2 + ..., then using same-day zone
    values to predict Total is data leakage (the answer is built from them).
    """
    numeric = [c for c in df.select_dtypes("number").columns if c != date_column]
    for total in (c for c in numeric if any(w in _norm(c) for w in ("total", "overall", "sum"))):
        parts = [c for c in numeric if c != total]
        if len(parts) < 2:
            continue
        reference = df[total]
        valid = reference > 0
        if valid.sum() < 3:
            continue
        rel_err = ((df.loc[valid, parts].sum(axis=1) - reference[valid]).abs() / reference[valid]).median()
        if rel_err < 0.05:  # within 5% on the median row
            return total, parts
    return None


def detect_exogenous_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    """Which temperature/occupancy-like columns exist? Empty list = not available."""
    found: dict[str, list[str]] = {}
    for label, keywords in EXOGENOUS_KEYWORDS.items():
        found[label] = [c for c in df.columns if any(k in _norm(c) for k in keywords)]
    return found


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------
@dataclass
class SchemaCheck:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_invalid(self) -> None:
        if self.errors:
            raise SchemaError("; ".join(self.errors))


def validate_schema(df: pd.DataFrame, date_column: Optional[str], target_column: Optional[str]) -> SchemaCheck:
    """Check that the data is usable for time-series forecasting."""
    check = SchemaCheck()
    if df.empty:
        check.errors.append("The dataset has no rows.")
        return check
    if date_column is None or date_column not in df.columns:
        check.errors.append("No date/time column found; cannot do time-series forecasting.")
    if target_column is None or target_column not in df.columns:
        check.errors.append("No target (water demand) column identified.")
    if check.errors:
        return check

    target = df[target_column]
    if not pd.api.types.is_numeric_dtype(target):
        check.errors.append(f"Target column {target_column!r} is not numeric (dtype: {target.dtype}).")
    else:
        if target.isna().all():
            check.errors.append(f"Target column {target_column!r} is entirely missing.")
        if (target < 0).any():
            check.errors.append(f"Target column {target_column!r} contains negative values.")
        if target.isna().any():
            check.warnings.append(f"Target has {int(target.isna().sum())} missing value(s); they need handling before training.")
        if target.nunique() <= 1:
            check.warnings.append("Target is constant; a model cannot learn anything from it.")

    parsed, note = parse_dates(df[date_column])
    if parsed.isna().mean() > 0.1:
        check.errors.append(f"{int(parsed.isna().sum())} of {len(df)} values in {date_column!r} could not be parsed as dates.")
    if note:
        check.warnings.append(note)
    if parsed.dropna().duplicated().any():
        check.warnings.append("Duplicate timestamps present (several rows per time).")
    return check


# ============================================================================
# Phase 2: regular series, leakage-safe features, chronological split
# ============================================================================
import math

import numpy as np

# Per-frequency settings. "season" is the natural repeat length (24 hours / 7 days).
FREQ_CONFIG = {
    "hourly": {"step": pd.Timedelta(hours=1), "lags": (1, 2, 3, 24, 48, 168), "windows": (24, 168), "season": 24},
    "daily": {"step": pd.Timedelta(days=1), "lags": (1, 2, 7, 14), "windows": (7, 28), "season": 7},
}


def to_regular_series(df: pd.DataFrame, date_column: str, target_column: str,
                      freq_label: str) -> tuple[pd.Series, dict]:
    """Turn a table into a series on a complete, regular time grid.

    - Duplicate timestamps (e.g. the repeated hour when clocks go back) are averaged.
    - Missing time steps become NaN. They are NOT filled in or interpolated:
      inventing demand values would make the model look better than it is.
    """
    if freq_label not in FREQ_CONFIG:
        raise SchemaError(f"Unsupported frequency {freq_label!r}; supported: {list(FREQ_CONFIG)}")
    step = FREQ_CONFIG[freq_label]["step"]
    parsed, _ = parse_dates(df[date_column])
    values = pd.to_numeric(df[target_column], errors="coerce").to_numpy()
    series = pd.Series(values, index=pd.DatetimeIndex(parsed)).sort_index()
    series = series[series.index.notna()]
    n_duplicates = int(series.index.duplicated().sum())
    series = series.groupby(level=0).mean()

    if ((series.index - series.index.min()) % step != pd.Timedelta(0)).any():
        raise SchemaError(f"Timestamps are not aligned to a regular {freq_label} grid; resample the data first.")
    full_index = pd.date_range(series.index.min(), series.index.max(), freq=step)
    series = series.reindex(full_index)
    series.index.name = "timestamp"
    return series, {"n_steps": len(series), "n_missing_steps": int(series.isna().sum()),
                    "n_duplicate_timestamps_averaged": n_duplicates}


def build_supervised_frame(series: pd.Series, freq_label: str,
                           horizon: int) -> tuple[pd.DataFrame, list[str], dict]:
    """Build model inputs for predicting the value `horizon` steps after the information cut-off.

    LEAKAGE RULE: the row for time t may only use values of the series at or before t - horizon,
    because that is all we would know when making the forecast. So:
      * every lag is at least `horizon` steps back;
      * rolling statistics are computed on the series shifted by `horizon` first;
      * calendar features (hour, weekday, ...) describe time t itself, which is known in advance.
    Rows still missing an exact lag value (or too much of a rolling window) are dropped, never imputed.
    """
    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError(f"horizon must be a whole number >= 1 (got {horizon!r}).")
    cfg = FREQ_CONFIG[freq_label]
    past = series.shift(horizon)  # the newest information available at forecast time

    cols: dict[str, object] = {}
    for lag in sorted({horizon} | {l for l in cfg["lags"] if l >= horizon}):
        cols[f"lag_{lag}"] = series.shift(lag)
    # Rolling statistics use the values actually observed in the window (at least 80% of it), so a
    # few missing hours do not wipe out hundreds of rows. This is not imputation: nothing is invented.
    def need(window: int) -> int:
        return max(2, math.ceil(0.8 * window))

    for window in cfg["windows"]:
        cols[f"roll_mean_{window}"] = past.rolling(window, min_periods=need(window)).mean()
    short = cfg["windows"][0]
    cols[f"roll_std_{short}"] = past.rolling(short, min_periods=need(short)).std()

    idx = series.index
    if freq_label == "hourly":
        cols["hour"] = idx.hour.to_numpy()
    cols["day_of_week"] = idx.dayofweek.to_numpy()
    cols["is_weekend"] = (idx.dayofweek >= 5).astype(int)
    cols["month"] = idx.month.to_numpy()
    features = pd.DataFrame(cols, index=idx)
    feature_names = list(features.columns)

    # Baselines are also built only from the past. Persistence = "same as `horizon` steps ago".
    # Seasonal naive = "same time in the previous cycle" (e.g. same hour yesterday), using the
    # smallest whole number of cycles that is at least `horizon` back.
    seasonal_lag = cfg["season"] * math.ceil(horizon / cfg["season"])
    frame = features.copy()
    frame["target"] = series
    frame["baseline_persistence"] = series.shift(horizon)
    frame["baseline_seasonal_naive"] = series.shift(seasonal_lag)
    rows_before = len(frame)
    frame = frame.dropna()
    return frame, feature_names, {"rows_before_dropping_missing": rows_before, "rows_after": len(frame),
                                  "seasonal_lag_steps": seasonal_lag}


def chronological_split(frame: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Oldest rows -> train, newest rows -> test. Never shuffled."""
    if not 0 < test_fraction < 0.5:
        raise ValueError(f"test_fraction must be between 0 and 0.5 (got {test_fraction}).")
    frame = frame.sort_index()
    cut = int(len(frame) * (1 - test_fraction))
    train, test = frame.iloc[:cut], frame.iloc[cut:]
    if train.empty or test.empty:
        raise ValueError("Not enough rows to make both a training and a test period.")
    assert train.index.max() < test.index.min(), "train/test periods overlap"
    return train, test
