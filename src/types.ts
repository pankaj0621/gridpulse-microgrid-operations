export type PageId = 'overview' | 'forecasts' | 'telemetry' | 'controls';
export type GridMode = 'main-grid' | 'renewable-storage';
export type ModelSource = 'quickml' | 'demo-fallback';

export interface DispatchSettings {
  storageThresholdKw: number;
  criticalThresholdKw: number;
  storageStartHour: number;
  storageEndHour: number;
  startingSocPercent: number;
}

export interface DispatchDecision {
  mode: GridMode;
  criticalAlert: boolean;
  reasons: string[];
}

export interface ForecastPoint {
  timestamp: string;
  ambient_temp_c: number;
  humidity_pct: number;
  solar_irradiance_wm2: number;
  predicted_demand_kw: number;
  mode: GridMode;
  critical_alert: boolean;
  reasons: string[];
}

export interface WeatherInput {
  timestamp: string;
  ambient_temp_c: number | null;
  humidity_pct: number | null;
  solar_irradiance_wm2: number | null;
}

export interface ForecastResult {
  predictions: ForecastPoint[];
  model_source: ModelSource;
  notice?: string;
  simulated_soc_percent: number;
}

export interface TelemetrySummary {
  uploaded_rows: number;
  training_rows: number;
  test_rows: number;
  last_timestamp?: string | null;
  latest_upload?: string | null;
}
