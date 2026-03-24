from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

_REQUIRED_COLUMNS = {"sensor_id", "timestamp", "value"}
_ALLOWED_AGG = {"mean", "median", "min", "max", "sum", "first", "last"}


def _require_columns(frame, required):
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")


def _validate_freq(freq):
    try:
        offset = pd.tseries.frequencies.to_offset(freq)
    except ValueError as exc:
        raise ValueError(f"invalid pandas frequency: {freq!r}") from exc
    if pd.Timedelta(offset) <= pd.Timedelta(0):
        raise ValueError("frequency must be positive")
    return offset


def _prepare_frame(frame, sensor_col, time_col, value_col):
    _require_columns(frame, {sensor_col, time_col, value_col})

    out = frame[[sensor_col, time_col, value_col]].copy()
    out[time_col] = pd.to_datetime(out[time_col], errors="coerce")
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce")
    out = out.dropna(subset=[sensor_col, time_col])
    return out.sort_values([sensor_col, time_col], kind="mergesort")


def load_readings(path: str | Path) -> pd.DataFrame:
    """Read a supplier CSV and normalize the timestamp/value columns.

    Rows with unparseable timestamps are kept out of the returned frame. Non-numeric
    values become missing values, because pandas aggregation handles those cleanly.
    """
    frame = pd.read_csv(path)
    return _prepare_frame(frame, "sensor_id", "timestamp", "value")


def resample_readings(
    frame: pd.DataFrame,
    freq: str = "5min",
    agg: Literal["mean", "median", "min", "max", "sum", "first", "last"] = "mean",
    *,
    sensor_col: str = "sensor_id",
    time_col: str = "timestamp",
    value_col: str = "value",
) -> pd.DataFrame:
    """Resample readings independently per sensor.

    Returns a tidy DataFrame with the sensor column, timestamp column, and value
    column. Intervals with no readings are present with a missing value when they
    fall between the first and last reading for that sensor.
    """
    offset = _validate_freq(freq)
    if agg not in _ALLOWED_AGG:
        raise ValueError(f"unsupported aggregation {agg!r}")

    clean = _prepare_frame(frame, sensor_col, time_col, value_col)
    if clean.empty:
        return pd.DataFrame(columns=[sensor_col, time_col, value_col])

    pieces = []
    for sensor, group in clean.groupby(sensor_col, sort=False):
        indexed = group.set_index(time_col)[value_col].sort_index()
        sampled = indexed.resample(offset).agg(agg)
        # sampled = sampled.rolling(3, center=True, min_periods=1).median()
        piece = sampled.rename(value_col).reset_index()
        piece.insert(0, sensor_col, sensor)
        pieces.append(piece)

    result = pd.concat(pieces, ignore_index=True)
    return result.sort_values([sensor_col, time_col], kind="mergesort").reset_index(drop=True)
