"""Tests for src/prepare_meter_data.py using a tiny SYNTHETIC fixture in the documented DAIAD format
(meter ID, dd/MM/yyyy HH:mm:ss, cumulative litres, litres since last reading). Numbers are invented
so the expected answers can be checked by hand; this does NOT test the real 17-million-row file."""
import math
import zipfile

import pytest

from src.prepare_meter_data import aggregate_meter_file, detect_delimiter, has_header

ROWS = """M1,01/03/2016 00:10:00,100,5
M2,01/03/2016 00:20:00,200,7
M3,01/03/2016 00:30:00,50,9
M1,01/03/2016 01:10:00,105,5
M2,01/03/2016 01:20:00,207,-1
M3,01/03/2016 01:30:00,59,3
M1,01/03/2016 03:10:00,110,9
"""


def test_hourly_mean_over_reporting_meters(tmp_path):
    f = tmp_path / "m.csv"; f.write_text(ROWS)
    hourly, stats = aggregate_meter_file(f, min_readings_fraction=0.0)
    assert len(hourly) == 4  # hours 0..3
    assert math.isclose(hourly["litres_per_meter_hour"].iloc[0], (5 + 7 + 9) / 3)
    assert math.isclose(hourly["litres_per_meter_hour"].iloc[1], (5 + 3) / 2)  # negative reading dropped
    assert math.isnan(hourly["litres_per_meter_hour"].iloc[2])  # no readings -> missing, not invented
    assert hourly["readings"].tolist() == [3, 2, 0, 1]
    assert stats["negative_values"] == 1 and stats["n_meters"] == 3 and stats["rows_read"] == 7


def test_hours_with_too_few_meters_become_missing(tmp_path):
    f = tmp_path / "m.csv"; f.write_text(ROWS)
    hourly, stats = aggregate_meter_file(f, min_readings_fraction=0.6)  # typical=2 -> need >= 1.2
    assert math.isnan(hourly["litres_per_meter_hour"].iloc[3])
    assert stats["n_hours_set_missing_for_too_few_meters"] == 1


def test_zip_and_header_are_handled(tmp_path):
    csv = tmp_path / "inner.csv"
    csv.write_text("meter,time,total,delta\n" + ROWS)
    z = tmp_path / "m.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(csv, "inner.csv")
    hourly, stats = aggregate_meter_file(z, min_readings_fraction=0.0)
    assert stats["rows_read"] == 7
    assert math.isclose(hourly["litres_per_meter_hour"].iloc[0], 7.0)


def test_wrong_format_is_rejected(tmp_path):
    f = tmp_path / "bad.csv"; f.write_text("a,not a date,1,2\nb,also not,3,4\n")
    with pytest.raises(ValueError, match="timestamps"):
        aggregate_meter_file(f)


def test_helpers():
    assert detect_delimiter("a;b;c;d") == ";"
    assert has_header("meter,time,total,delta") and not has_header("M1,01/03/2016 00:10:00,1,2")
    with pytest.raises(ValueError):
        detect_delimiter("justonecolumn")


def test_result_does_not_depend_on_chunk_size(tmp_path):
    """The real file spans many chunks; a meter-hour split across a chunk boundary must not change results."""
    lines = []
    for m in range(5):
        for h in range(200):
            day, hour = divmod(h, 24)
            lines.append(f"M{m},{day + 1:02d}/03/2016 {hour:02d}:{(m * 7) % 60:02d}:00,0,{(m * 31 + h * 17) % 50}")
    f = tmp_path / "many.csv"; f.write_text("\n".join(lines) + "\n")
    small, _ = aggregate_meter_file(f, chunksize=7, min_readings_fraction=0.0)
    large, _ = aggregate_meter_file(f, chunksize=100_000, min_readings_fraction=0.0)
    assert small.equals(large)
    assert len(small) == 200
