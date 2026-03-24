from __future__ import annotations

import pandas as pd

_REQUIRED = {"sensor_id", "timestamp"}


def _require_columns(frame, required):
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing required column(s): {joined}")


def _as_timedelta(value, name):
    try:
        delta = pd.Timedelta(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a pandas timedelta string, got {value!r}") from exc
    if delta <= pd.Timedelta(0):
        raise ValueError(f"{name} must be positive")
    return delta


def _clean_times(frame, time_col):
    out = frame.copy()
    # TODO: decide whether timezone-aware supplier files should be normalized to UTC here.
    out[time_col] = pd.to_datetime(out[time_col], errors="coerce")
    return out.dropna(subset=[time_col])


def detect_gaps(
    frame: pd.DataFrame,
    *,
    sensor_col: str = "sensor_id",
    time_col: str = "timestamp",
    max_gap: str = "10min",
) -> pd.DataFrame:
    """Return one row per observed gap larger than ``max_gap``.

    The returned frame has columns: ``sensor_id`` (or the configured sensor column
    name), ``gap_start``, ``gap_end``, and ``duration``. Bad timestamps are ignored;
    missing structural columns are not.
    """
    _require_columns(frame, {sensor_col, time_col})
    limit = _as_timedelta(max_gap, "max_gap")

    clean = _clean_times(frame[[sensor_col, time_col]], time_col)
    if clean.empty:
        return pd.DataFrame(columns=[sensor_col, "gap_start", "gap_end", "duration"])

    clean = clean.sort_values([sensor_col, time_col], kind="mergesort")
    clean = clean.drop_duplicates([sensor_col, time_col], keep="first")

    rows = []
    for sensor, group in clean.groupby(sensor_col, sort=False):
        previous = group[time_col].shift()
        duration = group[time_col] - previous
        gaps = group.loc[duration > limit, [time_col]].copy()
        for idx, row in gaps.iterrows():
            start = previous.loc[idx]
            end = row[time_col]
            rows.append(
                {
                    sensor_col: sensor,
                    "gap_start": start,
                    "gap_end": end,
                    "duration": end - start,
                }
            )

    return pd.DataFrame(rows, columns=[sensor_col, "gap_start", "gap_end", "duration"])
