"""
PlantaOS · Weather service
===========================
Tempo actual em Lisboa via open-meteo.com (gratuito, sem auth).
Cache em memória 10 minutos. Sem dependências externas.

API: https://api.open-meteo.com/v1/forecast?latitude=38.78&longitude=-9.09&current_weather=true
"""
from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta

import httpx

from app.models.operations import WeatherNow
from app.clusters_geo import ANCHOR_GPS as _ANCHOR_GPS

# Âncora GPS do recinto (clusters_geo — única fonte)
LAT = _ANCHOR_GPS["lat"]
LON = _ANCHOR_GPS["lon"]
LOCATION = "Lisboa · Parque Tejo"

CACHE_TTL_S = 600  # 10 minutos
_cache: dict[str, object] = {"payload": None, "fetched_at": 0.0}

# WMO weather codes → label PT-PT (selecção dos mais comuns)
WMO_CODES = {
    0: "céu limpo",
    1: "muito limpo",
    2: "parcialmente nublado",
    3: "encoberto",
    45: "nevoeiro",
    48: "nevoeiro gelado",
    51: "chuvisco fraco",
    53: "chuvisco moderado",
    55: "chuvisco forte",
    61: "chuva fraca",
    63: "chuva moderada",
    65: "chuva forte",
    71: "neve fraca",
    73: "neve moderada",
    75: "neve forte",
    77: "grãos de neve",
    80: "aguaceiros fracos",
    81: "aguaceiros moderados",
    82: "aguaceiros violentos",
    85: "aguaceiros de neve fracos",
    86: "aguaceiros de neve fortes",
    95: "trovoada",
    96: "trovoada com granizo leve",
    99: "trovoada com granizo forte",
}


def _label(code: int) -> str:
    return WMO_CODES.get(code, f"código {code}")


async def get_now() -> WeatherNow:
    """Devolve tempo actual com cache 10 min."""
    now_ts = time.time()
    cached = _cache.get("payload")
    fetched_at = _cache.get("fetched_at") or 0.0
    if cached and (now_ts - float(fetched_at)) < CACHE_TTL_S:
        return cached  # type: ignore[return-value]

    # Fetch new
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
        f"wind_speed_10m,wind_direction_10m,precipitation,weather_code"
        f"&timezone=Europe/Lisbon"
    )
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

    cur = data.get("current", {})
    code = int(cur.get("weather_code", 0))
    payload = WeatherNow(
        location=LOCATION,
        fetched_at=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc) + timedelta(seconds=CACHE_TTL_S),
        temperature_c=float(cur.get("temperature_2m", 0)),
        feels_like_c=float(cur.get("apparent_temperature", 0)),
        humidity_pct=float(cur.get("relative_humidity_2m", 0)),
        wind_kmh=float(cur.get("wind_speed_10m", 0)),
        wind_direction_deg=float(cur.get("wind_direction_10m", 0)),
        precipitation_mm_h=float(cur.get("precipitation", 0)),
        weather_code=code,
        weather_label=_label(code),
        source="open-meteo",
    )

    _cache["payload"] = payload
    _cache["fetched_at"] = now_ts
    return payload
