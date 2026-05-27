"""SCOR/Sensaway publisher — consome o próprio /api/v1/state."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from statistics import mean

import httpx

log = logging.getLogger(__name__)


async def _fetch_state() -> dict | None:
    """Lê o estado actual via o endpoint local /api/v1/state."""
    try:
        port = os.getenv("PORT", "8080")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"http://localhost:{port}/api/v1/state")
            r.raise_for_status()
            return r.json()
    except Exception as e:
        log.warning(f"scor.state.fetch.error {type(e).__name__}: {e}")
        return None


def _build_payload(state: dict) -> dict:
    """Compõe o body do POST a partir de /api/v1/state."""
    kpis = state.get("kpis", {}) or {}
    sections = state.get("sections", []) or []

    occ_values = [float(s.get("ocupacao_pct", 0)) for s in sections if s.get("ocupacao_pct") is not None]
    crit_count = sum(1 for s in sections if s.get("status") == "critical")

    kpi_02 = round(mean(occ_values), 1) if occ_values else 0.0
    kpi_01 = int(round(max(0.0, 100.0 - kpi_02)))
    kpi_03 = int(crit_count)
    kpi_04 = int(kpis.get("redirected_count", 0))

    clusters = []
    for s in sections:
        sid = s.get("section_id")
        if not sid:
            continue
        if sid in ("WC-05", "WC-06"):
            genero = "UNISSEX"
        elif sid.endswith("_M"):
            genero = "M"
        elif sid.endswith("_F"):
            genero = "F"
        else:
            genero = s.get("gender") or "UNISSEX"
        clusters.append({
            "cluster_id": sid,
            "fila_actual": int(s.get("fila_atual", 0) or 0),
            "tempo_espera_min": round(float(s.get("tempo_espera_min", 0) or 0), 1),
            "fluxo_entrada_pmin": round(float(s.get("fluxo_entrada_pmin", 0) or 0)),
            "ocupacao_pct": round(float(s.get("ocupacao_pct", 0) or 0), 1),
            "genero": genero,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "PlantaOS",
        "kpi_01": kpi_01,
        "kpi_02": float(kpi_02),
        "kpi_03": kpi_03,
        "kpi_04": kpi_04,
        "clusters": clusters,
    }


async def push_once() -> bool:
    base = os.getenv("SCOR_BASE_URL", "https://scor.sensaway.com")
    token = os.getenv("SCOR_TOKEN_KPI", "")
    if not token:
        log.warning("scor.publish.skip token_missing")
        return False

    state = await _fetch_state()
    if not state:
        log.warning("scor.publish.skip state_unavailable")
        return False

    payload = _build_payload(state)

    if os.getenv("SCOR_DRY_RUN", "true").lower() == "true":
        log.info(f"scor.publish.dry_run clusters={len(payload['clusters'])} kpi_01={payload['kpi_01']} kpi_02={payload['kpi_02']} kpi_03={payload['kpi_03']}")
        return True

    url = f"{base}/api/v1/{token}/telemetry"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if 200 <= r.status_code < 300:
                log.info(f"scor.publish.ok status={r.status_code} clusters={len(payload['clusters'])} kpi_01={payload['kpi_01']} kpi_02={payload['kpi_02']} kpi_03={payload['kpi_03']}")
                return True
            log.warning(f"scor.publish.error status={r.status_code} body={r.text[:200]}")
            return False
    except Exception as e:
        log.warning(f"scor.publish.exception {type(e).__name__}: {e}")
        return False


async def publisher_loop() -> None:
    interval_s = int(os.getenv("SCOR_PUSH_INTERVAL_S", "60"))
    log.info(f"scor.publisher.started interval_s={interval_s} dry_run={os.getenv('SCOR_DRY_RUN','true')}")
    await asyncio.sleep(20)
    while True:
        try:
            await push_once()
        except asyncio.CancelledError:
            log.info("scor.publisher.stopped")
            break
        except Exception as e:
            log.error(f"scor.publisher.unhandled {type(e).__name__}: {e}")
        try:
            await asyncio.sleep(interval_s)
        except asyncio.CancelledError:
            log.info("scor.publisher.stopped")
            break
