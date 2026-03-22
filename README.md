# sensor-gaps

Small pandas helpers for checking timestamped sensor exports. The package reads a CSV with
`sensor_id`, `timestamp`, and `value`, resamples each sensor to a fixed interval, and reports
places where the time between readings is too large.

This is aimed at local QA notebooks/scripts, not a daemon or a full validation framework.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Run the tests:

```bash
pytest
```

## Quick use

```python
from pathlib import Path
from sensor_gaps import load_readings, resample_readings, detect_gaps

readings = load_readings(Path("data/readings.csv"))

five_min = resample_readings(readings, freq="5min")
print(five_min.head())

gaps = detect_gaps(readings, max_gap="10min")
print(gaps)
```

`resample_readings` returns one row per sensor per interval. Empty intervals are kept with a
missing `value`, which makes quick plots and joins easier. `detect_gaps` works on the observed
readings, so it is useful before filling or resampling anything.

## Layout

- `data/readings.csv` - small messy export used by tests and for manual poking
- `sensor_gaps/gaps.py` - gap detection
- `sensor_gaps/resample.py` - CSV loading and per-sensor resampling
- `tests/` - pytest checks for the main path and validation errors

## Non-goals

No timezone conversion, no interpolation policy, and no attempt to guess units from column names.
If a supplier changes the export shape, clean it up before calling these functions.
