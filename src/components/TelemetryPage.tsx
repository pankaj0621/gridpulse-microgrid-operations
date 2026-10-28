import { useRef, useState, type FormEvent } from 'react';
import { Activity, ArrowDownToLine, ArrowUpFromLine, Check, CircleAlert, CloudUpload, Database, FileSpreadsheet, Radio, Thermometer, Wind } from 'lucide-react';
import type { TelemetrySummary } from '../types';

interface TelemetryPageProps {
  summary: TelemetrySummary;
  stagedRows: number;
  uploadMessage: string;
  uploadError: boolean;
  onUpload: (file: File) => void;
}

const requiredColumns = ['timestamp', 'ambient_temp_c', 'humidity_pct', 'solar_irradiance_wm2'];

export function TelemetryPage({ summary, stagedRows, uploadMessage, uploadError, onUpload }: TelemetryPageProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [temperature, setTemperature] = useState('27.5');
  const [humidity, setHumidity] = useState('58');
  const [solar, setSolar] = useState('420');

  function acceptFile(file?: File) {
    if (file) onUpload(file);
  }

  function submitManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const timestamp = new Date();
    const offset = timestamp.getTimezoneOffset() * 60_000;
    const local = new Date(timestamp.getTime() - offset).toISOString().slice(0, 19).replace('T', ' ');
    const csv = [requiredColumns.join(','), `${local},${temperature},${humidity},${solar}`].join('\n');
    acceptFile(new File([csv], 'manual-telemetry.csv', { type: 'text/csv' }));
  }

  function downloadSchema() {
    const content = `${requiredColumns.join(',')}\n2026-10-24 18:00:00,27.5,58,420\n`;
    const url = URL.createObjectURL(new Blob([content], { type: 'text/csv' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'gridpulse-telemetry-template.csv';
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page-content">
      <div className="page-heading page-heading-compact">
        <div><div className="eyebrow"><span className="eyebrow-line" />INPUT PIPELINE <span>/</span> TELEMETRY</div><h1>Signals in. <span>Clarity out.</span></h1><p>Upload hourly weather telemetry or add a single reading to prepare a forecast.</p></div>
        <button className="button button-secondary" onClick={downloadSchema} type="button"><ArrowDownToLine size={16} />Download CSV template</button>
      </div>

      <section className="telemetry-status-grid">
        <article className="telemetry-status-card"><span className="status-card-icon icon-cyan"><Radio size={18} /></span><span><small>LIVE SENSOR LINK</small><strong>Not connected</strong><i>CSV and manual entry available</i></span><span className="status-indicator status-idle" /></article>
        <article className="telemetry-status-card"><span className="status-card-icon icon-mint"><Database size={18} /></span><span><small>UPLOADED RECORDS</small><strong>{summary.uploaded_rows.toLocaleString('en-US')} <em>rows</em></strong><i>{summary.latest_upload ? `Last upload ${summary.latest_upload}` : 'No local upload yet'}</i></span><span className="status-indicator status-led-green" /></article>
        <article className="telemetry-status-card"><span className="status-card-icon icon-violet"><FileSpreadsheet size={18} /></span><span><small>STARTER DATASET</small><strong>{summary.training_rows.toLocaleString('en-US')} / {summary.test_rows.toLocaleString('en-US')}</strong><i>Training rows / test rows</i></span><span className="status-indicator status-led-green" /></article>
      </section>

      <div className="telemetry-layout">
        <section className="panel upload-panel">
          <div className="panel-heading lower-heading"><div><div className="section-kicker"><span className="kicker-dot" />CSV INGESTION</div><h2>Upload telemetry</h2><p>Expected fields: timestamp, ambient temperature, humidity, solar irradiance.</p></div><span className="upload-limit">CSV · UP TO 10 MB</span></div>
          {stagedRows > 0 && <div className="staged-pill"><Check size={14} />{stagedRows} of 24 forecast hours staged from the selected file.</div>}
          <div className={`dropzone${dragging ? ' drag-active' : ''}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files[0]); }}>
            <span className="dropzone-icon"><CloudUpload size={24} /></span><strong>Drop your telemetry file here</strong><span>or choose a CSV from this device</span>
            <button className="button button-secondary" type="button" onClick={() => inputRef.current?.click()}><ArrowUpFromLine size={15} />Choose CSV file</button>
            <input ref={inputRef} type="file" accept=".csv,text/csv" hidden onChange={(event) => { acceptFile(event.target.files?.[0]); event.currentTarget.value = ''; }} />
            <small>Required columns: {requiredColumns.join(' · ')}</small>
          </div>
          {uploadMessage && <div className={`upload-feedback${uploadError ? ' feedback-error' : ''}`} role="status">{uploadError ? <CircleAlert size={16} /> : <Check size={16} />}{uploadMessage}</div>}
          <div className="schema-grid"><div><Thermometer size={16} /><span><strong>ambient_temp_c</strong><small>Ambient temperature · °C</small></span></div><div><Activity size={16} /><span><strong>humidity_pct</strong><small>Relative humidity · %</small></span></div><div><Wind size={16} /><span><strong>solar_irradiance_wm2</strong><small>Solar irradiance · W/m²</small></span></div></div>
        </section>

        <section className="panel manual-panel">
          <div className="manual-header"><span className="manual-icon"><Activity size={17} /></span><div><div className="section-kicker">QUICK INPUT</div><h2>Manual weather reading</h2></div></div>
          <form onSubmit={submitManual} className="manual-form">
            <label>Ambient temperature <span>°C</span><input type="number" step="0.1" min="-30" max="60" value={temperature} onChange={(event) => setTemperature(event.target.value)} required /></label>
            <label>Relative humidity <span>%</span><input type="number" step="0.1" min="0" max="100" value={humidity} onChange={(event) => setHumidity(event.target.value)} required /></label>
            <label>Solar irradiance <span>W/m²</span><input type="number" step="1" min="0" max="1400" value={solar} onChange={(event) => setSolar(event.target.value)} required /></label>
            <button className="button button-primary manual-submit" type="submit"><Activity size={15} />Add reading</button>
          </form>
          <p className="manual-note">A timestamp is added automatically. The reading is staged for forecasting; it does not trigger a device action.</p>
        </section>
      </div>

      <section className="panel dataset-panel">
        <div className="panel-heading lower-heading"><div><div className="section-kicker">MODEL INPUT REFERENCE</div><h2>Starter kit files</h2></div><span className="dataset-badge"><Database size={13} />VALIDATED SCHEMA</span></div>
        <div className="dataset-files">
          <article><span className="file-icon"><FileSpreadsheet size={19} /></span><span><strong>train_telemetry.csv</strong><small>4,000 historical rows · target_demand_kw included</small></span><span className="file-tag">TRAINING</span></article>
          <article><span className="file-icon"><FileSpreadsheet size={19} /></span><span><strong>sample_test_input.csv</strong><small>1,000 weather rows · target omitted</small></span><span className="file-tag file-tag-test">VALIDATION</span></article>
        </div>
        <p className="dataset-footnote">Missing weather values are imputed during ingestion. Invalid timestamps and duplicate hours are rejected.</p>
      </section>
    </div>
  );
}
