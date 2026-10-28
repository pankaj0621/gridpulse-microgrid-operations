import type { DispatchDecision, DispatchSettings } from '../types';

export const DEFAULT_SETTINGS: DispatchSettings = {
  storageThresholdKw: 160,
  criticalThresholdKw: 200,
  storageStartHour: 18,
  storageEndHour: 22,
  startingSocPercent: 82,
};

function readHour(timestamp: string): number {
  const match = timestamp.match(/(?:T|\s)(\d{2}):\d{2}/);
  if (!match) throw new Error('Timestamp must include an hour and minute.');
  const hour = Number(match[1]);
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    throw new Error('Timestamp hour must be between 00 and 23.');
  }
  return hour;
}

function isWithinWindow(hour: number, start: number, end: number): boolean {
  return start <= end ? hour >= start && hour <= end : hour >= start || hour <= end;
}

export function evaluateDispatch(
  demandKw: number,
  timestamp: string,
  settings: DispatchSettings = DEFAULT_SETTINGS,
): DispatchDecision {
  if (!Number.isFinite(demandKw)) throw new Error('Demand must be a finite number.');
  for (const [name, hour] of [
    ['storageStartHour', settings.storageStartHour],
    ['storageEndHour', settings.storageEndHour],
  ] as const) {
    if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
      throw new Error(`${name} must be an hour between 0 and 23.`);
    }
  }
  const hour = readHour(timestamp);
  const demandTrigger = demandKw > settings.storageThresholdKw;
  const timeTrigger = isWithinWindow(hour, settings.storageStartHour, settings.storageEndHour);
  const criticalAlert = demandKw >= settings.criticalThresholdKw;
  const reasons: string[] = [];
  if (demandTrigger) reasons.push(`Demand exceeds ${settings.storageThresholdKw} kW.`);
  if (timeTrigger) reasons.push('Scheduled evening storage window is active.');
  if (criticalAlert) reasons.push(`Critical limit of ${settings.criticalThresholdKw} kW reached.`);
  return {
    mode: demandTrigger || timeTrigger ? 'renewable-storage' : 'main-grid',
    criticalAlert,
    reasons,
  };
}
