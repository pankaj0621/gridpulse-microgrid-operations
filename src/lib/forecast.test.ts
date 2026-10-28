import { describe, expect, it } from 'vitest';
import { createDemoForecast, formatHour, maxForecast } from './demo';

describe('demo forecast helpers', () => {
  it('creates exactly one point for each of the next 24 hours', () => {
    const result = createDemoForecast(undefined, new Date(2026, 9, 24, 11, 30));
    expect(result.predictions).toHaveLength(24);
    expect(result.predictions[0].timestamp).toContain('00:00');
    expect(result.predictions[23].timestamp).toContain('23:00');
  });

  it('keeps peak demand and the dispatch window aligned with the scenario', () => {
    const result = createDemoForecast(undefined, new Date(2026, 9, 24));
    const peak = maxForecast(result.predictions);
    expect(peak?.predicted_demand_kw).toBe(211);
    expect(formatHour(peak!.timestamp)).toBe('20:00');
    expect(result.predictions.find((point) => formatHour(point.timestamp) === '18:00'))
      .toMatchObject({ predicted_demand_kw: 176.4, mode: 'renewable-storage' });
  });
});
