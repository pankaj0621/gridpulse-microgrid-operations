"""Catalyst Stratus and Data Store persistence for AppSail requests."""

from __future__ import annotations

import io
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any


UPLOADS_TABLE = "GridPulseTelemetryUploads"
FORECASTS_TABLE = "GridPulseForecastLogs"


class CatalystStorageConfigurationError(ValueError):
    """Raised when Catalyst storage is selected without required resources."""


def catalyst_storage_is_configured() -> bool:
    return bool(os.getenv("GRIDPULSE_STRATUS_BUCKET", "").strip())


def storage_mode() -> str:
    mode = os.getenv("GRIDPULSE_STORAGE_MODE", "local").strip().lower()
    if mode not in {"local", "catalyst"}:
        raise CatalystStorageConfigurationError("GRIDPULSE_STORAGE_MODE must be 'local' or 'catalyst'.")
    return mode


class CatalystStorage:
    """Request-scoped Catalyst SDK adapter; initialize once for each AppSail request."""

    def __init__(self, request: Any, app: Any | None = None):
        self.bucket_name = os.getenv("GRIDPULSE_STRATUS_BUCKET", "").strip()
        if not self.bucket_name:
            raise CatalystStorageConfigurationError("GRIDPULSE_STRATUS_BUCKET must name an existing Stratus bucket.")
        self.uploads_table_name = os.getenv("GRIDPULSE_DATASTORE_UPLOADS_TABLE", UPLOADS_TABLE).strip()
        self.forecasts_table_name = os.getenv("GRIDPULSE_DATASTORE_FORECASTS_TABLE", FORECASTS_TABLE).strip()
        if not self.uploads_table_name or not self.forecasts_table_name:
            raise CatalystStorageConfigurationError("Catalyst Data Store table names cannot be empty.")

        if app is None:
            try:
                import zcatalyst_sdk
            except ImportError as error:
                raise CatalystStorageConfigurationError("Install zcatalyst-sdk to use Catalyst storage.") from error
            app = zcatalyst_sdk.initialize(req=request)
        self.app = app

    def store_upload(
        self,
        filename: str,
        contents: bytes,
        records: list[dict[str, Any]],
        missing_values_filled: int,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        upload_id = uuid.uuid4().hex
        safe_name = _safe_filename(filename)
        object_key = f"telemetry/{now:%Y/%m}/{upload_id}_{safe_name}"
        latest_timestamp = max(str(record["timestamp"]) for record in records)

        bucket = self.app.stratus().bucket(self.bucket_name)
        bucket.put_object(
            object_key,
            io.BytesIO(contents),
            {
                "content_type": "text/csv",
                "meta_data": {"upload_id": upload_id},
            },
        )

        metadata = {
            "UploadId": upload_id,
            "FileName": safe_name,
            "ObjectKey": object_key,
            "RowCount": len(records),
            "MissingValuesFilled": missing_values_filled,
            "LatestTimestamp": latest_timestamp,
            "CreatedAt": now.isoformat(),
        }
        self.app.datastore().table(self.uploads_table_name).insert_row(metadata)
        return {
            "upload_id": upload_id,
            "rows": len(records),
            "missing_values_filled": missing_values_filled,
            "latest_timestamp": latest_timestamp,
            "object_key": object_key,
        }

    def log_forecast(
        self,
        *,
        model_source: str,
        point_count: int,
        storage_hours: int,
        critical_alerts: int,
        scenario_only: bool,
        first_timestamp: str,
        latest_timestamp: str,
    ) -> str:
        forecast_id = uuid.uuid4().hex
        row = {
            "ForecastId": forecast_id,
            "CreatedAt": datetime.now(timezone.utc).isoformat(),
            "ModelSource": model_source,
            "PointCount": point_count,
            "StorageHours": storage_hours,
            "CriticalAlerts": critical_alerts,
            "ScenarioOnly": scenario_only,
            "FirstTimestamp": first_timestamp,
            "LatestTimestamp": latest_timestamp,
        }
        self.app.datastore().table(self.forecasts_table_name).insert_row(row)
        return forecast_id

    def telemetry_summary(self) -> dict[str, Any]:
        upload_rows = self._all_rows(self.uploads_table_name)
        forecast_rows = self._all_rows(self.forecasts_table_name)
        latest_timestamp = max(
            (str(row.get("LatestTimestamp", "")) for row in upload_rows if row.get("LatestTimestamp")),
            default=None,
        )
        latest_upload = max(
            (str(row.get("CreatedAt", "")) for row in upload_rows if row.get("CreatedAt")),
            default=None,
        )
        return {
            "uploaded_rows": sum(int(row.get("RowCount", 0) or 0) for row in upload_rows),
            "training_rows": 4000,
            "test_rows": 1000,
            "last_timestamp": latest_timestamp,
            "latest_upload": latest_upload,
            "forecast_runs": len(forecast_rows),
            "critical_alerts_logged": sum(int(row.get("CriticalAlerts", 0) or 0) for row in forecast_rows),
        }

    def _all_rows(self, table_name: str) -> list[dict[str, Any]]:
        table = self.app.datastore().table(table_name)
        rows: list[dict[str, Any]] = []
        next_token = None
        visited_tokens: set[str] = set()
        while True:
            page = table.get_paged_rows(next_token, max_rows=200)
            rows.extend(page.get("data", []))
            token = page.get("next_token")
            if not token:
                return rows
            if token in visited_tokens:
                raise RuntimeError("Catalyst Data Store returned an invalid pagination token.")
            visited_tokens.add(token)
            next_token = token


def _safe_filename(filename: str) -> str:
    base_name = PurePosixPath(filename.replace("\\", "/")).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("._")
    return safe_name or "telemetry.csv"
