import { useState } from 'react';
import { BatteryCharging, Check, CircleAlert, Clock3, LockKeyhole, Save, ShieldAlert, SlidersHorizontal, Zap } from 'lucide-react';
import type { DispatchSettings } from '../types';

interface ControlsPageProps {
  settings: DispatchSettings;
  onSettingsChange: (settings: DispatchSettings) => void;
  onSave: () => void;
}

export function ControlsPage({ settings, onSettingsChange, onSave }: ControlsPageProps) {
  const [saved, setSaved] = useState(false);

  function update<K extends keyof DispatchSettings>(key: K, value: DispatchSettings[K]) {
    setSaved(false);
    onSettingsChange({ ...settings, [key]: value });
  }

  function save() {
    onSave();
    setSaved(true);
  }

  return (
    <div className="page-content">
      <div className="page-heading page-heading-compact">
        <div><div className="eyebrow"><span className="eyebrow-line" />OPERATING POLICY <span>/</span> GRID CONTROLS</div><h1>Rules with <span>guardrails.</span></h1><p>Adjust the scenario thresholds used by the forecast decision preview.</p></div>
        <span className="simulation-lock"><LockKeyhole size={14} />SIMULATION ONLY</span>
      </div>

      <div className="control-page-grid">
        <section className="panel settings-panel">
          <div className="panel-heading lower-heading"><div><div className="section-kicker"><SlidersHorizontal size={13} />SCENARIO SETTINGS</div><h2>Transition rules</h2><p>Changes apply to new forecasts and stay in this browser.</p></div><span className="local-badge">LOCAL SETTINGS</span></div>
          <div className="setting-group">
            <div className="setting-description"><span className="setting-icon mint-icon"><Zap size={17} /></span><span><strong>Storage demand threshold</strong><small>Switch to renewable storage above this predicted load.</small></span></div>
            <label className="input-with-unit"><input type="number" min="80" max="300" step="1" value={settings.storageThresholdKw} onChange={(event) => update('storageThresholdKw', Number(event.target.value))} /><span>kW</span></label>
          </div>
          <div className="setting-group">
            <div className="setting-description"><span className="setting-icon red-icon"><ShieldAlert size={17} /></span><span><strong>Critical alert threshold</strong><small>Alert independently of the active grid mode.</small></span></div>
            <label className="input-with-unit"><input type="number" min="100" max="400" step="1" value={settings.criticalThresholdKw} onChange={(event) => update('criticalThresholdKw', Number(event.target.value))} /><span>kW</span></label>
          </div>
          <div className="setting-group setting-hours">
            <div className="setting-description"><span className="setting-icon amber-icon"><Clock3 size={17} /></span><span><strong>Scheduled storage window</strong><small>Inclusive start and end hours, local site time.</small></span></div>
            <div className="hour-inputs"><label><small>START</small><span><input type="number" min="0" max="23" value={settings.storageStartHour} onChange={(event) => update('storageStartHour', Number(event.target.value))} />:00</span></label><i>→</i><label><small>END</small><span><input type="number" min="0" max="23" value={settings.storageEndHour} onChange={(event) => update('storageEndHour', Number(event.target.value))} />:00</span></label></div>
          </div>
          <div className="setting-group">
            <div className="setting-description"><span className="setting-icon cyan-icon"><BatteryCharging size={17} /></span><span><strong>Starting battery estimate</strong><small>Scenario input only. No live SOC sensor is linked.</small></span></div>
            <label className="input-with-unit"><input type="number" min="0" max="100" step="1" value={settings.startingSocPercent} onChange={(event) => update('startingSocPercent', Number(event.target.value))} /><span>%</span></label>
          </div>
          <div className="settings-actions"><p><LockKeyhole size={14} />Physical controller actions are disabled.</p><button className="button button-primary" onClick={save} type="button">{saved ? <Check size={15} /> : <Save size={15} />}{saved ? 'Settings saved' : 'Save scenario'}</button></div>
        </section>

        <div className="control-side-column">
          <section className="panel rule-preview-panel">
            <div className="section-kicker">RULE ENGINE</div><h2>What triggers a transition?</h2>
            <div className="rule-preview"><span className="rule-number">01</span><span className="rule-icon storage-rule"><Zap size={17} /></span><span><strong>Renewable storage</strong><small>Demand &gt; {settings.storageThresholdKw} kW <b>OR</b> {String(settings.storageStartHour).padStart(2, '0')}:00–{String(settings.storageEndHour).padStart(2, '0')}:00 inclusive</small></span></div>
            <div className="rule-preview"><span className="rule-number">02</span><span className="rule-icon alert-rule"><CircleAlert size={17} /></span><span><strong>Critical overload alert</strong><small>Demand ≥ {settings.criticalThresholdKw} kW, independent of grid mode.</small></span></div>
            <div className="rule-preview"><span className="rule-number">03</span><span className="rule-icon main-grid-rule"><Check size={17} /></span><span><strong>Main grid</strong><small>Demand ≤ {settings.storageThresholdKw} kW outside the scheduled window.</small></span></div>
          </section>
          <section className="panel safety-panel"><span className="safety-symbol"><LockKeyhole size={19} /></span><div><div className="section-kicker">SAFETY BOUNDARY</div><h2>Advice only</h2><p>GridPulse shows recommended modes and alerts. It does not send switching commands to physical equipment.</p><div className="safety-state"><span />NO CONTROLLER LINKED</div></div></section>
        </div>
      </div>
      <div className="page-bottom-note"><span className="bottom-note-line" />Starter kit defaults: storage &gt; 160 kW or 18:00–22:00 inclusive; critical alert ≥ 200 kW.</div>
    </div>
  );
}
