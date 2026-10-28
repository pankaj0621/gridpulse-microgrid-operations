import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from app.dispatch import evaluate_dispatch
from app.catalyst_storage import (
    CatalystStorage,
    CatalystStorageConfigurationError,
    catalyst_storage_is_configured,
    storage_mode,
)
from app.quickml_client import QuickMLClient, QuickMLConfig
from app.store import log_forecast, store_telemetry, telemetry_summary
from app.telemetry import clean_forecast_rows, parse_telemetry_csv


backend_env = Path(__file__).resolve().parent / ".env"
workspace_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(workspace_env if workspace_env.is_file() else backend_env, override=False)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app = FastAPI(title="GridPulse Forecast API", version="1.0.0", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


class WeatherRow(BaseModel):
    timestamp: str = Field(min_length=16, max_length=64)
    ambient_temp_c: float | None = None
    humidity_pct: float | None = None
    solar_irradiance_wm2: float | None = None


class ForecastSettings(BaseModel):
    storage_threshold_kw: float = Field(default=160, gt=0, le=1000)
    critical_threshold_kw: float = Field(default=200, gt=0, le=2000)
    storage_start_hour: int = Field(default=18, ge=0, le=23)
    storage_end_hour: int = Field(default=22, ge=0, le=23)
    starting_soc_percent: float = Field(default=82, ge=0, le=100)


class ForecastRequest(BaseModel):
    rows: list[WeatherRow] = Field(min_length=24, max_length=24)
    settings: ForecastSettings = Field(default_factory=ForecastSettings)
    scenario_only: bool = False


@app.get("/api/health")
def health() -> dict[str, Any]:
    quickml = QuickMLConfig.from_environment()
    try:
        current_storage_mode = storage_mode()
    except CatalystStorageConfigurationError:
        current_storage_mode = "invalid"
    return {
        "status": "ok",
        "service": "gridpulse",
        "quickml_configured": quickml.configured,
        "quickml_enabled": quickml.enabled,
        "quickml_missing_configuration": quickml.missing_fields if quickml.enabled else [],
        "storage_mode": current_storage_mode,
        "storage_configured": current_storage_mode == "local" or catalyst_storage_is_configured(),
    }


@app.get("/api/telemetry/summary")
def get_telemetry_summary(request: Request) -> dict[str, Any]:
    try:
        if storage_mode() == "catalyst":
            return CatalystStorage(request).telemetry_summary()
        return telemetry_summary()
    except CatalystStorageConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Catalyst storage is unavailable. Check the AppSail resource configuration.") from error


@app.post("/api/telemetry/upload")
async def upload_telemetry(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a CSV file.")
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV exceeds the 10 MB limit.")
    try:
        text = contents.decode("utf-8-sig")
        records, filled = parse_telemetry_csv(text)
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="CSV must use UTF-8 encoding.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    try:
        if storage_mode() == "catalyst":
            return CatalystStorage(request).store_upload(file.filename, contents, records, filled)
        stored = store_telemetry(records)
        return {
            "rows": stored,
            "missing_values_filled": filled,
            "latest_timestamp": max(record["timestamp"] for record in records),
        }
    except CatalystStorageConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Telemetry could not be persisted. Check the configured storage services.") from error


def fallback_predict(rows: list[dict[str, Any]]) -> list[float]:
    predictions: list[float] = []
    for row in rows:
        timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        hour = timestamp.hour
        base_load = 120.0 + 30.0 * math.sin(2 * math.pi * (hour - 6) / 24)
        cooling_load = max(0.0, float(row["ambient_temp_c"]) - 24.0) * 8.5
        predictions.append(base_load + cooling_load)
    return predictions


def quickml_predict(rows: list[dict[str, Any]]) -> list[float]:
    config = QuickMLConfig.from_environment()
    if not config.enabled:
        return fallback_predict(rows)
    try:
        return QuickMLClient(config).predict(rows)
    except (requests.RequestException, ValueError, TypeError) as error:
        raise HTTPException(status_code=502, detail="QuickML inference failed. Check the configured endpoint and response contract.") from error


@app.post("/api/forecast")
async def forecast(request: Request) -> dict[str, Any]:
    try:
        forecast_request = ForecastRequest.model_validate_json(await request.body())
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Request body must be valid forecast JSON.") from error

    raw_rows = [row.model_dump() for row in forecast_request.rows]
    try:
        rows, filled = clean_forecast_rows(raw_rows)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    predictions = quickml_predict(rows)

    settings = forecast_request.settings.model_dump()
    decisions = [
        evaluate_dispatch(demand, row["timestamp"], settings)
        for row, demand in zip(rows, predictions, strict=True)
    ]
    forecast_points = []
    for row, demand, decision in zip(rows, predictions, decisions, strict=True):
        forecast_points.append({
            **row,
            "predicted_demand_kw": round(demand, 2),
            "mode": decision["mode"],
            "critical_alert": decision["critical_alert"],
            "reasons": decision["reasons"],
        })

    storage_hours = sum(decision["mode"] == "renewable-storage" for decision in decisions)
    simulated_soc = max(0.0, forecast_request.settings.starting_soc_percent - min(15.0, storage_hours * 1.8))
    model_source = "quickml" if QuickMLConfig.from_environment().enabled else "demo-fallback"
    notice = None if model_source == "quickml" else "QuickML is not configured. This output uses the starter kit's deterministic baseline formula."
    if forecast_request.scenario_only:
        scenario_notice = "Weather inputs are an illustrative local scenario, not a live site forecast."
        notice = f"{notice} {scenario_notice}" if notice else scenario_notice
    if filled:
        notice = f"{filled} missing weather values were median-imputed." if notice is None else f"{notice} {filled} missing weather values were median-imputed."
    critical_alert_count = sum(decision["critical_alert"] for decision in decisions)
    try:
        if storage_mode() == "catalyst":
            forecast_id = CatalystStorage(request).log_forecast(
                model_source=model_source,
                point_count=len(forecast_points),
                storage_hours=storage_hours,
                critical_alerts=critical_alert_count,
                scenario_only=forecast_request.scenario_only,
                first_timestamp=rows[0]["timestamp"],
                latest_timestamp=rows[-1]["timestamp"],
            )
        else:
            forecast_id = log_forecast(
                model_source=model_source,
                point_count=len(forecast_points),
                storage_hours=storage_hours,
                critical_alerts=critical_alert_count,
                scenario_only=forecast_request.scenario_only,
                first_timestamp=rows[0]["timestamp"],
                latest_timestamp=rows[-1]["timestamp"],
            )
    except CatalystStorageConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Forecast was generated but its audit record could not be stored.") from error
    return {
        "forecast_id": forecast_id,
        "predictions": forecast_points,
        "model_source": model_source,
        "notice": notice,
        "simulated_soc_percent": round(simulated_soc, 1),
    }
