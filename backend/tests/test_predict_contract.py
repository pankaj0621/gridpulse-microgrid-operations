import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from predict import predict


class PredictContractTests(unittest.TestCase):
    def test_sample_input_keeps_one_finite_prediction_per_timestamp(self):
        sample = pd.read_csv(PROJECT_ROOT / "sample_test_input.csv")
        predictions = predict(sample)
        self.assertIsInstance(predictions, np.ndarray)
        self.assertEqual(len(predictions), len(sample))
        self.assertTrue(np.isfinite(predictions).all())

    def test_missing_weather_features_are_imputed_without_mutating_input(self):
        data = pd.DataFrame({
            "timestamp": ["2026-10-24 10:00:00", "2026-10-24 11:00:00"],
            "ambient_temp_c": [20.0, np.nan],
            "humidity_pct": [40.0, 50.0],
            "solar_irradiance_wm2": [0.0, 100.0],
        })
        original = data.copy(deep=True)
        predictions = predict(data)
        self.assertEqual(len(predictions), 2)
        self.assertTrue(np.isfinite(predictions).all())
        pd.testing.assert_frame_equal(data, original)

    def test_invalid_timestamp_fails_clearly(self):
        data = pd.DataFrame({
            "timestamp": ["not-a-timestamp"],
            "ambient_temp_c": [20.0],
            "humidity_pct": [50.0],
            "solar_irradiance_wm2": [0.0],
        })
        with self.assertRaisesRegex(ValueError, "invalid timestamp"):
            predict(data)


if __name__ == "__main__":
    unittest.main()
