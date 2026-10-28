import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import App from './App';

describe('GridPulse workspace navigation', () => {
  afterEach(() => localStorage.clear());

  it('opens an English-language overview with the 24-hour chart', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /see the surge before it hits/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /isometric 24-hour forecast/i })).toBeInTheDocument();
    expect(screen.getByText(/simulation mode/i)).toBeInTheDocument();
  });

  it('switches between forecast, telemetry, and grid controls sections', () => {
    render(<App />);
    const navigation = within(screen.getAllByRole('navigation', { name: 'Main navigation' })[0]);
    fireEvent.click(navigation.getByRole('button', { name: /Forecasts/ }));
    expect(screen.getByRole('heading', { name: /forecast workspace/i })).toBeInTheDocument();

    fireEvent.click(navigation.getByRole('button', { name: 'Telemetry' }));
    expect(screen.getByRole('heading', { name: /signals in/i })).toBeInTheDocument();

    fireEvent.click(navigation.getByRole('button', { name: 'Grid controls' }));
    expect(screen.getByRole('heading', { name: /rules with guardrails/i })).toBeInTheDocument();
  });
});
