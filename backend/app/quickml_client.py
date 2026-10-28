"""Authenticated batch adapter for published Catalyst QuickML endpoints."""

from __future__ import annotations

import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


class QuickMLConfigurationError(ValueError):
    """Raised when an endpoint is set but its OAuth configuration is incomplete."""


@dataclass(frozen=True)
class QuickMLConfig:
    endpoint_url: str
    endpoint_key: str
    org_id: str
    environment: str
    token_url: str
    refresh_token: str
    client_id: str
    client_secret: str

    @classmethod
    def from_environment(cls) -> "QuickMLConfig":
        return cls(
            endpoint_url=os.getenv("QUICKML_ENDPOINT_URL", "").strip(),
            endpoint_key=os.getenv("QUICKML_ENDPOINT_KEY", "").strip(),
            org_id=os.getenv("QUICKML_ORG_ID", "").strip(),
            environment=os.getenv("QUICKML_ENVIRONMENT", "Development").strip(),
            token_url=os.getenv("ZOHO_OAUTH_TOKEN_URL", "https://accounts.zoho.in/oauth/v2/token").strip(),
            refresh_token=os.getenv("QUICKML_REFRESH_TOKEN", "").strip(),
            client_id=os.getenv("QUICKML_CLIENT_ID", "").strip(),
            client_secret=os.getenv("QUICKML_CLIENT_SECRET", "").strip(),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint_url)

    @property
    def missing_fields(self) -> list[str]:
        required = {
            "QUICKML_ENDPOINT_KEY": self.endpoint_key,
            "QUICKML_ORG_ID": self.org_id,
            "QUICKML_REFRESH_TOKEN": self.refresh_token,
            "QUICKML_CLIENT_ID": self.client_id,
            "QUICKML_CLIENT_SECRET": self.client_secret,
            "ZOHO_OAUTH_TOKEN_URL": self.token_url,
        }
        missing = [name for name, value in required.items() if not value]
        if self.environment not in {"Development", "Production"}:
            missing.append("QUICKML_ENVIRONMENT (Development or Production)")
        return missing

    @property
    def configured(self) -> bool:
        return self.enabled and not self.missing_fields


_TOKEN_CACHE: dict[tuple[str, str, str], tuple[str, float]] = {}
_TOKEN_CACHE_LOCK = threading.Lock()


def clear_token_cache() -> None:
    """Clear cached OAuth access tokens; exposed for deterministic tests."""
    with _TOKEN_CACHE_LOCK:
        _TOKEN_CACHE.clear()


def prepare_model_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map GridPulse weather rows to the feature schema used to train QuickML."""
    prepared: list[dict[str, Any]] = []
    for row in rows:
        raw_timestamp = row.get("timestamp")
        if not isinstance(raw_timestamp, str):
            raise ValueError("QuickML received an invalid timestamp.")
        try:
            timestamp = datetime.fromisoformat(raw_timestamp.strip().replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("QuickML received an invalid timestamp.") from error

        weekday = timestamp.weekday()
        prepared.append({
            "ambient_temp_c": row.get("ambient_temp_c"),
            "humidity_pct": row.get("humidity_pct"),
            "solar_irradiance_wm2": row.get("solar_irradiance_wm2"),
            "hour": timestamp.hour,
            "day_of_week": weekday + 1,
            "month": timestamp.month,
            "is_weekend": int(weekday >= 5),
        })
    return prepared


class QuickMLClient:
    def __init__(self, config: QuickMLConfig, session: Any = requests):
        self.config = config
        self.session = session

    @classmethod
    def from_environment(cls, session: Any = requests) -> "QuickMLClient":
        return cls(QuickMLConfig.from_environment(), session=session)

    def predict(self, rows: list[dict[str, Any]]) -> list[float]:
        if not self.config.endpoint_url:
            raise QuickMLConfigurationError("QUICKML_ENDPOINT_URL is not configured.")
        if self.config.missing_fields:
            fields = ", ".join(self.config.missing_fields)
            raise QuickMLConfigurationError(f"QuickML configuration is incomplete: {fields}.")
        if not rows:
            return []
        model_rows = prepare_model_features(rows)

        response = self.session.post(
            self.config.endpoint_url,
            json={"data": model_rows},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Zoho-oauthtoken {self._access_token()}",
                "X-QUICKML-ENDPOINT-KEY": self.config.endpoint_key,
                "CATALYST-ORG": self.config.org_id,
                "Environment": self.config.environment,
            },
            timeout=(5, 20),
        )
        response.raise_for_status()
        payload = response.json()
        predictions = payload.get("predictions") if isinstance(payload, dict) else None
        if not isinstance(predictions, list) or len(predictions) != len(rows):
            raise ValueError("QuickML returned a prediction count that does not match the input.")

        values: list[float] = []
        for prediction in predictions:
            if isinstance(prediction, bool):
                raise ValueError("QuickML returned a non-numeric prediction.")
            try:
                value = float(prediction)
            except (TypeError, ValueError) as error:
                raise ValueError("QuickML returned a non-numeric prediction.") from error
            if not math.isfinite(value):
                raise ValueError("QuickML returned a non-finite prediction.")
            values.append(value)
        return values

    def _access_token(self) -> str:
        cache_key = (self.config.token_url, self.config.client_id, self.config.refresh_token)
        now = time.time()
        with _TOKEN_CACHE_LOCK:
            cached = _TOKEN_CACHE.get(cache_key)
            if cached and cached[1] > now:
                return cached[0]

        response = self.session.post(
            self.config.token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self.config.refresh_token,
            },
            timeout=(5, 20),
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise ValueError("Zoho OAuth did not return an access token.")
        try:
            lifetime = max(1, int(payload.get("expires_in", 3600)) - 60)
        except (TypeError, ValueError):
            lifetime = 3540
        with _TOKEN_CACHE_LOCK:
            _TOKEN_CACHE[cache_key] = (token, time.time() + lifetime)
        return token
