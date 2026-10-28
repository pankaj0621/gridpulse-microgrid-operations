import { describe, expect, it } from 'vitest';
import { evaluateDispatch } from './dispatch';

describe('evaluateDispatch', () => {
  it('keeps demand at 160 kW on the main grid outside the storage window', () => {
    expect(evaluateDispatch(160, '2026-10-24 17:00:00')).toMatchObject({
      mode: 'main-grid',
      criticalAlert: false,
    });
  });

  it('switches to storage when demand is above 160 kW', () => {
    expect(evaluateDispatch(160.01, '2026-10-24 17:00:00')).toMatchObject({
      mode: 'renewable-storage',
      criticalAlert: false,
    });
  });

  it('switches to storage throughout the inclusive 18:00–22:00 window', () => {
    for (const hour of [18, 19, 20, 21, 22]) {
      expect(evaluateDispatch(120, `2026-10-24 ${String(hour).padStart(2, '0')}:00:00`).mode)
        .toBe('renewable-storage');
    }
  });

  it('returns to the main grid at 23:00 when demand is at or below 160 kW', () => {
    expect(evaluateDispatch(160, '2026-10-24 23:00:00').mode).toBe('main-grid');
  });

  it('raises the critical alert at 200 kW independently of grid mode', () => {
    expect(evaluateDispatch(200, '2026-10-24 08:00:00')).toMatchObject({
      mode: 'renewable-storage',
      criticalAlert: true,
    });
  });

  it('rejects non-finite demand and unparseable timestamps', () => {
    expect(() => evaluateDispatch(Number.NaN, '2026-10-24 08:00:00')).toThrow();
    expect(() => evaluateDispatch(120, 'not-a-date')).toThrow();
  });
});
