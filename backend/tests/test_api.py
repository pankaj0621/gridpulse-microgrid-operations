import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            "GRIDPULSE_DATABASE_PATH": os.path.join(self.temp_dir.name, "test.sqlite3"),
            "GRIDPULSE_STORAGE_MODE": "local",
            "QUICKML_ENDPOINT_URL": "",
            "QUICKML_ENDPOINT_KEY": "",
            "QUICKML_ORG_ID": "",
            "QUICKML_REFRESH_TOKEN": "",
            "QUICKML_CLIENT_ID": "",
            "QUICKML_CLIENT_SECRET": "",
        })
        self.environment.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.environment.stop()
        self.temp_dir.cleanup()

    def test_health_identifies_unconfigured_quickml(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertFalse(response.json()["quickml_configured"])

    def test_health_reports_missing_quickml_environment_names_without_values(self):
        values = {
            "QUICKML_ENDPOINT_URL": "https://quickml.example/predict",
            "QUICKML_ENDPOINT_KEY": "",
            "QUICKML_ORG_ID": "",
            "QUICKML_REFRESH_TOKEN": "",
            "QUICKML_CLIENT_ID": "",
            "QUICKML_CLIENT_SECRET": "",
        }
        with patch.dict(os.environ, values, clear=False):
            response = self.client.get("/api/health")
        self.assertFalse(response.json()["quickml_configured"])
        self.assertIn("QUICKML_REFRESH_TOKEN", response.json()["quickml_missing_configuration"])
        self.assertNotIn("client-secret", response.text)

    def test_forecast_returns_one_result_per_hour_and_marks_demo_inputs(self):
        rows = [
            {
                "timestamp": f"2026-10-24 {hour:02d}:00:00",
                "ambient_temp_c": 25,
                "humidity_pct": 55,
                "solar_irradiance_wm2": 100,
            }
            for hour in range(24)
        ]
        response = self.client.post("/api/forecast", json={"rows": rows, "scenario_only": True})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload["predictions"]), 24)
        self.assertEqual(payload["model_source"], "demo-fallback")
        self.assertIn("illustrative local scenario", payload["notice"])
        self.assertEqual(payload["predictions"][18]["mode"], "renewable-storage")
        self.assertEqual(self.client.get("/api/telemetry/summary").json()["forecast_runs"], 1)

    def test_forecast_fails_explicitly_when_quickml_url_has_incomplete_auth(self):
        rows = [
            {
                "timestamp": f"2026-10-24 {hour:02d}:00:00",
                "ambient_temp_c": 25,
                "humidity_pct": 55,
                "solar_irradiance_wm2": 100,
            }
            for hour in range(24)
        ]
        values = {
            "QUICKML_ENDPOINT_URL": "https://quickml.example/predict",
            "QUICKML_ENDPOINT_KEY": "",
            "QUICKML_ORG_ID": "",
            "QUICKML_REFRESH_TOKEN": "",
            "QUICKML_CLIENT_ID": "",
            "QUICKML_CLIENT_SECRET": "",
        }
        with patch.dict(os.environ, values, clear=False):
            response = self.client.post("/api/forecast", json={"rows": rows})
        self.assertEqual(response.status_code, 502)

    def test_catalyst_storage_does_not_silently_write_to_local_sqlite_when_unconfigured(self):
        csv = "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n2026-10-24 10:00:00,20,50,100\n"
        values = {"GRIDPULSE_STORAGE_MODE": "catalyst", "GRIDPULSE_STRATUS_BUCKET": ""}
        with patch.dict(os.environ, values, clear=False):
            response = self.client.post("/api/telemetry/upload", files={"file": ("telemetry.csv", csv, "text/csv")})
            summary = self.client.get("/api/telemetry/summary")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(summary.status_code, 503)

    def test_forecast_rejects_a_partial_hourly_window(self):
        response = self.client.post("/api/forecast", json={"rows": [{"timestamp": "2026-10-24 00:00:00"}]})
        self.assertEqual(response.status_code, 422)

    def test_upload_cleans_and_persists_csv_rows(self):
        csv = (
            "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2,target_demand_kw\n"
            "2026-10-24 10:00:00,20,50,100,125\n"
            "2026-10-24 11:00:00,,70,200,130\n"
        )
        response = self.client.post("/api/telemetry/upload", files={"file": ("telemetry.csv", csv, "text/csv")})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["rows"], 2)
        self.assertEqual(response.json()["missing_values_filled"], 1)
        self.assertEqual(self.client.get("/api/telemetry/summary").json()["uploaded_rows"], 2)

    def test_upload_rejects_duplicate_hours(self):
        csv = (
            "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n"
            "2026-10-24 10:00:00,20,50,100\n"
            "2026-10-24 10:00:00,21,52,110\n"
        )
        response = self.client.post("/api/telemetry/upload", files={"file": ("duplicate.csv", csv, "text/csv")})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
