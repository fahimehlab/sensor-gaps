from pathlib import Path

import pandas as pd
import pytest

from sensor_gaps import detect_gaps, load_readings, resample_readings

DATA = Path(__file__).resolve().parents[1] / "data" / "readings.csv"


def test_load_resample_and_detect_gaps_happy_path():
    readings = load_readings(DATA)

    assert set(readings.columns) == {"sensor_id", "timestamp", "value"}
    assert len(readings) == 14
    assert pd.api.types.is_datetime64_any_dtype(readings["timestamp"])

    sampled = resample_readings(readings, freq="5min")

    boiler = sampled[sampled["sensor_id"] == "boiler-1"]
    assert len(boiler) == 7
    assert boiler["timestamp"].iloc[0] == pd.Timestamp("2024-03-01 00:00:00")
    assert boiler.loc[boiler["timestamp"] == pd.Timestamp("2024-03-01 00:15:00"), "value"].isna().all()

    freezer_value = sampled.loc[
        (sampled["sensor_id"] == "freezer-2")
        & (sampled["timestamp"] == pd.Timestamp("2024-03-01 00:05:00")),
        "value",
    ].item()
    assert freezer_value == pytest.approx(-4.8)

    gaps = detect_gaps(readings, max_gap="10min")
    assert list(gaps.columns) == ["sensor_id", "gap_start", "gap_end", "duration"]
    assert set(gaps["sensor_id"]) == {"boiler-1", "roof-9"}
    assert gaps["duration"].max() == pd.Timedelta("15min")


def test_missing_column_is_reported():
    frame = pd.DataFrame(
        {
            "sensor_id": ["x"],
            "timestamp": ["2024-03-01 00:00:00"],
        }
    )

    with pytest.raises(ValueError, match="value"):
        resample_readings(frame)


def test_invalid_frequency_fails():
    readings = load_readings(DATA)

    with pytest.raises(ValueError, match="invalid pandas frequency"):
        resample_readings(readings, freq="nonsense")


def test_gap_detection_allows_empty_after_bad_timestamps():
    frame = pd.DataFrame(
        {
            "sensor_id": ["a", "a"],
            "timestamp": ["nope", "still nope"],
            "value": [1, 2],
        }
    )

    gaps = detect_gaps(frame)
    assert gaps.empty
    assert list(gaps.columns) == ["sensor_id", "gap_start", "gap_end", "duration"]
