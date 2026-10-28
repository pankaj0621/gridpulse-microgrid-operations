import type { DispatchSettings, ForecastResult, TelemetrySummary, WeatherInput } from '../types';
import { createDemoForecast } from './demo';

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

async function readResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as T & { detail?: string };
  if (!response.ok) {
    throw new Error(payload.detail ?? `Request failed with status ${response.status}.`);
  }
  return payload;
}

export async function requestForecast(
  settings: DispatchSettings,
  stagedRows?: WeatherInput[],
  signal?: AbortSignal,
): Promise<ForecastResult> {
  const fallback = createDemoForecast(settings);
  const weatherRows = stagedRows?.length === 24 ? stagedRows : fallback.predictions.map((point) => ({
    timestamp: point.timestamp,
    ambient_temp_c: point.ambient_temp_c,
    humidity_pct: point.humidity_pct,
    solar_irradiance_wm2: point.solar_irradiance_wm2,
  }));
  const backendSettings = {
    storage_threshold_kw: settings.storageThresholdKw,
    critical_threshold_kw: settings.criticalThresholdKw,
    storage_start_hour: settings.storageStartHour,
    storage_end_hour: settings.storageEndHour,
    starting_soc_percent: settings.startingSocPercent,
  };
  const response = await fetch(`${API_BASE}/api/forecast`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ rows: weatherRows, settings: backendSettings, scenario_only: stagedRows?.length !== 24 }),
    signal,
  });
  return readResponse<ForecastResult>(response);
}

export async function uploadTelemetry(file: File): Promise<{ rows: number; latest_timestamp?: string }> {
  const body = new FormData();
  body.append('file', file);
  const response = await fetch(`${API_BASE}/api/telemetry/upload`, { method: 'POST', body });
  return readResponse(response);
}

export async function fetchTelemetrySummary(signal?: AbortSignal): Promise<TelemetrySummary> {
  const response = await fetch(`${API_BASE}/api/telemetry/summary`, { signal });
  return readResponse<TelemetrySummary>(response);
}
