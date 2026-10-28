import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def database_path() -> Path:
    configured = os.getenv("GRIDPULSE_DATABASE_PATH")
    return Path(configured) if configured else Path(__file__).resolve().parents[1] / ".data" / "gridpulse.sqlite3"


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS telemetry (
            timestamp TEXT PRIMARY KEY,
            ambient_temp_c REAL NOT NULL,
            humidity_pct REAL NOT NULL,
            solar_irradiance_wm2 REAL NOT NULL,
            target_demand_kw REAL,
            uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS forecast_logs (
            forecast_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            model_source TEXT NOT NULL,
            point_count INTEGER NOT NULL,
            storage_hours INTEGER NOT NULL,
            critical_alerts INTEGER NOT NULL,
            scenario_only INTEGER NOT NULL,
            first_timestamp TEXT NOT NULL,
            latest_timestamp TEXT NOT NULL
        )"""
    )
    return connection


@contextmanager
def connection_scope():
    connection = connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def store_telemetry(records: list[dict[str, Any]]) -> int:
    with connection_scope() as connection:
        connection.executemany(
            """INSERT INTO telemetry (timestamp, ambient_temp_c, humidity_pct, solar_irradiance_wm2, target_demand_kw)
               VALUES (:timestamp, :ambient_temp_c, :humidity_pct, :solar_irradiance_wm2, :target_demand_kw)
               ON CONFLICT(timestamp) DO UPDATE SET
                   ambient_temp_c=excluded.ambient_temp_c,
                   humidity_pct=excluded.humidity_pct,
                   solar_irradiance_wm2=excluded.solar_irradiance_wm2,
                   target_demand_kw=excluded.target_demand_kw,
                   uploaded_at=CURRENT_TIMESTAMP""",
            records,
        )
    return len(records)


def telemetry_summary() -> dict[str, Any]:
    with connection_scope() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS row_count, MAX(timestamp) AS last_timestamp, MAX(uploaded_at) AS latest_upload FROM telemetry"
        ).fetchone()
        forecasts = connection.execute(
            "SELECT COUNT(*) AS run_count, COALESCE(SUM(critical_alerts), 0) AS alert_count FROM forecast_logs"
        ).fetchone()
    return {
        "uploaded_rows": row["row_count"],
        "training_rows": 4000,
        "test_rows": 1000,
        "last_timestamp": row["last_timestamp"],
        "latest_upload": row["latest_upload"],
        "forecast_runs": forecasts["run_count"],
        "critical_alerts_logged": forecasts["alert_count"],
    }


def log_forecast(
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
    created_at = datetime.now(timezone.utc).isoformat()
    with connection_scope() as connection:
        connection.execute(
            """INSERT INTO forecast_logs (
                forecast_id, created_at, model_source, point_count, storage_hours,
                critical_alerts, scenario_only, first_timestamp, latest_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                forecast_id,
                created_at,
                model_source,
                point_count,
                storage_hours,
                critical_alerts,
                int(scenario_only),
                first_timestamp,
                latest_timestamp,
            ),
        )
    return forecast_id


def latest_weather_rows(limit: int = 24) -> list[dict[str, Any]]:
    with connection_scope() as connection:
        rows = connection.execute(
            "SELECT timestamp, ambient_temp_c, humidity_pct, solar_irradiance_wm2 FROM telemetry ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]
