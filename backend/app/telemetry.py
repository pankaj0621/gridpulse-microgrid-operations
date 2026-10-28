import csv
import io
import math
import statistics
from datetime import datetime
from typing import Any


FEATURES = ("ambient_temp_c", "humidity_pct", "solar_irradiance_wm2")
REQUIRED_COLUMNS = ("timestamp", *FEATURES)
MISSING_DEFAULTS = {"ambient_temp_c": 22.0, "humidity_pct": 50.0, "solar_irradiance_wm2": 0.0}
ALLOWED_RANGES = {
    "ambient_temp_c": (-80.0, 80.0),
    "humidity_pct": (0.0, 100.0),
    "solar_irradiance_wm2": (0.0, 2500.0),
    "target_demand_kw": (0.0, 2000.0),
}


def _parse_timestamp(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Every row must include a timestamp.")
    try:
        datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid timestamp: {cleaned}") from error
    return cleaned


def _parse_number(column: str, raw: str | None) -> float | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"Column {column} contains a non-numeric value.") from error
    if not math.isfinite(number):
        raise ValueError(f"Column {column} contains a non-finite value.")
    low, high = ALLOWED_RANGES[column]
    if not low <= number <= high:
        raise ValueError(f"Column {column} must be between {low:g} and {high:g}.")
    return number


def parse_telemetry_csv(content: str) -> tuple[list[dict[str, Any]], int]:
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    headers = [header.strip() for header in (reader.fieldnames or [])]
    missing_headers = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing_headers:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_headers)}.")

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in reader:
        if not any((value or "").strip() for value in raw.values()):
            continue
        timestamp = _parse_timestamp(raw.get("timestamp", ""))
        if timestamp in seen:
            raise ValueError(f"Duplicate timestamp: {timestamp}")
        seen.add(timestamp)
        record: dict[str, Any] = {"timestamp": timestamp}
        for column in FEATURES:
            record[column] = _parse_number(column, raw.get(column))
        target = raw.get("target_demand_kw")
        record["target_demand_kw"] = _parse_number("target_demand_kw", target)
        records.append(record)
    if not records:
        raise ValueError("CSV contains no telemetry rows.")

    filled = 0
    for column in FEATURES:
        values = [record[column] for record in records if record[column] is not None]
        fill_value = float(statistics.median(values)) if values else MISSING_DEFAULTS[column]
        for record in records:
            if record[column] is None:
                record[column] = fill_value
                filled += 1
    return records, filled


def clean_forecast_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    if len(rows) != 24:
        raise ValueError("A complete forecast requires exactly 24 hourly weather rows.")
    headers = ["timestamp", *FEATURES]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in headers})
    return parse_telemetry_csv(stream.getvalue())
