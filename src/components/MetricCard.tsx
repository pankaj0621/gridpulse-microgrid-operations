import type { LucideIcon } from 'lucide-react';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  detail: string;
  icon: LucideIcon;
  tone?: 'mint' | 'cyan' | 'amber' | 'red';
  trend?: 'up' | 'down';
  featured?: boolean;
}

export function MetricCard({ label, value, unit, detail, icon: Icon, tone = 'mint', trend, featured }: MetricCardProps) {
  const Trend = trend === 'up' ? ArrowUpRight : ArrowDownRight;
  return (
    <article className={`metric-card tone-${tone}${featured ? ' metric-featured' : ''}`}>
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className="metric-icon"><Icon size={17} strokeWidth={1.8} aria-hidden="true" /></span>
      </div>
      <div className="metric-value">{value}{unit && <span>{unit}</span>}</div>
      <div className="metric-detail">
        {trend && <Trend size={15} aria-hidden="true" />}
        <span>{detail}</span>
      </div>
    </article>
  );
}
