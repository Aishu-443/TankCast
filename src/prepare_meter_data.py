"""Turn a long-format smart-meter file (one row per meter reading) into ONE hourly series.

Built for the DAIAD "swm_trialA_1K" file (Alicante, Spain). Its page documents four fields per record:
    1. meter ID   2. timestamp "dd/MM/yyyy HH:mm:ss"   3. cumulative litres   4. litres since last reading
(whether the file has a header row is not documented, so both cases are handled).

Usage:
    python -m src.prepare_meter_data --input data/raw/swm_trialA_1K.zip

Output (in data/processed/):
    hourly_water_demand.csv        timestamp, litres_per_meter_hour, readings
    hourly_water_demand.meta.json  source, units, what was dropped, limitations

The target is the MEAN litres per meter per hour over the meters that reported in that hour. A plain
sum would jump whenever meters join or drop out, which is not a change in demand.
The file is read in chunks, so the full ~17 million rows are never held in memory at once.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
import pandas as pd

from src.data_loader import PROJECT_ROOT

TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"
TIMESTAMP_PATTERN = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}")
TARGET_COLUMN = "litres_per_meter_hour"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "hourly_water_demand.csv"


@contextlib.contextmanager
def open_source(path: Path) -> Iterator:
    """Open a CSV, or the single file inside a .zip, as a binary stream."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            members = [m for m in zf.namelist() if not m.endswith("/") and not m.startswith("__MACOSX")]
            if len(members) != 1:
                raise ValueError(f"Expected exactly one file inside {path.name}, found {members}. Unzip it and pass the CSV.")
            with zf.open(members[0]) as handle:
                yield handle
    else:
        with open(path, "rb") as handle:
            yield handle


def first_line(path: Path) -> str:
    with open_source(path) as handle:
        return handle.readline().decode("utf-8-sig", errors="replace").strip()


def detect_delimiter(line: str) -> str:
    """Pick the separator that splits the first line into at least 3 fields."""
    best = max([",", ";", "\t"], key=line.count)
    if line.count(best) < 2:
        raise ValueError(f"Could not detect the delimiter from the first line: {line!r}")
    return best


def has_header(line: str) -> bool:
    """A data row contains a dd/MM/yyyy HH:mm:ss timestamp; a header row does not."""
    return TIMESTAMP_PATTERN.search(line) is None


