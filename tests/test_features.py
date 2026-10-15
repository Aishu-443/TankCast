"""Tests for leakage-safe feature building and the chronological split.
All series here are SYNTHETIC TEST FIXTURES (random numbers), used only to check the logic."""
import numpy as np
import pandas as pd
import pytest

from src import preprocessing as pp


def make_series(n=24 * 30, seed=0):
    idx = pd.date_range("2024-01-01", periods=n, freq=pd.Timedelta(hours=1), name="timestamp")
    return pd.Series(np.random.default_rng(seed).uniform(50, 500, n), index=idx)


@pytest.mark.parametrize("horizon", [1, 6, 24, 30])
def test_no_future_leakage(horizon):
    """Changing the series from time t-horizon+1 onward must not change the features at t."""
    y = make_series()
    frame, names, _ = pp.build_supervised_frame(y, "hourly", horizon)
    t = frame.index[len(frame) // 2]
    pos = y.index.get_loc(t)
    tampered = y.copy()
    tampered.iloc[pos - horizon + 1:] = 1e9  # everything the forecaster could NOT know yet
    frame2, _, _ = pp.build_supervised_frame(tampered, "hourly", horizon)
    pd.testing.assert_series_equal(frame.loc[t, names].astype(float), frame2.loc[t, names].astype(float))
    assert frame.loc[t, "baseline_persistence"] == frame2.loc[t, "baseline_persistence"]
    assert frame.loc[t, "baseline_seasonal_naive"] == frame2.loc[t, "baseline_seasonal_naive"]


@pytest.mark.parametrize("horizon", [1, 24, 48])
def test_lags_are_never_shorter_than_horizon(horizon):
    _, names, _ = pp.build_supervised_frame(make_series(), "hourly", horizon)
    lags = [int(n.split("_")[1]) for n in names if n.startswith("lag_")]
    assert lags and min(lags) == horizon


def test_lag_and_rolling_values_are_correct():
    y = make_series()
    horizon = 24
    frame, _, _ = pp.build_supervised_frame(y, "hourly", horizon)
    t = frame.index[10]
    pos = y.index.get_loc(t)
    assert frame.loc[t, "lag_24"] == y.iloc[pos - 24]
    assert frame.loc[t, "lag_48"] == y.iloc[pos - 48]
    window = y.iloc[pos - horizon - 23: pos - horizon + 1]  # the 24 values ending at t-horizon
    assert np.isclose(frame.loc[t, "roll_mean_24"], window.mean())
    assert frame.loc[t, "target"] == y.iloc[pos]


def test_baselines():
    y = make_series()
    f1, _, info1 = pp.build_supervised_frame(y, "hourly", 1)
    t = f1.index[5]; pos = y.index.get_loc(t)
    assert f1.loc[t, "baseline_persistence"] == y.iloc[pos - 1]
    assert f1.loc[t, "baseline_seasonal_naive"] == y.iloc[pos - 24]
    assert info1["seasonal_lag_steps"] == 24
    _, _, info30 = pp.build_supervised_frame(y, "hourly", 30)
    assert info30["seasonal_lag_steps"] == 48  # smallest whole number of days >= 30 hours


def test_missing_values_are_dropped_not_filled():
    y = make_series()
    y.iloc[300:303] = np.nan
    frame, names, info = pp.build_supervised_frame(y, "hourly", 1)
    assert not frame.isna().any().any()
    assert info["rows_after"] < info["rows_before_dropping_missing"]
    assert y.index[300] not in frame.index  # a row whose target is missing is gone


def test_invalid_horizon():
    for bad in (0, -1, 1.5, "24"):
        with pytest.raises(ValueError):
            pp.build_supervised_frame(make_series(), "hourly", bad)


def test_chronological_split_never_overlaps():
    frame, _, _ = pp.build_supervised_frame(make_series(), "hourly", 24)
    train, test = pp.chronological_split(frame, 0.2)
    assert train.index.max() < test.index.min()
    assert len(train) + len(test) == len(frame)
    assert abs(len(test) / len(frame) - 0.2) < 0.01
    assert train.index.is_monotonic_increasing and test.index.is_monotonic_increasing


def test_split_rejects_bad_fraction():
    frame, _, _ = pp.build_supervised_frame(make_series(), "hourly", 24)
    for bad in (0, 0.5, 1, -0.1):
        with pytest.raises(ValueError):
            pp.chronological_split(frame, bad)


def test_regular_series_averages_duplicates_and_marks_gaps():
    df = pd.DataFrame({"timestamp": ["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 01:00", "2024-01-01 04:00"],
                       "demand": [10.0, 20.0, 40.0, 50.0]})
    s, info = pp.to_regular_series(df, "timestamp", "demand", "hourly")
    assert len(s) == 5
    assert s.iloc[1] == 30.0  # duplicate hour averaged
    assert s.iloc[2:4].isna().all()  # gap left empty, not invented
    assert info["n_missing_steps"] == 2 and info["n_duplicate_timestamps_averaged"] == 1


def test_off_grid_timestamps_are_rejected():
    df = pd.DataFrame({"timestamp": ["2024-01-01 00:00", "2024-01-01 01:30"], "demand": [1.0, 2.0]})
    with pytest.raises(pp.SchemaError):
        pp.to_regular_series(df, "timestamp", "demand", "hourly")
