"""Dataset loading and inspection for TANKCAST.

Usage (from the project root):

    python -m src.data_loader                         # inspect every CSV in data/raw/
    python -m src.data_loader --path data/raw/my.csv  # inspect one file
    python -m src.data_loader --path data/raw/my.csv --date-column Date --target-column "Total M.L.D"

This tool only REPORTS what is in the file. It never downloads anything and
never creates substitute data.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from src import preprocessing as pp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Rules of thumb for THIS prototype, not statistical laws.
MIN_DAILY_ROWS = 180        # roughly six months of daily data
MIN_HOURLY_ROWS = 24 * 30   # roughly one month of hourly data


class DatasetNotFoundError(FileNotFoundError):
    """The expected CSV is not on disk."""


MISSING_DATA_HELP = f"""
No dataset found. Nothing has been downloaded or invented.

To continue, download a real CSV yourself and place it in:
    {RAW_DIR}

Sources to investigate:
  1. Pune Municipal Corporation (OpenCity):
     https://data.opencity.in/dataset/water-consumption-in-pune
     (the page lists daily CSVs for Dec 2016 and Dec 2017)
  2. Kaggle competition dm1718 (needs a Kaggle login and accepting the rules):
     https://www.kaggle.com/competitions/dm1718

Then run:   python -m src.data_loader
"""


def list_raw_csvs(raw_dir: Path = RAW_DIR) -> list[Path]:
    return sorted(raw_dir.glob("*.csv")) if raw_dir.exists() else []


def load_csv(path: Path | str) -> pd.DataFrame:
    """Read a CSV with clear errors. Column names are stripped of stray spaces."""
    path = Path(path)
    if not path.exists():
        raise DatasetNotFoundError(f"File not found: {path}\n{MISSING_DATA_HELP}")
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")  # utf-8-sig also removes a BOM if present
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
    df.columns = [str(c).strip() for c in df.columns]
    return df


# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------
@dataclass
class DatasetReport:
    file_path: Optional[str]
    n_rows: int
    columns: pd.DataFrame                 # name, dtype, missing, missing_pct
    date_column: Optional[str]
    date_note: str
    date_min: Optional[pd.Timestamp]
    date_max: Optional[pd.Timestamp]
    frequency: pp.FrequencyInfo
    duplicate_timestamps: int
    target: pp.TargetInfo
    total_relationship: Optional[tuple[str, list[str]]]
    numeric_summary: pd.DataFrame
    exogenous: dict[str, list[str]]
    candidate_feature_columns: list[str]
    suitability: str                      # "daily" / "hourly" / "not suitable"
    suitability_notes: list[str] = field(default_factory=list)
    schema: pp.SchemaCheck = field(default_factory=pp.SchemaCheck)


def _assess_suitability(freq: pp.FrequencyInfo, n_unique: int, target: pp.TargetInfo,
                        duplicates: int) -> tuple[str, list[str]]:
    notes: list[str] = []
    if target.column is None:
        return "not suitable", ["No target column identified."]
    if freq.label == "unknown":
        return "not suitable", ["Could not determine the time frequency (need a date column with 2+ distinct dates). "
                                "Without timestamps rows cannot be ordered in time, so chronological splitting, "
                                "lag features and persistence baselines are impossible."]
    if duplicates:
        notes.append(f"{duplicates} duplicate timestamp(s): several rows share a time (e.g. multiple zones stacked "
                     "in long format). Aggregate or pivot before forecasting.")
    if "MLD" in target.unit or "kL/day" in target.unit:
        notes.append("Municipal-scale units. These are NOT directly comparable with hostel litres/hour; "
                     "do not mix them without explicit scaling assumptions.")

    if freq.label == "hourly":
        if n_unique >= MIN_HOURLY_ROWS:
            return "hourly", notes
        notes.append(f"Only {n_unique} hourly rows (< {MIN_HOURLY_ROWS}); too few for a reliable ML model.")
    elif freq.label == "daily":
        if n_unique >= MIN_DAILY_ROWS:
            return "daily", notes
        notes.append(f"Only {n_unique} daily rows (< {MIN_DAILY_ROWS}); too few for a reliable ML model. "
                     "A baseline (e.g. persistence) is the defensible option; Random Forest results would not be trustworthy.")
    else:
        notes.append(f"Frequency is '{freq.label}', which this prototype does not forecast.")
    return "not suitable", notes


def inspect_dataset(df: pd.DataFrame, path: Optional[Path | str] = None,
                    date_column: Optional[str] = None, target_column: Optional[str] = None) -> DatasetReport:
    """Build a factual report about a DataFrame."""
    if date_column is not None and date_column not in df.columns:
        raise pp.SchemaError(f"Date column {date_column!r} not found. Columns: {list(df.columns)}")
    date_col = date_column or pp.find_date_column(df)

    parsed, date_note = (pd.Series(dtype="datetime64[ns]"), "")
    if date_col is not None:
        parsed, date_note = pp.parse_dates(df[date_col])

    freq = pp.infer_frequency(parsed) if date_col is not None else pp.FrequencyInfo("unknown", None, 0.0, 0)
    duplicates = int(parsed.dropna().duplicated().sum()) if date_col is not None else 0
    target = pp.guess_target(df, date_col, target_column)

    missing = df.isna().sum()
    columns = pd.DataFrame({
        "name": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "missing": missing.values,
        "missing_pct": (missing.values / max(len(df), 1) * 100).round(1),
    })
    numeric = df.select_dtypes("number")
    n_unique = int(parsed.dropna().nunique()) if date_col is not None else 0
    suitability, notes = _assess_suitability(freq, n_unique, target, duplicates)
    total_rel = pp.detect_total_relationship(df, date_col)
    if total_rel:
        notes.append(f"'{total_rel[0]}' is approximately the sum of the other numeric columns. Using those columns "
                     "from the SAME period as features would leak the answer; only past values may be used.")
    if freq.n_gaps:
        notes.append(f"{freq.n_gaps} gap(s) larger than the usual step (missing periods).")

    candidates = [c for c in numeric.columns if c not in (date_col, target.column)]
    return DatasetReport(
        file_path=str(path) if path else None,
        n_rows=len(df),
        columns=columns,
        date_column=date_col,
        date_note=date_note,
        date_min=parsed.min() if date_col is not None and parsed.notna().any() else None,
        date_max=parsed.max() if date_col is not None and parsed.notna().any() else None,
        frequency=freq,
        duplicate_timestamps=duplicates,
        target=target,
        total_relationship=total_rel,
        numeric_summary=numeric.describe().T.round(3) if not numeric.empty else pd.DataFrame(),
        exogenous=pp.detect_exogenous_columns(df),
        candidate_feature_columns=candidates,
        suitability=suitability,
        suitability_notes=notes,
        schema=pp.validate_schema(df, date_col, target.column),
    )


def format_report(r: DatasetReport) -> str:
    """Plain-text report (ASCII only so it prints on any terminal)."""
    line = "=" * 70
    out = [line, "TANKCAST DATASET INSPECTION", line,
           f"File           : {r.file_path or '(in-memory DataFrame)'}",
           f"Rows x columns : {r.n_rows} x {len(r.columns)}", "", "COLUMNS"]
    out.append(r.columns.to_string(index=False))

    out += ["", "TIME COVERAGE"]
    if r.date_column is None:
        out.append("  No date column detected.")
    else:
        step = r.frequency.median_step
        out += [f"  Date column         : {r.date_column}",
                f"  Range               : {r.date_min} -> {r.date_max}",
                f"  Detected frequency  : {r.frequency.label}" + (f" (median step {step})" if step is not None else ""),
                f"  Regular steps       : {r.frequency.regular_fraction:.0%}   Gaps: {r.frequency.n_gaps}",
                f"  Duplicate timestamps: {r.duplicate_timestamps}"]
        if r.date_note:
            out.append(f"  NOTE: {r.date_note}")

    out += ["", "TARGET (guess - please confirm)"]
    t = r.target
    out += [f"  Column : {t.column}", f"  Unit   : {t.unit}  [{t.unit_source}]", f"  Why    : {t.reason}"]
    if t.other_candidates:
        out.append(f"  Other candidate columns: {', '.join(t.other_candidates)}")

    out += ["", "FEATURES ACTUALLY AVAILABLE"]
    out.append("  Time features (hour, weekday, month...) can be derived from the date column"
               if r.date_column else "  No date column, so no time features.")
    out.append(f"  Other numeric columns: {r.candidate_feature_columns or 'none'}")
    for label, cols in r.exogenous.items():
        out.append(f"  {label.capitalize()} data: " + (", ".join(cols) if cols else "NOT in this dataset (do not model it)"))

    out += ["", "NUMERIC SUMMARY", r.numeric_summary.to_string() if not r.numeric_summary.empty else "  (no numeric columns)"]

    out += ["", "SUITABILITY FOR FORECASTING", f"  Verdict: {r.suitability.upper()}"]
    out += [f"  - {n}" for n in r.suitability_notes]
    out += ["", "SCHEMA CHECK", f"  Result: {'OK' if r.schema.ok else 'PROBLEMS FOUND'}"]
    out += [f"  ERROR: {e}" for e in r.schema.errors] + [f"  warning: {w}" for w in r.schema.warnings]
    out.append(line)
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a water-demand CSV (no data is downloaded or invented).")
    parser.add_argument("--path", help="CSV to inspect. Default: every CSV in data/raw/")
    parser.add_argument("--date-column", help="Override the detected date column")
    parser.add_argument("--target-column", help="Override the detected target column")
    args = parser.parse_args(argv)

    paths = [Path(args.path)] if args.path else list_raw_csvs()
    if not paths:
        print(MISSING_DATA_HELP)
        return 2
    for path in paths:
        try:
            df = load_csv(path)
            print(format_report(inspect_dataset(df, path, args.date_column, args.target_column)))
        except (DatasetNotFoundError, pp.SchemaError) as err:
            print(err)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
