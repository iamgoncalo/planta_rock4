"""
SCOR / Sensaway publisher — porta do backend B.

Push a cada SCOR_PUSH_INTERVAL_S segundos para:
  POST https://scor.sensaway.com/api/v1/{SCOR_TOKEN_KPI}/telemetry

Body único: 4 KPIs + array de 14 clusters (WC-01_M, WC-01_F, ..., WC-05, WC-06, ...).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from statistics import mean
from typing import Any

import httpx

from app.services.state import get_kpis, get_sections

log = logging.getLogger(__name__)


def _build_payload() -> dict[str, Any]:
    """Compõe o body do POST a partir do estado actual (sections + kpis)."""
    kpis = get_kpis()
    sections = get_sections()

    sec_list = sections if isinstance(sections, list) else list(sections)

    occ_values = []
    crit_count = 0
    for s in sec_list:
        occ = getattr(s, "ocupacao_pct", None) if hasattr(s, "ocupacao_pct") else s.get("ocupacao_pct")
        status = getattr(s, "status", None) if hasattr(s, "status") else s.get("status")
        if occ is not None:
            occ_values.append(float(occ))
        if status == "critical":
            crit_count += 1

    kpi_02 = round(mean(occ_values), 1) if occ_values else 0.0
    kpi_01 = round(max(0.0, 100.0 - kpi_02))
    kpi_03 = crit_count
    kpi_04 = getattr(kpis, "redirected_count", 0) if hasattr(kpis, "redirected_count") \
             else (kpis.get("redirected_count", 0) if isinstance(kpis, dict) else 0)

    clusters_payload = []
    for s in sec_list:
        sid = getattr(s, "section_id", None) if hasattr(s, "section_id") else s.get("section_id")
        if not sid:
            continue
        fila = getattr(s, "fila_atual", None) if hasattr(s, "fila_atual") else s.get("fila_atual", 0)
        tesp = getattr(s, "tempo_espera_min", None) if hasattr(s, "tempo_espera_min") else s.get("tempo_espera_min", 0)
        fent = getattr(s, "fluxo_entrada_pmin", None) if hasattr(s, "fluxo_entrada_pmin") else s.get("fluxo_entrada_pmin", 0)
        opct = getattr(s, "ocupacao_pct", None) if hasattr(s, "ocupacao_pct") else s.get("ocupacao_pct", 0)
        gen = getattr(s, "gender", None) if hasattr(s, "gender") else s.get("gender", "UNISSEX")

        # WC-05 e WC-06 são UNISSEX → genero "UNISSEX"
        # Outras secções têm sufixo _M ou _F → genero "M" / "F"
        if sid in ("WC-05", "WC-06"):
            genero = "UNISSEX"
        elif sid.endswith("_M"):
            genero = "M"
        elif sid.endswith("_F"):
            genero = "F"
        else:
            genero = gen or "UNISSEX"

        clusters_payload.append({
            "cluster_id": sid,
            "fila_actual": int(fila or 0),
            "tempo_espera_min": round(float(tesp or 0), 1),
            "fluxo_entrada_pmin": round(float(fent or 0)),
            "ocupacao_pct": round(float(opct or 0), 1),
            "genero": genero,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "PlantaOS",
        "kpi_01": int(kpi_01),
        "kpi_02": float(kpi_02),
        "kpi_03": int(kpi_03),
        "kpi_04": int(kpi_04),
        "clusters": clusters_payload,
    }


async def push_once() -> bool:
    """Publica 1 payload. Devolve True se 2xx."""
    base = os.getenv("SCOR_BASE_URL", "https://scor.sensaway.com")
    token = os.getenv("SCOR_TOKEN_KPI", "")
    if not token:
        log.warning("scor.publish.skip token_missing")
        return False

    if os.getenv("SCOR_DRY_RUN", "true").lower() == "true":
        payload = _build_payload()
        log.info(f"scor.publish.dry_run clusters={len(payload['clusters'])} kpi_01={payload['kpi_01']} kpi_02={payload['kpi_02']}")
        return True

    url = f"{base}/api/v1/{token}/telemetry"
    payload = _build_payload()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if 200 <= r.status_code < 300:
                log.info(f"scor.publish.ok status={r.status_code} clusters={len(payload['clusters'])} kpi_01={payload['kpi_01']} kpi_02={payload['kpi_02']}")
                return True
            log.warning(f"scor.publish.error status={r.status_code} body={r.text[:200]}")
            return False
    except Exception as e:
        log.warning(f"scor.publish.exception {type(e).__name__}: {e}")
        return False


async def publisher_loop() -> None:
    """Loop background, intervalo de SCOR_PUSH_INTERVAL_S segundos (default 60)."""
    interval_s = int(os.getenv("SCOR_PUSH_INTERVAL_S", "60"))
    log.info(f"scor.publisher.started interval_s={interval_s} dry_run={os.getenv('SCOR_DRY_RUN','true')}")
    # Push inicial após 20s (deixar a app estabilizar)
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
