import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Check, Database, X } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import { OverviewPage } from './components/OverviewPage';
import { ForecastsPage } from './components/ForecastsPage';
import { TelemetryPage } from './components/TelemetryPage';
import { ControlsPage } from './components/ControlsPage';
import { createDemoForecast } from './lib/demo';
import { DEFAULT_SETTINGS } from './lib/dispatch';
import { fetchTelemetrySummary, requestForecast, uploadTelemetry } from './lib/api';
import type { DispatchSettings, ForecastResult, PageId, TelemetrySummary, WeatherInput } from './types';

const requiredHeaders = ['timestamp', 'ambient_temp_c', 'humidity_pct', 'solar_irradiance_wm2'];

const initialSummary: TelemetrySummary = { uploaded_rows: 0, training_rows: 4000, test_rows: 1000 };

function parseCsvLine(line: string): string[] {
  const fields: string[] = [];
  let value = '';
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"' && line[index + 1] === '"' && quoted) { value += '"'; index += 1; }
    else if (character === '"') quoted = !quoted;
    else if (character === ',' && !quoted) { fields.push(value.trim()); value = ''; }
    else value += character;
  }
  fields.push(value.trim());
  return fields;
}

function stageForecastRows(text: string, headers: string[]): WeatherInput[] {
  const indices = Object.fromEntries(requiredHeaders.map((name) => [name, headers.indexOf(name)]));
  return text.split(/\r?\n/).slice(1).filter((line) => line.trim()).slice(0, 24).map((line) => {
    const cells = parseCsvLine(line);
    const read = (key: string): string => cells[indices[key]] ?? '';
    const number = (key: string): number | null => {
      const value = read(key);
      if (!value) return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };
    return {
      timestamp: read('timestamp'),
      ambient_temp_c: number('ambient_temp_c'),
      humidity_pct: number('humidity_pct'),
      solar_irradiance_wm2: number('solar_irradiance_wm2'),
    };
  });
}

