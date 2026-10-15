
from pathlib import Path

import joblib
import pandas as pd

from src import preprocessing as pp


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = PROJECT_ROOT / "models" / "tankcast_rf_reviewed_comparison.joblib"
FORECAST_HOURS = 24


def forecast_next_24_hours(data: pd.DataFrame,
                           model_path: str | Path = DEFAULT_MODEL) -> pd.DataFrame:
    """Forecast the next 24 hourly demand values from observed historical data."""

    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Input data must be a non-empty pandas DataFrame.")

    bundle = joblib.load(model_path)
    model = bundle["model"]
    feature_names = bundle["feature_names"]
    metadata = bundle["metadata"]

    if metadata.get("frequency") != "hourly":
        raise ValueError("This forecasting function requires an hourly model.")

    if metadata.get("horizon_steps") != FORECAST_HOURS:
        raise ValueError("The loaded model must have a 24-hour forecast horizon.")

    date_column = metadata["date_column"]
    target_column = metadata["target_column"]

    missing_columns = [
        col for col in (date_column, target_column) if col not in data.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Reuse the project's existing timestamp parsing and hourly-grid logic.
    
    series, _ = pp.to_regular_series(
        data, date_column, target_column, "hourly"
    )

    # Fill missing historical values from the same hour one week earlier.
    # Only fill a gap when that earlier observation is available.
    previous_week = series.shift(168)
    series = series.fillna(previous_week)


    last_observed = series.last_valid_index()
    if last_observed is None:
        raise ValueError("No valid historical demand readings were found.")

    # Forecast relative to the most recent actual reading.
    series = series.loc[:last_observed]

    future_index = pd.date_range(
        start=last_observed + pd.Timedelta(hours=1),
        periods=FORECAST_HOURS,
        freq="h",
    )

    # Future target values remain NaN. They are never used as actual readings.
    future_placeholders = pd.Series(index=future_index, dtype="float64")
    extended = pd.concat([series, future_placeholders])

    cfg = pp.FREQ_CONFIG["hourly"]
    horizon = FORECAST_HOURS
    past = extended.shift(horizon)

    columns = {}

    for lag in sorted({horizon} | {
        lag for lag in cfg["lags"] if lag >= horizon
    }):
        columns[f"lag_{lag}"] = extended.shift(lag)

    def required_values(window):
        return max(2, int(__import__("math").ceil(0.8 * window)))

    for window in cfg["windows"]:
        columns[f"roll_mean_{window}"] = past.rolling(
            window, min_periods=required_values(window)
        ).mean()

    short_window = cfg["windows"][0]
    columns[f"roll_std_{short_window}"] = past.rolling(
        short_window, min_periods=required_values(short_window)
    ).std()

    idx = extended.index
    columns["hour"] = idx.hour.to_numpy()
    columns["day_of_week"] = idx.dayofweek.to_numpy()
    columns["is_weekend"] = (idx.dayofweek >= 5).astype(int)
    columns["month"] = idx.month.to_numpy()

    features = pd.DataFrame(columns, index=idx)
    X = features.loc[future_index, feature_names]

    
    # Forecast only rows whose required features are available.
    valid_rows = X.notna().all(axis=1)
    predictions = pd.Series(float("nan"), index=future_index)

    if valid_rows.any():
        predictions.loc[valid_rows] = model.predict(X.loc[valid_rows])

    result = pd.DataFrame({
        "timestamp": future_index,
        "predicted_demand": predictions.to_numpy(),
        "status": [
            "forecast_available" if valid else "unavailable_missing_history"
            for valid in valid_rows
        ],
    })

    return result
