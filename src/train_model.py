"""Train and evaluate the TANKCAST demand model.

Train (reproducible; the random seed is fixed):
    python -m src.train_model --data data/processed/hourly_water_demand.csv --horizon 24

Check a saved model reproduces its own reported numbers:
    python -m src.train_model --verify models/<name>.joblib

What the horizon means: with --horizon 24 the model forecasts each hour using only information that is
at least 24 hours old. One model therefore covers every hour of the next day, with no feeding of
predictions back into the model. --horizon 1 means "next hour".

Evaluation: the NEWEST part of the data (default 20%) is held out as a test period. The model never
sees it during training. Hyper-parameters are fixed in advance, not tuned on the test period.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor

from src import preprocessing as pp
from src.data_loader import PROJECT_ROOT, DatasetNotFoundError, inspect_dataset, load_csv

MODEL_DIR = PROJECT_ROOT / "models"
MIN_USABLE_ROWS = 500          # rows left after building features; prototype rule of thumb
MAX_MISSING_FRACTION = 0.30    # refuse if more than 30% of time steps have no value
MAX_DUPLICATE_FRACTION = 0.01  # many duplicate timestamps suggest several series stacked together
RF_PARAMS = {"n_estimators": 200, "min_samples_leaf": 3, "random_state": 42, "n_jobs": -1}

METRIC_EXPLANATION = {
    "MAE": "Mean Absolute Error: the average size of the forecast error, in the target's own unit. Easy to read.",
    "RMSE": "Root Mean Squared Error: like MAE but squares errors first, so rare large misses count more. "
            "RMSE is always >= MAE; a big gap between them means occasional large errors.",
    "persistence": "Baseline: predicts that demand equals its value `horizon` steps earlier (at a 24-hour horizon "
                   "this is simply 'same hour yesterday').",
    "seasonal_naive": "Baseline: predicts the value from the same time in the previous cycle (e.g. same hour yesterday).",
}


class TrainingDataError(ValueError):
    """The data is not suitable for training; the message says why."""


def mae(actual, predicted) -> float:
    return float(np.mean(np.abs(np.asarray(actual, float) - np.asarray(predicted, float))))


def rmse(actual, predicted) -> float:
    return float(np.sqrt(np.mean((np.asarray(actual, float) - np.asarray(predicted, float)) ** 2)))


def _scores(actual, predicted) -> dict:
    return {"mae": mae(actual, predicted), "rmse": rmse(actual, predicted)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def read_sidecar(data_path: Path) -> dict:
    """Metadata written next to the CSV (units, source, synthetic flag), if any."""
    side = data_path.with_suffix(".meta.json")
    return json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}


def prepare_data(df: pd.DataFrame, date_column: str, target_column: str, frequency: str,
                 horizon: int, test_fraction: float):
    """Shared by training and verification so both rebuild exactly the same rows."""
    series, series_info = pp.to_regular_series(df, date_column, target_column, frequency)
    if series.isna().mean() > MAX_MISSING_FRACTION:
        raise TrainingDataError(f"{series.isna().mean():.0%} of time steps have no value (limit {MAX_MISSING_FRACTION:.0%}).")
    frame, features, frame_info = pp.build_supervised_frame(series, frequency, horizon)
    if len(frame) < MIN_USABLE_ROWS:
        raise TrainingDataError(f"Only {len(frame)} usable rows after building features (need >= {MIN_USABLE_ROWS}).")
    train, test = pp.chronological_split(frame, test_fraction)
    return series_info, frame_info, features, train, test


def train(data_path: Path | str, horizon: int = 24, test_fraction: float = 0.2,
          date_column: Optional[str] = None, target_column: Optional[str] = None,
          unit: Optional[str] = None, model_dir: Path | str = MODEL_DIR,
          model_name: Optional[str] = None) -> dict:
    data_path = Path(data_path)
    df = load_csv(data_path)
    side = read_sidecar(data_path)

    # --- 1. Validate before training: schema, target, frequency, size, units ---------------------
    report = inspect_dataset(df, data_path, date_column or side.get("date_column"),
                             target_column or side.get("target_column"))
    report.schema.raise_if_invalid()
    if report.suitability == "not suitable":
        raise TrainingDataError("Dataset is not suitable for training: " + " ".join(report.suitability_notes))
    if report.duplicate_timestamps > MAX_DUPLICATE_FRACTION * report.n_rows:
        raise TrainingDataError(f"{report.duplicate_timestamps} duplicate timestamps: this looks like several series "
                                "stacked together. Aggregate to one series first (e.g. src.prepare_meter_data).")
    unit = unit or side.get("unit")
    if not unit:
        raise TrainingDataError("The target's unit is unknown. Pass --unit 'litres per hour' (or write it in "
                                "<file>.meta.json). Units are never guessed for training.")
    frequency = report.suitability  # "hourly" or "daily"

    series_info, frame_info, features, train_df, test_df = prepare_data(
        df, report.date_column, report.target.column, frequency, horizon, test_fraction)

    # --- 2. Fit on the training period only ------------------------------------------------------
    model = RandomForestRegressor(**RF_PARAMS)
    model.fit(train_df[features], train_df["target"])

    # --- 3. Evaluate on the untouched test period, against baselines on the SAME rows ------------
    # If the seasonal lag equals the horizon (e.g. 24h ahead, same hour yesterday), the two baselines are the
    # same predictor, so only one is reported.
    baselines = ["persistence"] if frame_info["seasonal_lag_steps"] == horizon else ["persistence", "seasonal_naive"]
    predictions = pd.DataFrame({"actual": test_df["target"], "random_forest": model.predict(test_df[features])},
                               index=test_df.index)
    for b in baselines:
        predictions[b] = test_df["baseline_persistence" if b == "persistence" else "baseline_seasonal_naive"]
    metrics = {name: _scores(predictions["actual"], predictions[name]) for name in ["random_forest"] + baselines}
    best_baseline = min(baselines, key=lambda n: metrics[n]["mae"])
    improvement = 100 * (metrics[best_baseline]["mae"] - metrics["random_forest"]["mae"]) / metrics[best_baseline]["mae"]

    is_synthetic = bool(side.get("is_synthetic", False))
    metadata = {
        "model_type": "RandomForestRegressor",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_path": _relative(data_path),
        "data_sha256": _sha256(data_path),
        "data_status": side.get("data_status", "USER-SUPPLIED DATA (status not declared)"),
        "is_synthetic": is_synthetic,
        "source": side.get("source", "not declared"),
        "target_column": report.target.column,
        "date_column": report.date_column,
        "target_unit": unit,
        "frequency": frequency,
        "horizon_steps": horizon,
        "test_fraction": test_fraction,
        "feature_names": features,
        "feature_policy": "Calendar features for the forecast time plus lags/rolling statistics of the target that are "
                          "at least `horizon` steps old. No temperature or occupancy features are used.",
        "exogenous_features_used": [],
        "exogenous_columns_found_in_data": report.exogenous,
        "preprocessing": {"missing_policy": "missing time steps are left empty; rows lacking any needed history are dropped (no imputation)",
                          "duplicate_timestamp_policy": "averaged", **series_info, **frame_info},
        "split": {"method": "chronological (no shuffling)",
                  "train_start": str(train_df.index.min()), "train_end": str(train_df.index.max()),
                  "test_start": str(test_df.index.min()), "test_end": str(test_df.index.max()),
                  "n_train": len(train_df), "n_test": len(test_df)},
        "hyperparameters": RF_PARAMS,
        "metrics": metrics,
        "mean_test_target": float(predictions["actual"].mean()),
        "best_baseline": best_baseline,
        "mae_improvement_over_best_baseline_pct": float(improvement),
        "baselines_reported": baselines,
        "random_forest_beats_all_baselines": bool(all(
            metrics["random_forest"]["mae"] < metrics[b]["mae"] for b in baselines)),
        "metric_explanation": METRIC_EXPLANATION,
        "dataset_limitations": side.get("limitations", []),
        "limitations": [
            "Metrics come from ONE chronological test period; they say little about other seasons or conditions.",
            "The test period was not used for tuning, but only fixed hyper-parameters were tried.",
            "Predictions are in the dataset's unit and scale; they are not hostel demand unless the data is.",
        ] + (["SYNTHETIC DEMO DATA: these metrics only show the code runs. They are NOT real-world results."]
             if is_synthetic else []),
        "library_versions": {"scikit-learn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }

    # --- 4. Save model, feature names, preprocessing info, metadata, test predictions ------------
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    name = model_name or f"tankcast_rf_{data_path.stem}"
    model_path = model_dir / f"{name}.joblib"
    joblib.dump({"model": model, "feature_names": features, "metadata": metadata}, model_path)
    (model_dir / f"{name}.metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    predictions.to_csv(model_dir / f"{name}_test_predictions.csv", index_label="timestamp", float_format="%.4f")
    metadata["saved_to"] = _relative(model_path)
    return metadata


def verify(model_path: Path | str) -> list[str]:
    """Re-derive the evaluation from the saved model + original data. Returns problems (empty = OK)."""
    model_path = Path(model_path)
    bundle = joblib.load(model_path)
    meta, model = bundle["metadata"], bundle["model"]
    problems: list[str] = []
    data_path = PROJECT_ROOT / meta["data_path"] if not Path(meta["data_path"]).is_absolute() else Path(meta["data_path"])
    if not data_path.exists():
        return [f"Training data not found at {data_path}."]
    if _sha256(data_path) != meta["data_sha256"]:
        return ["The data file has changed since training (checksum differs), so the saved results cannot be "
                "reproduced. Retrain on the current file."]

    _, _, features, train_df, test_df = prepare_data(load_csv(data_path), meta["date_column"], meta["target_column"],
                                                     meta["frequency"], meta["horizon_steps"], meta["test_fraction"])
    if features != meta["feature_names"] or features != bundle["feature_names"]:
        problems.append("Feature names differ from those saved with the model.")
    if not train_df.index.max() < test_df.index.min():
        problems.append("Training period overlaps the test period.")
    if str(test_df.index.min()) != meta["split"]["test_start"] or str(train_df.index.max()) != meta["split"]["train_end"]:
        problems.append("Train/test boundary differs from the saved metadata.")

    fresh = _scores(test_df["target"], model.predict(test_df[features]))
    for key in ("mae", "rmse"):
        if not np.isclose(fresh[key], meta["metrics"]["random_forest"][key], rtol=1e-6):
            problems.append(f"Recomputed {key.upper()} {fresh[key]:.4f} != saved {meta['metrics']['random_forest'][key]:.4f}.")
    return problems


def format_summary(m: dict) -> str:
    unit, line = m["target_unit"], "=" * 70
    out = [line, "TANKCAST TRAINING SUMMARY", line]
    if m["is_synthetic"]:
        out += ["*** SYNTHETIC DEMO DATA - these numbers are NOT real-world results ***", ""]
    out += [f"Data status : {m['data_status']}", f"Data file   : {m['data_path']}",
            f"Target      : {m['target_column']}  [{unit}]",
            f"Frequency   : {m['frequency']}   Horizon: {m['horizon_steps']} step(s) ahead",
            f"Train       : {m['split']['train_start']} -> {m['split']['train_end']}  ({m['split']['n_train']} rows)",
            f"Test        : {m['split']['test_start']} -> {m['split']['test_end']}  ({m['split']['n_test']} rows)",
            f"Missing time steps left empty: {m['preprocessing']['n_missing_steps']}",
            f"Features    : {', '.join(m['feature_names'])}", "",
            f"TEST-PERIOD ERRORS (unit: {unit}; mean test demand = {m['mean_test_target']:.2f})",
            f"  {'model':<16}{'MAE':>12}{'RMSE':>12}"]
    for name, s in m["metrics"].items():
        out.append(f"  {name:<16}{s['mae']:>12.3f}{s['rmse']:>12.3f}")
    verdict = "BEATS" if m["random_forest_beats_all_baselines"] else "does NOT beat"
    out += ["", f"Random Forest {verdict} the baseline(s) (MAE change vs best baseline '{m['best_baseline']}': "
                f"{m['mae_improvement_over_best_baseline_pct']:+.1f}%).",
            "MAE = average error in the unit above. RMSE punishes big misses more (always >= MAE).",
            "", f"Saved: {m['saved_to']}  (+ .metadata.json and _test_predictions.csv)", line]
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Train the TANKCAST Random Forest demand model.")
    p.add_argument("--data", help="Hourly/daily CSV, e.g. data/processed/hourly_water_demand.csv")
    p.add_argument("--horizon", type=int, default=24, help="steps ahead to forecast (default 24)")
    p.add_argument("--test-fraction", type=float, default=0.2)
    p.add_argument("--date-column"); p.add_argument("--target-column")
    p.add_argument("--unit", help="Target unit, e.g. 'litres per hour' (needed if no .meta.json sits next to the CSV)")
    p.add_argument("--model-name")
    p.add_argument("--verify", metavar="MODEL.joblib", help="Check a saved model reproduces its reported metrics")
    a = p.parse_args(argv)
    try:
        if a.verify:
            problems = verify(a.verify)
            print("VERIFICATION " + ("PASSED: saved metrics reproduce exactly from the data; no train/test overlap."
                                     if not problems else "FAILED:\n  - " + "\n  - ".join(problems)))
            return 0 if not problems else 1
        if not a.data:
            p.error("--data is required unless --verify is used")
        print(format_summary(train(a.data, a.horizon, a.test_fraction, a.date_column, a.target_column, a.unit,
                                   model_name=a.model_name)))
        return 0
    except (TrainingDataError, pp.SchemaError, DatasetNotFoundError, FileNotFoundError, ValueError) as err:
        print(f"CANNOT TRAIN: {err}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
