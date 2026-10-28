"""HackSphere inference contract with a QuickML adapter and safe local fallback."""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from backend.app.quickml_client import QuickMLClient, QuickMLConfig


FEATURE_COLUMNS = ("ambient_temp_c", "humidity_pct", "solar_irradiance_wm2")
REQUIRED_COLUMNS = ("timestamp", *FEATURE_COLUMNS)
MISSING_DEFAULTS = {"ambient_temp_c": 22.0, "humidity_pct": 50.0, "solar_irradiance_wm2": 0.0}


def _prepare_input(input_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    missing = [column for column in REQUIRED_COLUMNS if column not in input_df.columns]
    if missing:
        raise ValueError(f"Input is missing required columns: {', '.join(missing)}.")
    features = input_df.loc[:, REQUIRED_COLUMNS].copy()
    timestamps = pd.to_datetime(features["timestamp"], errors="coerce")
    if timestamps.isna().any():
        raise ValueError("Input contains an invalid timestamp.")
    for column in FEATURE_COLUMNS:
        values = pd.to_numeric(features[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        fill_value = float(values.median()) if values.notna().any() else MISSING_DEFAULTS[column]
        features[column] = values.fillna(fill_value).astype(float)
    features["timestamp"] = input_df["timestamp"].astype(str).to_numpy()
    return features, timestamps


def _quickml_predictions(features: pd.DataFrame) -> np.ndarray:
    values = QuickMLClient.from_environment().predict(features.to_dict(orient="records"))
    return np.asarray(values, dtype=float).reshape(-1)


def predict(input_df: pd.DataFrame) -> np.ndarray:
    """Return one finite demand estimate per weather row, preserving row order."""
    if not isinstance(input_df, pd.DataFrame):
        raise TypeError("predict() expects a pandas DataFrame.")
    if input_df.empty:
        return np.asarray([], dtype=float)
    features, timestamps = _prepare_input(input_df)

    if QuickMLConfig.from_environment().enabled:
        return _quickml_predictions(features)

    hours = timestamps.dt.hour
    base_load = 120.0 + 30.0 * np.sin(2 * np.pi * (hours - 6) / 24)
    cooling_load = np.maximum(0.0, features["ambient_temp_c"].to_numpy() - 24.0) * 8.5
    return np.asarray(base_load.to_numpy() + cooling_load, dtype=float)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run demand forecasts for a telemetry CSV.")
    parser.add_argument("--input", default="sample_test_input.csv", help="Input CSV with timestamp and weather features.")
    parser.add_argument("--output", default="predictions.csv", help="Output CSV path.")
    arguments = parser.parse_args()
    input_df = pd.read_csv(arguments.input)
    predictions = predict(input_df)
    output = pd.DataFrame({
        "timestamp": input_df["timestamp"].astype(str),
        "target_demand_kw": predictions,
    })
    output.to_csv(arguments.output, index=False, float_format="%.2f")
    print(f"Wrote {len(output)} timestamp-aligned predictions to {arguments.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
