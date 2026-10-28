import unittest

from app.dispatch import evaluate_dispatch


class DispatchRuleTests(unittest.TestCase):
    def test_storage_threshold_is_strictly_greater_than_160(self):
        self.assertEqual(evaluate_dispatch(160, "2026-10-24 17:00:00")["mode"], "main-grid")
        self.assertEqual(evaluate_dispatch(160.01, "2026-10-24 17:00:00")["mode"], "renewable-storage")

    def test_storage_window_is_inclusive_from_18_through_22(self):
        for hour in range(18, 23):
            with self.subTest(hour=hour):
                decision = evaluate_dispatch(120, f"2026-10-24 {hour:02d}:00:00")
                self.assertEqual(decision["mode"], "renewable-storage")

    def test_23_returns_to_grid_when_demand_is_at_or_below_threshold(self):
        self.assertEqual(evaluate_dispatch(160, "2026-10-24 23:00:00")["mode"], "main-grid")

    def test_critical_alert_is_independent_and_inclusive(self):
        decision = evaluate_dispatch(200, "2026-10-24 08:00:00")
        self.assertEqual(decision["mode"], "renewable-storage")
        self.assertTrue(decision["critical_alert"])

    def test_wrapped_custom_time_window(self):
        settings = {"storage_threshold_kw": 160, "critical_threshold_kw": 200, "storage_start_hour": 22, "storage_end_hour": 2}
        self.assertEqual(evaluate_dispatch(120, "2026-10-24 23:00:00", settings)["mode"], "renewable-storage")
        self.assertEqual(evaluate_dispatch(120, "2026-10-24 03:00:00", settings)["mode"], "main-grid")

    def test_invalid_values_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dispatch(float("nan"), "2026-10-24 08:00:00")
        with self.assertRaises(ValueError):
            evaluate_dispatch(100, "invalid")


if __name__ == "__main__":
    unittest.main()
