import { DEFAULT_SETTINGS, evaluateDispatch } from './dispatch';
import type { DispatchSettings, ForecastPoint, ForecastResult } from '../types';

const demandProfile = [
  92, 94, 96, 100, 106, 111, 117, 122, 130, 136, 144, 151,
  155, 158, 163, 168, 172, 176.4, 176.4, 193.8, 211, 204, 186, 164,
];

function localTimestamp(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 19).replace('T', ' ');
}

export function createDemoForecast(
  settings: DispatchSettings = DEFAULT_SETTINGS,
  date = new Date(),
): ForecastResult {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  const predictions: ForecastPoint[] = demandProfile.map((demand, index) => {
    const timestamp = new Date(start.getTime() + index * 3_600_000);
    const hour = timestamp.getHours();
    const decision = evaluateDispatch(demand, localTimestamp(timestamp), settings);
    return {
      timestamp: localTimestamp(timestamp),
      ambient_temp_c: Number((18 + 11 * Math.sin(((hour - 7) / 24) * Math.PI * 2)).toFixed(1)),
      humidity_pct: Number((60 - 14 * Math.sin(((hour - 7) / 24) * Math.PI * 2)).toFixed(1)),
      solar_irradiance_wm2: Math.max(0, Math.round(680 * Math.sin(((hour - 6) / 12) * Math.PI))),
      predicted_demand_kw: demand,
      mode: decision.mode,
      critical_alert: decision.criticalAlert,
      reasons: decision.reasons,
    };
  });
  return {
    predictions,
    model_source: 'demo-fallback',
    notice: 'Illustrative scenario only. Connect a published QuickML endpoint for model-backed forecasts.',
    simulated_soc_percent: Math.max(0, settings.startingSocPercent - 11),
  };
}

export function maxForecast(points: ForecastPoint[]): ForecastPoint | undefined {
  return points.reduce<ForecastPoint | undefined>(
    (peak, point) => (!peak || point.predicted_demand_kw > peak.predicted_demand_kw ? point : peak),
    undefined,
  );
}

export function formatHour(timestamp: string): string {
  return timestamp.match(/(?:T|\s)(\d{2}:\d{2})/)?.[1] ?? '--:--';
}

export function formatDate(date = new Date()): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  }).format(date);
}
