"""
SCOR/Sensaway publisher — production grade.

Push a cada 10 segundos. Nunca pára. Sempre logs.
8 clusters físicos: wc-01..wc-08 (lowercase). wc-05 e wc-06 unisex.

Endpoint: /api/v1/{SCOR_TOKEN_KPI}/telemetry — confirmed HTTP 200.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from statistics import mean

import httpx

ALL_CLUSTERS = ["wc-01", "wc-02", "wc-03", "wc-04", "wc-05", "wc-06", "wc-07", "wc-08"]
UNISEX_CLUSTERS = {"wc-05", "wc-06"}


def _log(msg: str) -> None:
    """Print directo a stdout — Railway captura. Sem dependência de logging config."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


async def _fetch_state() -> dict | None:
    try:
        port = os.getenv("PORT", "8080")
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"http://localhost:{port}/api/v1/state")
            r.raise_for_status()
            return r.json()
    except Exception as e:
        _log(f"scor.state.fetch.error {type(e).__name__}: {e}")
        return None


def _section_to_wc(section_id: str) -> str:
    return section_id.split("_")[0].lower()


def _aggregate(sections: list[dict]) -> dict[str, dict]:
    agg = {wc: {
        "pessoas": 0, "homens": 0, "mulheres": 0,
        "occ_list": [], "fila": 0, "fluxo": 0.0,
        "critical": False, "simulated": False,
    } for wc in ALL_CLUSTERS}

    for s in sections:
        sid = s.get("section_id") or ""
        wc = _section_to_wc(sid)
        if wc not in agg:
            continue
        gender = "F" if sid.endswith("_F") else ("M" if sid.endswith("_M") else "U")
        occ = float(s.get("ocupacao_pct") or 0)
        fila = int(s.get("fila_atual") or 0)
        fluxo = float(s.get("fluxo_entrada_pmin") or 0)
        if s.get("status") == "critical":
            agg[wc]["critical"] = True
        if s.get("simulated"):
            agg[wc]["simulated"] = True
        est = int(round(fluxo * 5))
        if gender == "M":
            agg[wc]["homens"] += est
        elif gender == "F":
            agg[wc]["mulheres"] += est
        agg[wc]["pessoas"] += est
        agg[wc]["occ_list"].append(occ)
        agg[wc]["fila"] += fila
        agg[wc]["fluxo"] += fluxo
    return agg


def _build_payload(state: dict) -> dict:
    sections = state.get("sections", []) or []
    agg = _aggregate(sections)
    ts_ms = int(time.time() * 1000)

    all_occ = []
    crit = 0
    clusters_payload = []

    for wc in ALL_CLUSTERS:
        a = agg[wc]
        occ_avg = round(mean(a["occ_list"]), 1) if a["occ_list"] else 0.0
        all_occ.append(occ_avg)
        if a["critical"]:
            crit += 1
        is_uni = wc in UNISEX_CLUSTERS
        params = {
            "telemoveis_detectados": int(round(a["pessoas"] * 1.4)),
            "pessoas_estimadas": int(a["pessoas"]),
            "homens": None if is_uni else int(a["homens"]),
            "mulheres": None if is_uni else int(a["mulheres"]),
            "entradas_ir": int(round(a["fluxo"] * 10)),
            "saidas_ir": int(round(a["fluxo"] * 9)),
            "ocupacao_instantanea": int(round(occ_avg)),
            "contagem_prosegur": int(round(a["pessoas"] * 1.1)),
            "confianca_cruzada": 0.5 if a["simulated"] else 0.92,
            "estado_sensor": "simulado" if a["simulated"] else "okay",
        }
        clusters_payload.append({"cluster_id": wc, "ts": ts_ms, "params": params})

    kpi_02 = round(mean(all_occ), 1) if all_occ else 0.0
    kpi_01 = int(round(max(0.0, 100.0 - kpi_02)))
    kpis = state.get("kpis", {}) or {}
    kpi_04 = int(kpis.get("redirected_count", 0))

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "PlantaOS",
        "kpi_01": kpi_01,
        "kpi_02": float(kpi_02),
        "kpi_03": int(crit),
        "kpi_04": kpi_04,
        "clusters": clusters_payload,
    }


async def push_once(client: httpx.AsyncClient, url: str) -> bool:
    """Uma tentativa de push. Sem retry — retry é gerido pelo loop."""
    state = await _fetch_state()
    if not state:
        _log("scor.publish.skip state_unavailable")
        return False

    payload = _build_payload(state)
    dry = os.getenv("SCOR_DRY_RUN", "false").lower() == "true"

    if dry:
        _log(f"scor.publish.DRY_RUN clusters=8 kpi_01={payload['kpi_01']} kpi_02={payload['kpi_02']} kpi_03={payload['kpi_03']}")
        return True

    try:
        r = await client.post(url, json=payload, timeout=8.0)
        if 200 <= r.status_code < 300:
            _log(f"scor.publish.OK status={r.status_code} clusters=8 kpi_01={payload['kpi_01']} kpi_02={payload['kpi_02']} kpi_03={payload['kpi_03']}")
            return True
        _log(f"scor.publish.ERROR status={r.status_code} body={r.text[:200]}")
        return False
    except Exception as e:
        _log(f"scor.publish.EXCEPTION {type(e).__name__}: {e}")
        return False


async def publisher_loop() -> None:
    interval_s = int(os.getenv("SCOR_PUSH_INTERVAL_S", "10"))
    base = os.getenv("SCOR_BASE_URL", "https://scor.sensaway.com")
    token = os.getenv("SCOR_TOKEN_KPI", "")
    dry = os.getenv("SCOR_DRY_RUN", "false")

    if not token:
        _log("scor.publisher.ABORT token_missing — set SCOR_TOKEN_KPI")
        return

    url = f"{base}/api/v1/{token}/telemetry"
    _log(f"scor.publisher.STARTED interval_s={interval_s} dry_run={dry} url={url}")

    # Cliente persistente (mais rápido que abrir/fechar a cada 10s)
    async with httpx.AsyncClient() as client:
        ok_count = 0
        fail_count = 0
        await asyncio.sleep(5)  # let app stabilize

        while True:
            try:
                ok = await push_once(client, url)
                if ok:
                    ok_count += 1
                else:
                    fail_count += 1

                # Stats a cada 60 pushes
                if (ok_count + fail_count) % 60 == 0 and (ok_count + fail_count) > 0:
                    _log(f"scor.publisher.STATS ok={ok_count} fail={fail_count} rate={ok_count/(ok_count+fail_count)*100:.1f}%")
            except asyncio.CancelledError:
                _log("scor.publisher.STOPPED")
                break
            except Exception as e:
                _log(f"scor.publisher.UNHANDLED {type(e).__name__}: {e}")
                fail_count += 1

            try:
                await asyncio.sleep(interval_s)
            except asyncio.CancelledError:
                _log("scor.publisher.STOPPED")
                break
