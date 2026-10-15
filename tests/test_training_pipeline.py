"""End-to-end tests for src/train_model.py.
The training data here is SYNTHETIC DEMO DATA generated in a temp folder. These tests check that the
code behaves correctly (including refusing bad data); they say nothing about real-world accuracy."""
import math

import joblib
import pandas as pd
import pytest

from src import preprocessing as pp
from src.make_demo_data import generate_demo_frame, write_demo
from src.train_model import TrainingDataError, mae, rmse, train, verify


@pytest.fixture
def demo_csv(tmp_path):
    return write_demo(tmp_path / "demo.csv")


def test_metric_functions_by_hand():
    assert mae([1, 2, 3], [2, 2, 5]) == 1.0
    assert math.isclose(rmse([1, 2, 3], [2, 2, 5]), math.sqrt(5 / 3))


def test_train_saves_everything_and_labels_synthetic(demo_csv, tmp_path):
    meta = train(demo_csv, horizon=24, model_dir=tmp_path / "models", model_name="m")
    for suffix in (".joblib", ".metadata.json", "_test_predictions.csv"):
        assert (tmp_path / "models" / f"m{suffix}").exists()
    assert meta["is_synthetic"] is True
    assert any("SYNTHETIC" in text for text in meta["limitations"])
    assert meta["target_unit"] == "litres per hour"
    assert pd.Timestamp(meta["split"]["train_end"]) < pd.Timestamp(meta["split"]["test_start"])
    assert meta["exogenous_features_used"] == []
    assert not any(("temp" in f or "occup" in f) for f in meta["feature_names"])
    assert meta["metrics"]["random_forest"]["rmse"] >= meta["metrics"]["random_forest"]["mae"]


def test_saved_model_loads_and_predicts(demo_csv, tmp_path):
    meta = train(demo_csv, horizon=24, model_dir=tmp_path, model_name="m")
    bundle = joblib.load(tmp_path / "m.joblib")
    row = pd.DataFrame([[0.0] * len(bundle["feature_names"])], columns=bundle["feature_names"])
    assert bundle["model"].predict(row).shape == (1,)
    assert bundle["feature_names"] == meta["feature_names"]


def test_training_is_reproducible(demo_csv, tmp_path):
    a = train(demo_csv, horizon=24, model_dir=tmp_path / "a")["metrics"]["random_forest"]
    b = train(demo_csv, horizon=24, model_dir=tmp_path / "b")["metrics"]["random_forest"]
    # Same seed => same model, but the forest averages trees in parallel (n_jobs=-1), so the last
    # floating-point digit can differ between runs. Compare with a tight tolerance, not exact equality.
    assert a.keys() == b.keys() == {"mae", "rmse"}
    for name in ("mae", "rmse"):
        assert a[name] == pytest.approx(b[name], rel=1e-9, abs=1e-12), name


def test_verify_passes_then_detects_changed_data(demo_csv, tmp_path):
    train(demo_csv, horizon=24, model_dir=tmp_path, model_name="m")
    assert verify(tmp_path / "m.joblib") == []
    demo_csv.write_text(demo_csv.read_text() + "2030-01-01 00:00:00,999\n")
    assert any("changed" in problem for problem in verify(tmp_path / "m.joblib"))


def test_refuses_tiny_dataset_like_one_month_of_daily_data(tmp_path):
    df = pd.DataFrame({"Date": [f"{d:02d}-12-2016" for d in range(1, 32)],
                       "Total M.L.D": [100 + d for d in range(31)]})  # SYNTHETIC fixture
    f = tmp_path / "small.csv"; df.to_csv(f, index=False)
    with pytest.raises(TrainingDataError, match="not suitable"):
        train(f, unit="MLD", model_dir=tmp_path)


def test_refuses_when_unit_unknown(demo_csv, tmp_path):
    bare = tmp_path / "bare.csv"  # same data, but no .meta.json next to it
    generate_demo_frame().to_csv(bare, index=False)
    with pytest.raises(TrainingDataError, match="unit"):
        train(bare, model_dir=tmp_path)
    assert train(bare, unit="litres per hour", model_dir=tmp_path)["target_unit"] == "litres per hour"


def test_refuses_table_without_timestamps(tmp_path):
    df = pd.DataFrame({"a": range(1000), "b": range(1000), "nextCons": range(1000)})  # hypothetical fixture
    f = tmp_path / "no_time.csv"; df.to_csv(f, index=False)
    with pytest.raises(pp.SchemaError, match="date"):
        train(f, unit="litres", model_dir=tmp_path)


def test_refuses_stacked_series_with_duplicate_timestamps(tmp_path):
    base = generate_demo_frame()
    stacked = pd.concat([base, base.assign(demand_litres_per_hour=base["demand_litres_per_hour"] * 2)])
    f = tmp_path / "stacked.csv"; stacked.to_csv(f, index=False)
    with pytest.raises(TrainingDataError, match="duplicate"):
        train(f, unit="litres per hour", model_dir=tmp_path)


def test_refuses_data_with_too_many_gaps(tmp_path):
    base = generate_demo_frame()
    sparse = base.sample(frac=0.55, random_state=1).sort_values("timestamp")  # ~45% of hours missing, still hourly
    f = tmp_path / "sparse.csv"; sparse.to_csv(f, index=False)
    with pytest.raises(TrainingDataError, match="no value"):
        train(f, unit="litres per hour", model_dir=tmp_path)
