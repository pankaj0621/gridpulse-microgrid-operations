import os
import unittest
from unittest.mock import Mock, patch

from app.catalyst_storage import CatalystStorage


class FakeTable:
    def __init__(self, pages=None):
        self.inserted = []
        self.pages = list(pages or [])

    def insert_row(self, row):
        self.inserted.append(row)
        return {"ROWID": str(len(self.inserted)), **row}

    def get_paged_rows(self, next_token=None, max_rows=200):
        if self.pages:
            return self.pages.pop(0)
        return {"data": [], "next_token": None}


class FakeApp:
    def __init__(self, tables):
        self.tables = tables
        self.bucket = Mock()
        self.stratus_service = Mock()
        self.stratus_service.bucket.return_value = self.bucket
        self.datastore_service = Mock()
        self.datastore_service.table.side_effect = lambda name: self.tables[name]

    def stratus(self):
        return self.stratus_service

    def datastore(self):
        return self.datastore_service


class CatalystStorageTests(unittest.TestCase):
    def test_upload_saves_csv_to_stratus_and_writes_metadata_to_datastore(self):
        uploads = FakeTable()
        app = FakeApp({"GridPulseTelemetryUploads": uploads, "GridPulseForecastLogs": FakeTable()})
        env = {
            "GRIDPULSE_STRATUS_BUCKET": "gridpulse-data",
            "GRIDPULSE_DATASTORE_UPLOADS_TABLE": "GridPulseTelemetryUploads",
            "GRIDPULSE_DATASTORE_FORECASTS_TABLE": "GridPulseForecastLogs",
        }
        records = [{
            "timestamp": "2026-10-24 10:00:00",
            "ambient_temp_c": 20.0,
            "humidity_pct": 50.0,
            "solar_irradiance_wm2": 100.0,
            "target_demand_kw": 125.0,
        }]
        with patch.dict(os.environ, env, clear=True):
            storage = CatalystStorage(request=object(), app=app)
            result = storage.store_upload("..\\private.csv", b"timestamp,data\n", records, 1)

        self.assertEqual(result["rows"], 1)
        self.assertEqual(result["missing_values_filled"], 1)
        self.assertEqual(len(uploads.inserted), 1)
        self.assertEqual(uploads.inserted[0]["FileName"], "private.csv")
        self.assertEqual(uploads.inserted[0]["RowCount"], 1)
        self.assertTrue(uploads.inserted[0]["ObjectKey"].startswith("telemetry/2026/10/"))
        app.stratus_service.bucket.assert_called_once_with("gridpulse-data")
        upload_args = app.bucket.put_object.call_args.args
        self.assertEqual(upload_args[0], uploads.inserted[0]["ObjectKey"])
        self.assertEqual(upload_args[1].read(), b"timestamp,data\n")
        self.assertEqual(upload_args[2]["content_type"], "text/csv")

    def test_summary_pages_upload_rows_and_aggregates_counts(self):
        uploads = FakeTable([
            {"data": [{"RowCount": 24, "LatestTimestamp": "2026-10-24T23:00:00"}], "next_token": "page-2"},
            {"data": [{"RowCount": 10, "LatestTimestamp": "2026-10-25T09:00:00"}], "next_token": None},
        ])
        forecasts = FakeTable([{
            "data": [{"CriticalAlerts": 2}],
            "next_token": None,
        }])
        app = FakeApp({"GridPulseTelemetryUploads": uploads, "GridPulseForecastLogs": forecasts})
        env = {"GRIDPULSE_STRATUS_BUCKET": "gridpulse-data"}
        with patch.dict(os.environ, env, clear=True):
            summary = CatalystStorage(request=object(), app=app).telemetry_summary()

        self.assertEqual(summary["uploaded_rows"], 34)
        self.assertEqual(summary["forecast_runs"], 1)
        self.assertEqual(summary["critical_alerts_logged"], 2)
        self.assertEqual(summary["last_timestamp"], "2026-10-25T09:00:00")
        self.assertEqual(summary["training_rows"], 4000)
        self.assertEqual(summary["test_rows"], 1000)

    def test_forecast_audit_is_written_to_configured_datastore_table(self):
        forecasts = FakeTable()
        app = FakeApp({"GridPulseTelemetryUploads": FakeTable(), "GridPulseForecastLogs": forecasts})
        env = {"GRIDPULSE_STRATUS_BUCKET": "gridpulse-data"}
        with patch.dict(os.environ, env, clear=True):
            CatalystStorage(request=object(), app=app).log_forecast(
                model_source="quickml",
                point_count=24,
                storage_hours=7,
                critical_alerts=2,
                scenario_only=False,
                first_timestamp="2026-10-24 00:00:00",
                latest_timestamp="2026-10-24 23:00:00",
            )

        self.assertEqual(len(forecasts.inserted), 1)
        self.assertEqual(forecasts.inserted[0]["ModelSource"], "quickml")
        self.assertEqual(forecasts.inserted[0]["CriticalAlerts"], 2)
        self.assertFalse(forecasts.inserted[0]["ScenarioOnly"])


if __name__ == "__main__":
    unittest.main()
