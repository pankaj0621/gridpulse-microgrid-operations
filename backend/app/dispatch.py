import math
import re
from typing import Any


DEFAULT_SETTINGS = {
    "storage_threshold_kw": 160.0,
    "critical_threshold_kw": 200.0,
    "storage_start_hour": 18,
    "storage_end_hour": 22,
}


def _read_hour(timestamp: str) -> int:
    if not isinstance(timestamp, str):
        raise ValueError("Timestamp must be text.")
    match = re.search(r"(?:T|\s)(\d{2}):\d{2}", timestamp)
    if not match:
        raise ValueError("Timestamp must include an hour and minute.")
    hour = int(match.group(1))
    if not 0 <= hour <= 23:
        raise ValueError("Timestamp hour must be between 00 and 23.")
    return hour


def evaluate_dispatch(
    demand_kw: float,
    timestamp: str,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    configuration = {**DEFAULT_SETTINGS, **(settings or {})}
    try:
        demand = float(demand_kw)
        storage_threshold = float(configuration["storage_threshold_kw"])
        critical_threshold = float(configuration["critical_threshold_kw"])
        start_hour = int(configuration["storage_start_hour"])
        end_hour = int(configuration["storage_end_hour"])
    except (TypeError, ValueError, KeyError) as error:
        raise ValueError("Dispatch settings and demand must be numeric.") from error
    if not all(math.isfinite(value) for value in (demand, storage_threshold, critical_threshold)):
        raise ValueError("Demand thresholds must be finite numbers.")
    if not 0 <= start_hour <= 23 or not 0 <= end_hour <= 23:
        raise ValueError("Storage window hours must be between 0 and 23.")

    hour = _read_hour(timestamp)
    time_trigger = hour >= start_hour and hour <= end_hour if start_hour <= end_hour else hour >= start_hour or hour <= end_hour
    demand_trigger = demand > storage_threshold
    critical_alert = demand >= critical_threshold
    reasons = []
    if demand_trigger:
        reasons.append(f"Demand exceeds {storage_threshold:g} kW.")
    if time_trigger:
        reasons.append("Scheduled evening storage window is active.")
    if critical_alert:
        reasons.append(f"Critical limit of {critical_threshold:g} kW reached.")
    return {
        "mode": "renewable-storage" if demand_trigger or time_trigger else "main-grid",
        "critical_alert": critical_alert,
        "reasons": reasons,
    }
