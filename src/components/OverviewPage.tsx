import {
  Activity, ArrowRight, BatteryCharging, CircleAlert, Clock3, RadioTower,
  ShieldAlert, Signal, Sparkles, Zap,
} from 'lucide-react';
import { IsometricChart } from './IsometricChart';
import { MetricCard } from './MetricCard';
import { formatDate, formatHour, maxForecast } from '../lib/demo';
import type { DispatchSettings, ForecastResult } from '../types';

interface OverviewPageProps {
  result: ForecastResult;
  settings: DispatchSettings;
  onOpenForecasts: () => void;
  onOpenTelemetry: () => void;
}

function BatteryRing({ value }: { value: number }) {
  const circumference = 2 * Math.PI * 33;
  return (
    <svg className="battery-ring" viewBox="0 0 80 80" role="img" aria-label={`Illustrative battery state of charge ${value} percent`}>
      <circle cx="40" cy="40" r="33" className="ring-track" />
      <circle cx="40" cy="40" r="33" className="ring-progress" strokeDasharray={`${(value / 100) * circumference} ${circumference}`} />
      <text x="40" y="44" textAnchor="middle">{value}%</text>
    </svg>
  );
}

export function OverviewPage({ result, settings, onOpenForecasts, onOpenTelemetry }: OverviewPageProps) {
  const points = result.predictions;
  const peak = maxForecast(points);
  const criticalCount = points.filter((point) => point.critical_alert).length;
  const storageStart = points.find((point) => formatHour(point.timestamp) === `${String(settings.storageStartHour).padStart(2, '0')}:00`);
  const nextEvents = [
    { time: '17:00', title: 'Pre-peak check', detail: `Load approaching ${settings.storageThresholdKw} kW`, tone: 'cyan' },
    { time: `${String(settings.storageStartHour).padStart(2, '0')}:00`, title: 'Storage window begins', detail: storageStart ? `${storageStart.predicted_demand_kw.toFixed(1)} kW forecast` : 'Scheduled transition', tone: 'mint' },
    ...(peak?.critical_alert ? [{ time: formatHour(peak.timestamp), title: 'Critical overload', detail: `${peak.predicted_demand_kw.toFixed(1)} kW · alert only`, tone: 'red' }] : []),
  ];

  return (
    <div className="page-content page-overview">
      <div className="page-heading overview-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />NORTH RIDGE MICROGRID <span>/</span> 24-HOUR OUTLOOK</div>
          <h1>See the surge <span>before it hits.</span></h1>
          <p>Forecast demand early. Keep every storage transition visible.</p>
        </div>
        <div className="heading-date"><Clock3 size={15} /><span>{formatDate()}</span><i /> 24-hour view</div>
      </div>

      {result.notice && <div className="demo-notice"><Sparkles size={15} /><span>{result.notice}</span></div>}

      <section className="metric-grid" aria-label="Grid summary">
        <MetricCard featured label="Peak demand" value={peak?.predicted_demand_kw.toFixed(1) ?? '—'} unit="kW" detail={`${peak ? formatHour(peak.timestamp) : 'No forecast'} · ${peak?.critical_alert ? 'above critical limit' : 'within alert limit'}`} icon={Activity} tone="mint" trend="up" />
        <MetricCard label="Storage transition" value={`${String(settings.storageStartHour).padStart(2, '0')}:00`} detail="Scheduled evening window" icon={Zap} tone="cyan" />
        <MetricCard label="Critical alerts" value={String(criticalCount).padStart(2, '0')} detail="Independent 200 kW rule" icon={ShieldAlert} tone={criticalCount ? 'red' : 'amber'} />
        <MetricCard label="Grid state" value="Scenario" detail="Recommendations only · no device link" icon={RadioTower} tone="amber" />
      </section>

      <div className="overview-grid">
        <section className="panel chart-panel">
          <div className="panel-heading chart-heading">
            <div>
              <div className="section-kicker"><span className="kicker-dot" />FORECAST SIGNAL</div>
              <h2>24-hour demand forecast</h2>
              <p>Hourly model output <span>·</span> kilowatts</p>
            </div>
            <div className="panel-heading-actions"><span className="data-badge"><span /> {result.model_source === 'quickml' ? 'QUICKML MODEL' : 'SCENARIO DATA'}</span><button className="icon-button chart-action" aria-label="Open forecast workspace" onClick={onOpenForecasts} type="button"><ArrowRight size={17} /></button></div>
          </div>
          <IsometricChart points={points} />
          <div className="chart-legend">
            <span><i className="legend-swatch legend-mint" />Predicted demand</span>
            <span><i className="legend-swatch legend-amber" />Storage rule · {settings.storageThresholdKw} kW</span>
            <span><i className="legend-swatch legend-red" />Critical alert · {settings.criticalThresholdKw} kW</span>
          </div>
        </section>

        <section className="panel dispatch-panel">
          <div className="dispatch-topline"><span className="section-kicker"><span className="kicker-dot" />AUTOMATION PREVIEW</span><span className="sim-badge">SIMULATED</span></div>
          <div className="dispatch-title"><h2>Dispatch timeline</h2><p>Recommended transitions for today</p></div>
          <div className="dispatch-mode"><span className="dispatch-mode-icon"><BatteryCharging size={17} /></span><span><small>PLANNED GRID MODE</small><strong>Renewable storage</strong></span><span className="mode-orbit" /></div>
          <div className="timeline-list">
            {nextEvents.map((event, index) => (
              <div className={`timeline-event event-${event.tone}`} key={`${event.time}-${event.title}`}>
                <time>{event.time}</time><span className="timeline-connector"><i /></span>
                <div><strong>{event.title}</strong><p>{event.detail}</p></div>
                {index === 2 && event.tone === 'red' && <CircleAlert size={15} className="event-alert-icon" />}
              </div>
            ))}
          </div>
          <div className="dispatch-footer"><Signal size={15} /><span>Control path</span><strong>NO DEVICE CONNECTED</strong></div>
        </section>
      </div>

      <div className="lower-grid">
        <section className="panel transitions-panel">
          <div className="panel-heading lower-heading"><div><div className="section-kicker">UPCOMING HOURS</div><h2>Transition watch</h2></div><button className="text-button" onClick={onOpenForecasts} type="button">View forecast <ArrowRight size={15} /></button></div>
          <div className="table-scroll"><table className="data-table"><thead><tr><th>LOCAL TIME</th><th>FORECAST LOAD</th><th>GRID MODE</th><th>SYSTEM EVENT</th></tr></thead><tbody>
            {points.filter((point) => [18, 19, 20, 21, 22].includes(Number(formatHour(point.timestamp).slice(0, 2)))).slice(0, 4).map((point) => (
              <tr key={point.timestamp}><td className="mono-cell">{formatHour(point.timestamp)}</td><td className={`mono-cell${point.critical_alert ? ' cell-critical' : ''}`}>{point.predicted_demand_kw.toFixed(1)} kW</td><td><span className={`mode-pill${point.mode === 'renewable-storage' ? ' mode-storage' : ''}`}>{point.mode === 'renewable-storage' ? 'STORAGE' : 'MAIN GRID'}</span></td><td>{point.critical_alert ? <span className="critical-event-text">Critical alert threshold</span> : point.mode === 'renewable-storage' ? 'Storage rule active' : 'No transition required'}</td></tr>
            ))}
          </tbody></table></div>
        </section>
        <section className="panel battery-panel">
          <div className="panel-heading lower-heading"><div><div className="section-kicker">ENERGY STORAGE</div><h2>Battery outlook</h2></div><span className="estimate-badge">SCENARIO</span></div>
          <div className="battery-main"><BatteryRing value={result.simulated_soc_percent} /><div><div className="battery-drop">−11 <span>pts</span></div><p>Illustrative change from {settings.startingSocPercent}% start</p></div></div>
          <div className="battery-caption"><BatteryCharging size={14} /> No live state-of-charge sensor is connected.</div>
        </section>
      </div>

      <div className="page-bottom-note"><span className="bottom-note-line" />Forecast output is advisory. Physical dispatch is not connected. <button onClick={onOpenTelemetry} type="button">Review telemetry <ArrowRight size={13} /></button></div>
    </div>
  );
}