def aggregate_meter_file(path: Path | str, meter_pos: int = 0, time_pos: int = 1, value_pos: int = 3,
                         min_readings_fraction: float = 0.5, chunksize: int = 500_000,
                         verbose: bool = False) -> tuple[pd.DataFrame, dict]:
    """Aggregate meter readings to one row per hour. Returns (hourly_table, stats)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    line = first_line(path)
    sep, header = detect_delimiter(line), has_header(line)

    positions = {meter_pos: "meter_id", time_pos: "timestamp", value_pos: "litres"}
    order = sorted(positions)
    total = pd.Series(dtype="float64")
    readings = pd.Series(dtype="float64")
    meters: set[str] = set()
    stats = {"rows_read": 0, "bad_timestamps": 0, "unparseable_values": 0, "negative_values": 0,
             "max_readings_per_meter_hour_within_a_chunk": 0}

    with open_source(path) as handle:
        reader = pd.read_csv(handle, sep=sep, header=None, skiprows=1 if header else 0, usecols=order,
                             names=[positions[p] for p in order], dtype=str, chunksize=chunksize)
        for i, chunk in enumerate(reader):
            ts = pd.to_datetime(chunk["timestamp"], format=TIMESTAMP_FORMAT, errors="coerce")
            if i == 0 and ts.isna().mean() > 0.5:
                raise ValueError("More than half of the timestamps do not match dd/MM/yyyy HH:mm:ss. "
                                 "Check --time-pos and the file format.")
            litres = pd.to_numeric(chunk["litres"], errors="coerce")
            bad_ts, bad_val, negative = ts.isna(), litres.isna(), litres < 0
            stats["rows_read"] += len(chunk)
            stats["bad_timestamps"] += int(bad_ts.sum())
            stats["unparseable_values"] += int((bad_val & ~bad_ts).sum())
            stats["negative_values"] += int(negative.sum())

            ok = ~(bad_ts | bad_val | negative)
            hour = ts[ok].dt.floor("h")
            values = litres[ok]
            by_hour = values.groupby(hour)
            total = total.add(by_hour.sum(), fill_value=0.0)
            readings = readings.add(by_hour.size().astype(float), fill_value=0.0)
            ids = chunk.loc[ok, "meter_id"]
            per_meter_hour = values.groupby([hour, ids]).size()
            if len(per_meter_hour):
                stats["max_readings_per_meter_hour_within_a_chunk"] = max(
                    stats["max_readings_per_meter_hour_within_a_chunk"], int(per_meter_hour.max()))
            meters.update(ids.unique())
            if verbose:
                print(f"  ...{stats['rows_read']:,} rows processed", flush=True)

    if readings.empty:
        raise ValueError("No valid readings found. Check the file format and column positions.")

    grid = pd.date_range(total.index.min(), total.index.max(), freq=pd.Timedelta(hours=1))
    hourly = pd.DataFrame({TARGET_COLUMN: total / readings, "readings": readings}).reindex(grid)
    hourly["readings"] = hourly["readings"].fillna(0)
    typical = hourly.loc[hourly["readings"] > 0, "readings"].median()
    # Hours where far fewer meters than usual reported are unreliable: treat as missing, do not impute.
    unreliable = hourly["readings"] < min_readings_fraction * typical
    stats.update({
        "n_meters": len(meters),
        "n_hours_in_range": len(hourly),
        "n_hours_with_no_readings": int((hourly["readings"] == 0).sum()),
        "n_hours_set_missing_for_too_few_meters": int((unreliable & (hourly["readings"] > 0)).sum()),
        "typical_meters_reporting_per_hour": float(typical),
        "min_readings_fraction_rule": min_readings_fraction,
        "first_hour": str(grid[0]), "last_hour": str(grid[-1]),
    })
    hourly.loc[unreliable, TARGET_COLUMN] = np.nan
    hourly["readings"] = hourly["readings"].astype(int)
    hourly.index.name = "timestamp"
    stats["n_hours_usable"] = int(hourly[TARGET_COLUMN].notna().sum())
    return hourly, stats


def write_outputs(hourly: pd.DataFrame, stats: dict, source_file: Path, out_path: Path = OUTPUT_PATH) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    hourly.reset_index().to_csv(out_path, index=False, float_format="%.4f")
    meta = {
        "data_status": "REAL DATA - DAIAD smart water meters (Alicante, Spain), aggregated by TANKCAST",
        "is_synthetic": False,
        "source": "DAIAD swm_trialA_1K via https://hardmin.heal-link.gr/dataset/700cde6f-ef69-41f0-8fec-9c3f74ae38d4",
        "licence_as_stated_on_source_page": "CC-BY-SA 4.0",
        "source_file": source_file.name,
        "unit": "litres per meter per hour (mean over the meters that reported in that hour)",
        "date_column": "timestamp",
        "target_column": TARGET_COLUMN,
        "timestamps": "naive local utility time (CET incl. daylight saving, as exported); the repeated "
                      "autumn hour is averaged and the skipped spring hour appears as a gap",
        "processing": stats,
        "limitations": [
            "Residential households in Spain, not a hostel or an Indian city; usage patterns and climate differ.",
            "Values are per meter, not per building. Scaling to a hostel needs an explicit, separate assumption.",
            "If a meter skipped readings, its next 'litres since last reading' may cover several hours "
            "but is counted in one hour.",
            "No temperature or occupancy data is included.",
        ],
    }
    out_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate a smart-meter file to one hourly series.")
    parser.add_argument("--input", required=True, help="CSV or ZIP, e.g. data/raw/swm_trialA_1K.zip")
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument("--meter-pos", type=int, default=0, help="0-based column of the meter ID")
    parser.add_argument("--time-pos", type=int, default=1, help="0-based column of the timestamp")
    parser.add_argument("--value-pos", type=int, default=3, help="0-based column of litres since last reading")
    parser.add_argument("--min-readings-fraction", type=float, default=0.5)
    args = parser.parse_args(argv)
    try:
        print(f"Reading {args.input} in chunks (large files take a few minutes)...")
        hourly, stats = aggregate_meter_file(args.input, args.meter_pos, args.time_pos, args.value_pos,
                                             args.min_readings_fraction, verbose=True)
        out = write_outputs(hourly, stats, Path(args.input), Path(args.output))
    except (FileNotFoundError, ValueError) as err:
        print(f"ERROR: {err}")
        return 2
    print("\nSUMMARY (check these against the dataset description before trusting anything):")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print(f"\nWrote {out}\nNext: python -m src.data_loader --path {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
