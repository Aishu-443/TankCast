
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "hourly_water_demand.csv"
MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "tankcast_extra_trees_integration_ready.joblib"
)

from src.forecast import forecast_next_24_hours

app = FastAPI(title="TankCast API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bundle = None
model_load_error = None

try:
    bundle = joblib.load(MODEL_PATH)
except Exception as exc:
    model_load_error = str(exc)


def load_history():
    if not DATA_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Historical data file not found: {DATA_PATH}",
        )

    data = pd.read_csv(DATA_PATH)

    required = {"timestamp", "litres_per_meter_hour"}
    if not required.issubset(data.columns):
        raise HTTPException(
            status_code=500,
            detail="Historical data is missing required columns.",
        )

    data["timestamp"] = pd.to_datetime(
        data["timestamp"], errors="coerce"
    )
    data["litres_per_meter_hour"] = pd.to_numeric(
        data["litres_per_meter_hour"], errors="coerce"
    )

    data = (
        data.dropna(subset=["timestamp", "litres_per_meter_hour"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    if data.empty:
        raise HTTPException(
            status_code=500,
            detail="No valid historical readings are available.",
        )

    return data


def get_forecast():
    if bundle is None:
        raise HTTPException(
            status_code=503,
            detail=f"ML model is unavailable: {model_load_error}",
        )

    try:
        data = load_history()
        return forecast_next_24_hours(
            data,
            model_path=MODEL_PATH,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Forecast generation failed: {exc}",
        ) from exc


def get_metadata():
    return bundle.get("metadata", {}) if bundle else {}


@app.get("/")
def root():
    return {
        "message": "TankCast backend is running",
        "modelLoaded": bundle is not None,
    }


@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok" if bundle is not None else "error",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modelLoaded": bundle is not None,
        "activeModelName": MODEL_PATH.name,
        "environment": "local",
        "provisionalNotice": (
            "Research prototype; not yet validated for an Indian hostel."
        ),
    }


@app.get("/api/model/info")
def model_info():
    if bundle is None:
        raise HTTPException(
            status_code=503,
            detail="ML model is unavailable.",
        )

    return {
        "modelType": "ExtraTreesRegressor "
        "(n_estimators=200, min_samples_leaf=3)",
        "targetUnit": "litres per meter per hour",
        "frequency": "hourly",
        "horizonSteps": 24,
        "isSynthetic": False,
        "datasetSource": "DAIAD residential smart-meter data",
        "featuresUsed": bundle.get("feature_names", []),
        "featurePolicy": (
            "Hourly calendar features and historical lag/rolling features. "
            "No weather or occupancy features."
        ),
    }


@app.get("/api/forecast")
def forecast(
    scaling_factor: float = Query(default=1.0, gt=0, le=1000),
    meter_count: int = Query(default=100, ge=0, le=100000),
):
    result = get_forecast()
    multiplier = scaling_factor * meter_count
    predictions = []

    for row in result.to_dict(orient="records"):
        timestamp = pd.Timestamp(row["timestamp"]).isoformat()
        value = float(row["predicted_demand"])

        predictions.append({
            "timestamp": timestamp,
            "hour": pd.Timestamp(timestamp).hour,
            "predictedLitersPerMeter": value,
            "totalScaledDemandLiters": value * multiplier,
        })

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "horizonHours": len(predictions),
        "targetUnit": "litres per meter per hour",
        "scalingMultiplier": multiplier,
        "predictions": predictions,
        "isProvisional": True,
    }


@app.get("/api/historical")
def historical():
    data = load_history()
    recent = data.tail(168)
    points = []

    for row in recent.to_dict(orient="records"):
        timestamp = pd.Timestamp(row["timestamp"]).isoformat()
        value = float(row["litres_per_meter_hour"])

        points.append({
            "timestamp": timestamp,
            "hour": pd.Timestamp(timestamp).hour,
            "actualLitersPerMeter": value,
            "scaledBuildingLiters": value * 100,
        })

    return {
        "timeRange": {
            "start": points[0]["timestamp"] if points else None,
            "end": points[-1]["timestamp"] if points else None,
        },
        "targetUnit": "litres per meter per hour",
        "points": points,
    }


@app.get("/api/recommendations")
def recommendations():
    result = get_forecast()

    if result.empty:
        items = [{
            "id": "data-check",
            "title": "Check forecast availability",
            "action": (
                "Verify the latest meter readings and forecasting data."
            ),
            "priority": "medium",
            "category": "maintenance",
            "suggestedAt": datetime.now(timezone.utc).isoformat(),
            "explanation": "No forecast values were returned.",
        }]
    else:
        peak = result.loc[result["predicted_demand"].idxmax()]
        peak_value = float(peak["predicted_demand"])
        peak_time = pd.Timestamp(peak["timestamp"]).isoformat()

        items = [{
            "id": "peak-demand",
            "title": "Review projected peak demand",
            "action": (
                "Review supply and storage plans around the predicted peak. "
                "Confirm operational decisions against actual tank levels."
            ),
            "priority": "medium",
            "category": "refill",
            "suggestedAt": peak_time,
            "impactEstimate": (
                "Potential shortage risk reduction; not quantified"
            ),
            "explanation": (
                "The model's highest predicted per-meter hourly demand "
                f"is {peak_value:.2f} litres at {peak_time}. "
                "This is a rule-based advisory based on the forecast."
            ),
        }]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


@app.get("/api/model/evidence")
def model_evidence():
    if bundle is None:
        raise HTTPException(
            status_code=503,
            detail="ML model is unavailable.",
        )

    metadata = get_metadata()
    metrics = metadata.get("metrics", {})
    split = metadata.get("split", {})

    return {
        "modelName": MODEL_PATH.name,
        "modelType": "ExtraTreesRegressor",
        "horizonHours": 24,
        "datasetName": "DAIAD residential smart-meter data",
        "samplePeriod": (
            f"{split.get('train_start', 'Unknown')} to "
            f"{split.get('test_end', 'Unknown')}"
        ),
        "targetUnit": "litres per meter per hour",
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "mape": None,
        "metrics": {
            "mae": metrics.get("mae"),
            "rmse": metrics.get("rmse"),
            "mape": None,
            "baselineName": None,
            "baselineMae": None,
            "baselineRmse": None,
            "improvementOverBaselinePct": None,
        },
        "dataSplit": {
            "trainPeriod": (
                f"{split.get('train_start', 'Unknown')} to "
                f"{split.get('train_end', 'Unknown')}"
            ),
            "testPeriod": (
                f"{split.get('test_start', 'Unknown')} to "
                f"{split.get('test_end', 'Unknown')}"
            ),
        },
        "featurePolicy": (
            "10 historical lag, rolling-statistic and calendar features."
        ),
        "isVerified": False,
        "notes": [
            "Evaluation metrics are from the model bundle metadata.",
            "The forecast predicts litres per meter per hour.",
            "Building totals depend on the user-specified scaling multiplier.",
        ],
        "limitations": [
            "Trained on Spanish residential smart-meter data; Indian hostel "
            "usage patterns may differ.",
            "Scaling to a building is an assumption, not a measured total.",
            "Weather, occupancy and college schedules are not model features.",
            "Tank levels are manual simulation inputs, not live sensor readings.",
            "No baseline improvement is claimed by this endpoint.",
        ],
    }
