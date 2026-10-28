import { useState } from 'react';
import type { ForecastPoint } from '../types';
import { formatHour } from '../lib/demo';

interface IsometricChartProps {
  points: ForecastPoint[];
  compact?: boolean;
}

const W = 850;
const BASE = 278;
const TOP = 54;
const X0 = 70;
const STEP = 27;
const BAR_WIDTH = 15;
const DEPTH_X = 8;
const DEPTH_Y = 6;
const TOOLTIP_WIDTH = 168;
const THRESHOLD_TAG_WIDTH = 132;
const THRESHOLD_TAG_X = W - THRESHOLD_TAG_WIDTH - 13;

function yFor(demand: number): number {
  const bounded = Math.min(240, Math.max(80, demand));
  return BASE - ((bounded - 80) / 160) * (BASE - TOP);
}

function barColor(demand: number): { front: string; side: string; top: string } {
  if (demand >= 200) return { front: 'url(#bar-critical)', side: '#a63c4d', top: '#ff8b9d' };
  if (demand > 160) return { front: 'url(#bar-storage)', side: '#a36b23', top: '#ffd16a' };
  return { front: 'url(#bar-normal)', side: '#16765d', top: '#68e0b6' };
}

export function IsometricChart({ points, compact = false }: IsometricChartProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const chartPoints = points.map((point, index) => ({
    point,
    index,
    x: X0 + index * STEP,
    y: yFor(point.predicted_demand_kw),
  }));
  const peak = points.reduce<number>((best, point, index) =>
    point.predicted_demand_kw > points[best].predicted_demand_kw ? index : best, 0);
  const focused = hovered === null ? peak : hovered;
  const focusedPoint = chartPoints[focused];
  const tooltipX = Math.max(45, Math.min(W - TOOLTIP_WIDTH - 13, focusedPoint.x + BAR_WIDTH / 2 - TOOLTIP_WIDTH / 2));
  const tooltipY = Math.max(12, focusedPoint.y - 50);
  const linePoints = chartPoints.map(({ x, y }) => `${x + BAR_WIDTH / 2},${y - 1}`).join(' ');

  return (
    <div className={`iso-chart${compact ? ' iso-chart-compact' : ''}`}>
      <svg viewBox={`0 0 ${W} 330`} role="img" aria-label="Isometric 24-hour forecast with a 160 kilowatt storage threshold and a 200 kilowatt critical alert threshold.">
        <defs>
          <linearGradient id="bar-normal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#5ae0b4"/><stop offset="1" stopColor="#178164"/></linearGradient>
          <linearGradient id="bar-storage" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffdc83"/><stop offset="1" stopColor="#c58a32"/></linearGradient>
          <linearGradient id="bar-critical" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ff9aa8"/><stop offset="1" stopColor="#c54d5f"/></linearGradient>
          <filter id="column-shadow" x="-25%" y="-20%" width="155%" height="170%"><feDropShadow dx="0" dy="5" stdDeviation="4" floodColor="#020d0a" floodOpacity=".24"/></filter>
        </defs>
        <path className="iso-floor" d={`M48 ${BASE} L722 ${BASE} L741 ${BASE - 14} L67 ${BASE - 14} Z`} />
        {[240, 200, 160, 120, 80].map((value) => {
          const y = yFor(value);
          const special = value === 200 ? 'critical' : value === 160 ? 'storage' : '';
          return (
            <g key={value}>
              <line className={`iso-grid ${special ? `iso-grid-${special}` : ''}`} x1="48" y1={y} x2="722" y2={y} />
              <text className="iso-axis-label" x="7" y={y + 5}>{value}</text>
            </g>
          );
        })}
        <line className="iso-depth-edge" x1="48" y1={BASE} x2="67" y2={BASE - 14} />
        <line className="iso-depth-edge" x1="722" y1={BASE} x2="741" y2={BASE - 14} />
        <g filter="url(#column-shadow)">
          {chartPoints.map(({ point, index, x, y }) => {
            const color = barColor(point.predicted_demand_kw);
            const isHovered = index === hovered;
            return (
              <g
                key={point.timestamp}
                className={`iso-column${isHovered ? ' is-hovered' : ''}`}
                tabIndex={0}
                role="img"
                aria-label={`${formatHour(point.timestamp)}, ${point.predicted_demand_kw.toFixed(1)} kilowatts`}
                onMouseEnter={() => setHovered(index)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(index)}
                onBlur={() => setHovered(null)}
              >
                <title>{`${formatHour(point.timestamp)} — ${point.predicted_demand_kw.toFixed(1)} kW${point.critical_alert ? ', critical alert' : ''}`}</title>
                <path className="iso-face-top" d={`M${x} ${y} L${x + DEPTH_X} ${y - DEPTH_Y} L${x + BAR_WIDTH + DEPTH_X} ${y - DEPTH_Y} L${x + BAR_WIDTH} ${y} Z`} fill={color.top} />
                <path className="iso-face-side" d={`M${x + BAR_WIDTH} ${y} L${x + BAR_WIDTH + DEPTH_X} ${y - DEPTH_Y} L${x + BAR_WIDTH + DEPTH_X} ${BASE - DEPTH_Y} L${x + BAR_WIDTH} ${BASE} Z`} fill={color.side} />
                <path className="iso-face-front" d={`M${x} ${y} L${x + BAR_WIDTH} ${y} L${x + BAR_WIDTH} ${BASE} L${x} ${BASE} Z`} fill={color.front} />
              </g>
            );
          })}
        </g>
        {chartPoints.length > 1 && <polyline className="iso-load-line" points={linePoints} />}
        <g className="iso-threshold-tag iso-tag-critical"><rect x={THRESHOLD_TAG_X} y={yFor(200) - 14} width={THRESHOLD_TAG_WIDTH} height="22" rx="7"/><text x={THRESHOLD_TAG_X + 8} y={yFor(200) + 1}>200 · CRITICAL</text></g>
        <g className="iso-threshold-tag iso-tag-storage"><rect x={THRESHOLD_TAG_X} y={yFor(160) - 14} width={THRESHOLD_TAG_WIDTH} height="22" rx="7"/><text x={THRESHOLD_TAG_X + 8} y={yFor(160) + 1}>160 · STORAGE</text></g>
        {[0, 6, 12, 18, 23].map((hour) => (
          <text className="iso-hour-label" key={hour} x={X0 + hour * STEP + BAR_WIDTH / 2} y="310" textAnchor="middle">{formatHour(points[hour]?.timestamp ?? '')}</text>
        ))}
        <g className="iso-peak-tooltip" transform={`translate(${tooltipX} ${tooltipY})`} aria-hidden="true">
          <rect width={TOOLTIP_WIDTH} height="33" rx="10" />
          <circle cx="14" cy="16.5" r="4" />
          <text x="25" y="21">{formatHour(focusedPoint.point.timestamp)} · {focusedPoint.point.predicted_demand_kw.toFixed(1)} kW</text>
        </g>
        <text className="iso-unit-label" x="7" y="24">kW</text>
      </svg>
    </div>
  );
}
