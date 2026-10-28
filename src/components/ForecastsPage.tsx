import { ArrowDownToLine, ArrowUpRight, CalendarClock, CircleAlert, Gauge, Layers3 } from 'lucide-react';
import { IsometricChart } from './IsometricChart';
import { formatHour, maxForecast } from '../lib/demo';
import type { DispatchSettings, ForecastResult } from '../types';

interface ForecastsPageProps {
  result: ForecastResult;
  settings: DispatchSettings;
  onExport: () => void;
}

export function ForecastsPage({ result, settings, onExport }: ForecastsPageProps) {
  const peak = maxForecast(result.predictions);
  return (
    <div className="page-content">
      <div className="page-heading page-heading-compact">
        <div><div className="eyebrow"><span className="eyebrow-line" />MODEL OUTPUT <span>/</span> FORECASTS</div><h1>Forecast <span>workspace.</span></h1><p>Inspect the hourly signal and the rules that shape each grid decision.</p></div>
        <button className="button button-secondary" onClick={onExport} type="button"><ArrowDownToLine size={16} />Export CSV</button>
      </div>
      {result.notice && <div className="demo-notice"><Layers3 size={15} /><span>{result.notice}</span></div>}
      <div className="forecast-summary-row">
        <article className="forecast-summary"><span className="summary-icon mint-icon"><Gauge size={17} /></span><span><small>PEAK LOAD</small><strong>{peak?.predicted_demand_kw.toFixed(1) ?? '—'} <em>kW</em></strong><i>{peak ? `${formatHour(peak.timestamp)} local time` : 'No forecast available'}</i></span></article>
        <article className="forecast-summary"><span className="summary-icon amber-icon"><CalendarClock size={17} /></span><span><small>STORAGE WINDOW</small><strong>{String(settings.storageStartHour).padStart(2, '0')}:00–{String(settings.storageEndHour).padStart(2, '0')}:00</strong><i>Inclusive time rule</i></span></article>
        <article className="forecast-summary"><span className="summary-icon red-icon"><CircleAlert size={17} /></span><span><small>CRITICAL EVENTS</small><strong>{result.predictions.filter((point) => point.critical_alert).length} <em>hours</em></strong><i>Alert at ≥ {settings.criticalThresholdKw} kW</i></span></article>
      </div>
      <section className="panel chart-panel forecast-chart-panel">
        <div className="panel-heading chart-heading"><div><div className="section-kicker"><span className="kicker-dot" />24-HOUR SIGNAL</div><h2>Predicted demand by hour</h2><p>3D profile · threshold bands · keyboard-focusable hourly bars</p></div><span className="data-badge"><span />{result.model_source === 'quickml' ? 'QUICKML MODEL' : 'SCENARIO DATA'}</span></div>
        <IsometricChart points={result.predictions} />
        <div className="chart-legend"><span><i className="legend-swatch legend-mint" />Under {settings.storageThresholdKw} kW</span><span><i className="legend-swatch legend-amber" />Storage threshold</span><span><i className="legend-swatch legend-red" />Critical threshold</span></div>
      </section>
      <section className="panel forecast-table-panel">
        <div className="panel-heading lower-heading"><div><div className="section-kicker">HOURLY BREAKDOWN</div><h2>Dispatch decisions</h2></div><span className="table-total">{result.predictions.length} forecast points</span></div>
        <div className="table-scroll"><table className="data-table forecast-table"><thead><tr><th>TIME</th><th>PREDICTED DEMAND</th><th>AMBIENT</th><th>HUMIDITY</th><th>SOLAR</th><th>GRID MODE</th><th>ALERT</th></tr></thead><tbody>
          {result.predictions.map((point) => <tr key={point.timestamp}><td className="mono-cell">{formatHour(point.timestamp)}</td><td className={`mono-cell${point.critical_alert ? ' cell-critical' : ''}`}>{point.predicted_demand_kw.toFixed(1)} kW</td><td className="mono-cell">{point.ambient_temp_c.toFixed(1)}°</td><td className="mono-cell">{point.humidity_pct.toFixed(1)}%</td><td className="mono-cell">{point.solar_irradiance_wm2} W/m²</td><td><span className={`mode-pill${point.mode === 'renewable-storage' ? ' mode-storage' : ''}`}>{point.mode === 'renewable-storage' ? 'STORAGE' : 'MAIN GRID'}</span></td><td>{point.critical_alert ? <span className="alert-chip"><CircleAlert size={13} />CRITICAL</span> : <span className="clear-chip"><ArrowUpRight size={13} />CLEAR</span>}</td></tr>)}
        </tbody></table></div>
      </section>
      <div className="page-bottom-note"><span className="bottom-note-line" />Rules: storage above {settings.storageThresholdKw} kW or during {String(settings.storageStartHour).padStart(2, '0')}:00–{String(settings.storageEndHour).padStart(2, '0')}:00; alert at {settings.criticalThresholdKw} kW or higher.</div>
    </div>
  );
}
