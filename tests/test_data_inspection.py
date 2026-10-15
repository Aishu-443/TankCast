"""Tests for dataset inspection. All frames here are SYNTHETIC TEST FIXTURES built inside
the tests (column names mimic the documented Pune schema; the numbers are made up)."""
import pandas as pd
import pytest

from src import preprocessing as pp
from src.data_loader import DatasetNotFoundError, inspect_dataset, load_csv, main


def pune_like(days: int = 31) -> pd.DataFrame:
    dates = [f"{d:02d}-12-2016" for d in range(1, days + 1)]
    a = [100 + i for i in range(days)]
    b = [50 + i for i in range(days)]
    return pd.DataFrame({"Date": dates, "Parvati M.L.D": a, "Old Holkar M.L.D": b,
                         "Total M.L.D": [x + y for x, y in zip(a, b)]})


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(DatasetNotFoundError, match="data/raw|raw"):
        load_csv(tmp_path / "nope.csv")


def test_cli_without_data_exits_cleanly(tmp_path):
    assert main(["--path", str(tmp_path / "nope.csv")]) == 2


def test_day_first_dates_are_resolved_by_spacing():
    parsed, note = pp.parse_dates(pune_like()["Date"])
    assert parsed.min() == pd.Timestamp("2016-12-01")
    assert parsed.max() == pd.Timestamp("2016-12-31")
    assert note == ""


def test_pune_like_schema_detection():
    r = inspect_dataset(pune_like())
    assert r.date_column == "Date"
    assert r.frequency.label == "daily"
    assert r.target.column == "Total M.L.D"
    assert "MLD" in r.target.unit
    assert r.total_relationship is not None and r.total_relationship[0] == "Total M.L.D"
    assert r.exogenous["temperature"] == [] and r.exogenous["occupancy"] == []


def test_one_month_of_daily_data_is_not_suitable():
    r = inspect_dataset(pune_like())
    assert r.suitability == "not suitable"
    assert any("too few" in n for n in r.suitability_notes)


def test_long_daily_data_is_suitable():
    n = 200
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=n, freq="D"),
                       "consumption_litres": range(n)})
    r = inspect_dataset(df)
    assert r.suitability == "daily"
    assert r.target.column == "consumption_litres"


def test_hourly_frequency_detected():
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=24 * 40, freq="h"),
                       "demand_l": range(24 * 40)})
    r = inspect_dataset(df)
    assert r.frequency.label == "hourly"
    assert r.suitability == "hourly"


def test_unknown_unit_is_not_guessed():
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5), "water_use": [1, 2, 3, 4, 5]})
    r = inspect_dataset(df)
    assert r.target.column == "water_use"
    assert r.target.unit_source == "unknown"


def test_duplicate_timestamps_and_missing_values_reported():
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"],
                       "demand": [1.0, None, 3.0, 4.0]})
    r = inspect_dataset(df)
    assert r.duplicate_timestamps == 1
    assert int(r.columns.set_index("name").loc["demand", "missing"]) == 1


def test_no_target_found_is_reported_not_invented():
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5), "a": [1, 2, 3, 4, 5], "b": [5, 4, 3, 2, 1]})
    r = inspect_dataset(df)
    assert r.target.column is None
    assert not r.schema.ok


def test_bad_override_column_raises():
    with pytest.raises(pp.SchemaError):
        inspect_dataset(pune_like(), target_column="does_not_exist")
