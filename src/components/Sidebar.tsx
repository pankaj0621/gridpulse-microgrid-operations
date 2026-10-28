import {
  Activity, BatteryCharging, Boxes, ChartNoAxesCombined, ChevronDown, CircleHelp,
  Command, Gauge, LayoutDashboard, Settings2, ShieldCheck, Zap,
} from 'lucide-react';
import type { PageId } from '../types';

const navigation: { id: PageId; label: string; icon: typeof LayoutDashboard; group: string }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, group: 'Command center' },
  { id: 'forecasts', label: 'Forecasts', icon: ChartNoAxesCombined, group: 'Command center' },
  { id: 'telemetry', label: 'Telemetry', icon: Activity, group: 'Data & models' },
  { id: 'controls', label: 'Grid controls', icon: Settings2, group: 'Data & models' },
];

interface SidebarProps {
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  open: boolean;
  modelLabel: string;
}

export function Sidebar({ activePage, onNavigate, open, modelLabel }: SidebarProps) {
  return (
    <aside className={`sidebar${open ? ' sidebar-open' : ''}`}>
      <div className="sidebar-brand">
        <span className="brand-mark"><Zap size={20} fill="currentColor" strokeWidth={2.4} /></span>
        <span><strong>GRIDPULSE</strong><small>ENERGY SYSTEMS</small></span>
        <button className="icon-button sidebar-mobile-close" aria-label="Close navigation" onClick={() => onNavigate(activePage)}>×</button>
      </div>

      <button className="site-switcher" type="button" aria-label="Current microgrid site">
        <span className="site-orbit"><Boxes size={16} /></span>
        <span className="site-copy"><small>ACTIVE MICROGRID</small><strong>North Ridge <ChevronDown size={13} /></strong><em>California · UTC−07:00</em></span>
        <span className="site-pulse" />
      </button>

      <nav aria-label="Main navigation" className="primary-nav">
        {(['Command center', 'Data & models'] as const).map((group) => (
          <div className="nav-group" key={group}>
            <div className="nav-caption">{group}<span /></div>
            {navigation.filter((item) => item.group === group).map(({ id, label, icon: Icon }) => (
              <button
                aria-current={activePage === id ? 'page' : undefined}
                className={`nav-item${activePage === id ? ' active' : ''}`}
                key={id}
                onClick={() => onNavigate(id)}
                type="button"
              >
                <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                <span>{label}</span>
                {id === 'forecasts' && <span className="nav-badge">24h</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-spacer" />
      <div className="sidebar-model">
        <span className="model-icon"><Gauge size={16} /></span>
        <span><small>FORECAST ENGINE</small><strong>{modelLabel}</strong></span>
        <span className={`model-led${modelLabel === 'QuickML' ? ' led-live' : ''}`} />
      </div>
      <button className="help-link" type="button"><CircleHelp size={16} /> System guide <Command size={13} className="help-command" /></button>
      <div className="operator-card">
        <span className="operator-avatar">NR</span>
        <span><strong>North Ridge Ops</strong><small>Operator workspace</small></span>
        <ShieldCheck size={16} className="operator-shield" />
      </div>
      <div className="sidebar-decoration" aria-hidden="true"><BatteryCharging size={15} /> Clean energy · clear decisions</div>
    </aside>
  );
}