function loadSettings(): DispatchSettings {
  try {
    const stored = localStorage.getItem('gridpulse-settings-v1');
    if (!stored) return DEFAULT_SETTINGS;
    const candidate = { ...DEFAULT_SETTINGS, ...JSON.parse(stored) } as DispatchSettings;
    if (
      !Number.isFinite(candidate.storageThresholdKw) ||
      !Number.isFinite(candidate.criticalThresholdKw) ||
      !Number.isInteger(candidate.storageStartHour) ||
      !Number.isInteger(candidate.storageEndHour) ||
      !Number.isFinite(candidate.startingSocPercent)
    ) return DEFAULT_SETTINGS;
    return candidate;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export default function App() {
  const [activePage, setActivePage] = useState<PageId>('overview');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [settings, setSettings] = useState<DispatchSettings>(loadSettings);
  const [result, setResult] = useState<ForecastResult>(() => createDemoForecast(loadSettings()));
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ message: string; kind: 'success' | 'warning' | 'error' } | null>(null);
  const [summary, setSummary] = useState<TelemetrySummary>(initialSummary);
  const [stagedRows, setStagedRows] = useState<WeatherInput[]>([]);
  const [uploadMessage, setUploadMessage] = useState('');
  const [uploadError, setUploadError] = useState(false);
  const modelLabel = result.model_source === 'quickml' ? 'QuickML' : 'Demo fallback';

  useEffect(() => {
    localStorage.setItem('gridpulse-settings-v1', JSON.stringify(settings));
  }, [settings]);

  useEffect(() => {
    const controller = new AbortController();
    fetchTelemetrySummary(controller.signal).then(setSummary).catch(() => undefined);
    return () => controller.abort();
  }, []);

  const showToast = useCallback((message: string, kind: 'success' | 'warning' | 'error' = 'success') => {
    setToast({ message, kind });
    window.setTimeout(() => setToast(null), 5200);
  }, []);

  const navigate = useCallback((page: PageId) => {
    setActivePage(page);
    setMobileNavOpen(false);
  }, []);

  const runForecast = useCallback(async () => {
    setBusy(true);
    try {
      const next = await requestForecast(settings, stagedRows.length === 24 ? stagedRows : undefined);
      if (!Array.isArray(next.predictions) || next.predictions.length !== 24) {
        throw new Error('Forecast service must return 24 hourly predictions.');
      }
      setResult(next);
      showToast(next.model_source === 'quickml' ? 'QuickML forecast updated.' : 'Scenario forecast refreshed.', 'success');
    } catch {
      setResult(createDemoForecast(settings));
      showToast('Backend unavailable. Showing the labeled scenario forecast; no QuickML result was received.', 'warning');
    } finally {
      setBusy(false);
    }
  }, [settings, showToast, stagedRows]);

  const uploadFile = useCallback(async (file: File) => {
    setUploadMessage('');
    setUploadError(false);
    if (!file.name.toLowerCase().endsWith('.csv') && file.type !== 'text/csv') {
      setUploadError(true);
      setUploadMessage('Choose a CSV file to continue.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadError(true);
      setUploadMessage('File is larger than the 10 MB upload limit.');
      return;
    }
    let text: string;
    try {
      text = await file.text();
    } catch {
      setUploadError(true);
      setUploadMessage('The selected file could not be read.');
      return;
    }
    const headers = (text.split(/\r?\n/, 1)[0] ?? '').replace(/^\uFEFF/, '').split(',').map((header) => header.trim().replace(/^"|"$/g, ''));
    const missing = requiredHeaders.filter((header) => !headers.includes(header));
    const rows = text.split(/\r?\n/).filter((line) => line.trim()).length - 1;
    if (missing.length) {
      setUploadError(true);
      setUploadMessage(`CSV is missing required fields: ${missing.join(', ')}.`);
      return;
    }
    if (rows < 1) {
      setUploadError(true);
      setUploadMessage('CSV contains headers but no telemetry rows.');
      return;
    }
    const preparedRows = stageForecastRows(text, headers);
    setStagedRows(preparedRows);
    try {
      const uploaded = await uploadTelemetry(file);
      if (!Number.isFinite(uploaded.rows) || uploaded.rows < 1) throw new Error('Upload service did not confirm saved rows.');
      const freshSummary = await fetchTelemetrySummary().catch(() => null);
      if (freshSummary) setSummary(freshSummary);
      else setSummary((current) => ({ ...current, uploaded_rows: current.uploaded_rows + uploaded.rows, last_timestamp: uploaded.latest_timestamp ?? current.last_timestamp, latest_upload: 'just now' }));
      setUploadMessage(`${uploaded.rows.toLocaleString('en-US')} telemetry rows stored. ${preparedRows.length} rows staged for the next forecast.`);
      showToast('Telemetry file accepted by the API.', 'success');
    } catch (error) {
      setUploadError(true);
      const detail = error instanceof Error ? ` ${error.message}` : '';
      setUploadMessage(`${file.name} passed the local schema check, but the API could not store it. Nothing was stored.${detail}`);
    }
  }, [showToast]);

  const exportForecast = useCallback(() => {
    const csv = [
      'timestamp,target_demand_kw,grid_mode,critical_alert',
      ...result.predictions.map((point) => `${point.timestamp},${point.predicted_demand_kw.toFixed(2)},${point.mode},${point.critical_alert}`),
    ].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'gridpulse-24-hour-forecast.csv';
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast('Forecast CSV downloaded.');
  }, [result.predictions, showToast]);

  const page = useMemo(() => {
    if (activePage === 'forecasts') return <ForecastsPage result={result} settings={settings} onExport={exportForecast} />;
    if (activePage === 'telemetry') return <TelemetryPage summary={summary} stagedRows={stagedRows.length} uploadMessage={uploadMessage} uploadError={uploadError} onUpload={uploadFile} />;
    if (activePage === 'controls') return <ControlsPage settings={settings} onSettingsChange={setSettings} onSave={() => showToast('Scenario settings saved in this browser.')} />;
    return <OverviewPage result={result} settings={settings} onOpenForecasts={() => navigate('forecasts')} onOpenTelemetry={() => navigate('telemetry')} />;
  }, [activePage, exportForecast, navigate, result, settings, showToast, summary, uploadError, uploadFile, uploadMessage]);

  return (
    <div className="app-frame">
      <div className={`app-backdrop${mobileNavOpen ? ' backdrop-open' : ''}`} onClick={() => setMobileNavOpen(false)} aria-hidden="true" />
      <Sidebar activePage={activePage} onNavigate={navigate} open={mobileNavOpen} modelLabel={modelLabel} />
      <main className="main-shell">
        <Topbar activePage={activePage} onMenu={() => setMobileNavOpen(true)} onBuildForecast={runForecast} busy={busy} modelLabel={modelLabel} />
        <div className="main-scroll">{page}</div>
        <footer className="app-footer"><span><Database size={13} /> GRIDPULSE MICROGRID CONTROL ROOM</span><span>DEMAND FORECASTING <i /> CATALYST SLATE READY</span></footer>
      </main>
      {toast && <div className={`toast toast-${toast.kind}`} role="status"><span className="toast-icon">{toast.kind === 'error' ? <X size={16} /> : toast.kind === 'warning' ? <AlertTriangle size={16} /> : <Check size={16} />}</span><span>{toast.message}</span><button onClick={() => setToast(null)} type="button" aria-label="Dismiss notification"><X size={15} /></button></div>}
      <div className="ambient-orb ambient-orb-one" aria-hidden="true" /><div className="ambient-orb ambient-orb-two" aria-hidden="true" />
    </div>
  );
}
