# TANKCAST - ML-based water demand forecasting and tank monitoring

A college-level prototype that forecasts water demand and estimates how long a tank's water will last
(hostel / institution setting, Visakhapatnam, India).

**Status: Phase 2 of 4 complete** - data validation, leakage-safe features, training pipeline with baselines,
saved model + metadata, tank calculator. **Not built yet:** forecasting module, SHAP, Streamlit dashboard.

## Honest data statement

- **No live sensor.** Tank level/capacity/supply are manually entered scenario values.
- **No dataset ships in this repo as real data.** Nothing is downloaded automatically.
- `data/demo/synthetic_hostel_hourly_DEMO.csv` is **SYNTHETIC DEMO DATA** (random numbers). Models trained on it
  prove the code runs, nothing more. Their metadata is flagged `is_synthetic: true`.

| Dataset | Real? | Used for | Why |
|---|---|---|---|
| DAIAD Alicante smart meters (`swm_trialA_1K.zip`) | Real, hourly, litres, with timestamps | **Main ML pipeline** | Only candidate found that is hourly and timestamped. Spain, households, not a hostel. |
| Pune Municipal Corporation (OpenCity) | Real, daily, MLD | **Context only** | ~1 month per file; municipal scale. Trainer refuses it (too few rows). |
| Kaggle `dm1718` | Real | **Not used for time-series training** | Its page says rows carry no hour information and have no order dependency (target `nextCons`). Without timestamps there is no chronological split, lag feature or persistence baseline. Inspect the file yourself to confirm. |

## Install (Windows PowerShell)

```powershell
cd tankcast
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -v
```

## Check the pipeline works (synthetic demo - NOT real results)

```powershell
python -m src.make_demo_data
python -m src.train_model --data data\demo\synthetic_hostel_hourly_DEMO.csv --model-name tankcast_rf_DEMO_synthetic
python -m src.train_model --verify models\tankcast_rf_DEMO_synthetic.joblib
```

## Real data: DAIAD hourly smart-meter file

1. Download `swm_trialA_1K.zip` (about 90.6 MB) from the GitHub page listed on the dataset's page:
   <https://github.com/DAIAD/data/blob/master/swm_trialA_1K.zip> -> **Download raw file**. Save it as
   `data\raw\swm_trialA_1K.zip`. (Do not unzip; the tool reads the zip.)
2. Aggregate to one hourly series (reads ~17M rows in chunks; a minute or few):
   ```powershell
   python -m src.prepare_meter_data --input data\raw\swm_trialA_1K.zip
   ```
   Check the printed SUMMARY against the dataset description (meters, date range, dropped rows, missing hours).
3. Inspect the result:
   ```powershell
   python -m src.data_loader --path data\processed\hourly_water_demand.csv
   ```
4. Train (24 = forecast each hour from information at least a day old; `--horizon 1` = next hour):
   ```powershell
   python -m src.train_model --data data\processed\hourly_water_demand.csv --horizon 24
   ```
5. Verify the saved numbers reproduce from the data:
   ```powershell
   python -m src.train_model --verify models\tankcast_rf_hourly_water_demand.joblib
   ```

### Optional: inspect the Kaggle and Pune files
Put Kaggle files in `data\raw\kaggle_dm1718\` (needs a Kaggle login and accepting the rules) and Pune CSVs in
`data\raw\pune\`, then run `python -m src.data_loader --path <file>`.

## How the model avoids cheating
- Every lag is at least `horizon` steps old; rolling statistics are computed on the series shifted by `horizon`
  (tested by tampering with the future and checking features do not change).
- Train = oldest 80% of rows, test = newest 20%. No shuffling. Hyper-parameters are fixed, not tuned on the test period.
- Missing time steps are left empty, never interpolated. Hours where far fewer meters than usual reported are treated as missing.
- Baselines: persistence, and "same time last cycle" (same hour yesterday). The model must beat them to be worth using.
- Only target-derived and calendar features are used. Temperature/occupancy are **not** used (not in the data, and
  future values would be unknown at prediction time).
- Training refuses: missing timestamps, unknown units, tiny datasets, stacked series, >30% missing steps.

## Metrics
MAE = average error in the target's own unit. RMSE = like MAE but punishes large misses more (always >= MAE).

## Saved artefacts (`models/`)
`<name>.joblib` (model + feature names + metadata), `<name>.metadata.json` (human-readable), `<name>_test_predictions.csv`.

## Tank calculator
Per interval: `new_level = old_level - (demand - supply) x hours`, limited to 0..capacity. If the tank never empties the
result says the depletion time cannot be calculated and why. Units: L/hour, L/day, m3/day, MLD (conversion only).

## Known limitations
- DAIAD values are litres **per household meter**, in Spain. Using them for a hostel needs an explicit scaling
  assumption (e.g. occupancy), which is a later, clearly labelled step.
- A meter that skips readings may report several hours of water in one reading; this inflates that hour.
- Metrics come from one test period. Alert thresholds (30%/15%) are prototype defaults.
- Column/unit detection from names is a heuristic; training requires the unit to be declared.
