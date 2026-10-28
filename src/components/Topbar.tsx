import { Bell, Menu, Search, Sparkles } from 'lucide-react';
import type { PageId } from '../types';

const pageTitle: Record<PageId, string> = {
  overview: 'Overview', forecasts: 'Forecasts', telemetry: 'Telemetry', controls: 'Grid controls',
};

interface TopbarProps {
  activePage: PageId;
  onMenu: () => void;
  onBuildForecast: () => void;
  busy: boolean;
  modelLabel: string;
}

export function Topbar({ activePage, onMenu, onBuildForecast, busy, modelLabel }: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="icon-button menu-trigger" onClick={onMenu} aria-label="Open navigation"><Menu size={19} /></button>
        <div className="breadcrumbs"><span>GRIDPULSE</span><i>/</i><strong>{pageTitle[activePage]}</strong></div>
      </div>
      <div className="topbar-right">
        <span className="system-pill"><span className={`status-led${modelLabel === 'QuickML' ? ' led-active' : ''}`} />{modelLabel === 'QuickML' ? 'MODEL CONNECTED' : 'SIMULATION MODE'}</span>
        <button className="icon-button topbar-icon" aria-label="Search telemetry" type="button"><Search size={18} /></button>
        <button className="icon-button topbar-icon notification-button" aria-label="No unread alerts" type="button"><Bell size={18} /><i /></button>
        <button className="button button-primary topbar-build" onClick={onBuildForecast} disabled={busy} type="button">
          <Sparkles size={16} />{busy ? 'Building…' : 'Run forecast'}
        </button>
      </div>
    </header>
  );
}
