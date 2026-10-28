import unittest

from app.telemetry import parse_telemetry_csv


class TelemetryCsvTests(unittest.TestCase):
    def test_missing_weather_values_use_column_median_and_preserve_timestamps(self):
        content = (
            "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n"
            "2026-10-24 10:00:00,20,50,100\n"
            "2026-10-24 11:00:00,,70,200\n"
        )
        rows, filled = parse_telemetry_csv(content)
        self.assertEqual(rows[1]["timestamp"], "2026-10-24 11:00:00")
        self.assertEqual(rows[1]["ambient_temp_c"], 20.0)
        self.assertEqual(filled, 1)

    def test_duplicate_timestamps_are_rejected(self):
        content = (
            "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n"
            "2026-10-24 10:00:00,20,50,100\n"
            "2026-10-24 10:00:00,21,55,150\n"
        )
        with self.assertRaises(ValueError):
            parse_telemetry_csv(content)

    def test_required_feature_headers_are_enforced(self):
        with self.assertRaises(ValueError):
            parse_telemetry_csv("timestamp,ambient_temp_c\n2026-10-24 10:00:00,20\n")

    def test_nonnumeric_values_and_invalid_timestamp_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_telemetry_csv(
                "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n"
                "2026-10-24 10:00:00,hot,50,100\n"
            )
        with self.assertRaises(ValueError):
            parse_telemetry_csv(
                "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n"
                "later,20,50,100\n"
            )


if __name__ == "__main__":
    unittest.main()
