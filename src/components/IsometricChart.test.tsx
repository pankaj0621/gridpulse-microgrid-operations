import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS } from '../lib/dispatch';
import { createDemoForecast } from '../lib/demo';
import { IsometricChart } from './IsometricChart';

describe('IsometricChart tooltip', () => {
  it('keeps the full forecast value inside its rounded tooltip', () => {
    render(<IsometricChart points={createDemoForecast(DEFAULT_SETTINGS).predictions} />);
    const chart = screen.getByRole('img', { name: /isometric 24-hour forecast/i });
    const tooltip = chart.querySelector('.iso-peak-tooltip');
    const box = tooltip?.querySelector('rect');
    const text = tooltip?.querySelector('text');

    expect(box).not.toBeNull();
    expect(text).not.toBeNull();
    const boxWidth = Number(box?.getAttribute('width'));
    const visibleLabelWidth = 25 + (text?.textContent?.length ?? 0) * 7.8 + 10;
    const chartOffsetX = Number(tooltip?.getAttribute('transform')?.match(/translate\(([\d.]+)/)?.[1]);
    expect(boxWidth).toBeGreaterThanOrEqual(visibleLabelWidth);
    expect(chartOffsetX + boxWidth).toBeLessThanOrEqual(850);
  });

  it('keeps the Critical and Storage threshold labels inside their pills', () => {
    const { container } = render(<IsometricChart points={createDemoForecast(DEFAULT_SETTINGS).predictions} />);
    const chart = container.querySelector('svg[aria-label^="Isometric 24-hour forecast"]');
    const tags = [...(chart?.querySelectorAll('.iso-threshold-tag') ?? [])];

    expect(tags).toHaveLength(2);
    for (const tag of tags) {
      const box = tag.querySelector('rect');
      const text = tag.querySelector('text');
      expect(box).not.toBeNull();
      expect(text).not.toBeNull();

      const boxX = Number(box?.getAttribute('x'));
      const boxWidth = Number(box?.getAttribute('width'));
      const textX = Number(text?.getAttribute('x'));
      const estimatedTextWidth = (text?.textContent?.length ?? 0) * 7.8;
      expect(textX).toBeGreaterThanOrEqual(boxX + 8);
      expect(textX + estimatedTextWidth).toBeLessThanOrEqual(boxX + boxWidth - 8);
      expect(boxX + boxWidth).toBeLessThanOrEqual(850);
    }
  });
});
