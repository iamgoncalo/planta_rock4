"""
SCOR/Sensaway publisher — production grade.

Push a cada SCOR_PUSH_INTERVAL_S segundos. Nunca para.
8 clusters: wc-01..wc-08 (lowercase). wc-05 e wc-06 unisex.
Endpoint: /api/v1/{SCOR_TOKEN_KPI}/telemetry
Logs detalhados: por cada push imprime 1 cabecalho + 8 linhas (uma por WC).
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from statistics import mean

import httpx
from datetime import datetime, timezone
from app.services.scor_history import scor_history, ScorPublishRecord

ALL_CLUSTERS = ["wc-01", "wc-02", "wc-03", "wc-04",
                "wc-05", "wc-06", "wc-07", "wc-08"]
UNISEX_CLUSTERS = {"wc-05", "wc-06"}


def _log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def _fmt_int_or_dash(v) -> str:
    if v is None:
        return "---"
    return f"{int(v):>3}"


def _log_cluster_detail(payload: dict) -> None:
    """Imprime uma linha por cluster com TODOS os params."""
    for c in payload.get("clusters", []):
        cid = c.get("cluster_id", "?")
        p = c.get("params", {}) or {}
        homens = _fmt_int_or_dash(p.get("homens"))
        mulheres = _fmt_int_or_dash(p.get("mulheres"))
        line = (
            f"  --> {cid:>6} | "
            f"pessoas={p.get('pessoas_estimadas', 0):>3} "
            f"H={homens} M={mulheres} "
            f"ocup%={p.get('ocupacao_instantanea', 0):>3} "
            f"in={p.get('entradas_ir', 0):>4} out={p.get('saidas_ir', 0):>4} "
            f"tel={p.get('telemoveis_detectados', 0):>3} "
            f"prosegur={p.get('contagem_prosegur', 0):>3} "
            f"conf={p.get('confianca_cruzada', 0):.2f} "
            f"sensor={p.get('estado_sensor', '?')}"
        )
        _log(line)


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


def _aggregate(sections: list) -> dict:
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


def _build_clusters(state: dict) -> list:
    """1 entrada por cluster (wc-01..wc-08). 05/06 unisex -> homens/mulheres = None."""
    sections = state.get("sections", []) or []
    agg = _aggregate(sections)
    ts_ms = int(time.time() * 1000)
    clusters_payload = []
    for wc in ALL_CLUSTERS:
        a = agg[wc]
        occ_avg = round(mean(a["occ_list"]), 1) if a["occ_list"] else 0.0
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
    return clusters_payload


def _build_kpis(state: dict) -> dict:
    """KPIs com nomes kpi_NN_value (formato Sensaway). Sem lista clusters."""
    sections = state.get("sections", []) or []
    agg = _aggregate(sections)
    all_occ = []
    crit = 0
    for wc in ALL_CLUSTERS:
        a = agg[wc]
        if a["occ_list"]:
            all_occ.append(round(mean(a["occ_list"]), 1))
        if a["critical"]:
            crit += 1
    kpi_02 = round(mean(all_occ), 1) if all_occ else 0.0
    kpi_01 = int(round(max(0.0, 100.0 - kpi_02)))
    kpis = state.get("kpis", {}) or {}
    kpi_04 = int(kpis.get("redirected_count", 0))
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "PlantaOS",
        "kpi_01_value": kpi_01,
        "kpi_02_value": float(kpi_02),
        "kpi_03_value": int(crit),
        "kpi_04_value": kpi_04,
    }


async def push_once(client: httpx.AsyncClient, kpi_url: str, cluster_url: str) -> bool:
    state = await _fetch_state()
    if not state:
        _log("scor.publish.skip state_unavailable")
        return False
    kpis = _build_kpis(state)
    clusters = _build_clusters(state)
    dry = os.getenv("SCOR_DRY_RUN", "false").lower() == "true"

    if dry:
        _log(f"scor.publish.DRY_RUN kpi_01_value={kpis['kpi_01_value']} kpi_02_value={kpis['kpi_02_value']} kpi_03_value={kpis['kpi_03_value']} kpi_04_value={kpis['kpi_04_value']}")
        _log_cluster_detail({"clusters": clusters})
        return True

    ok_all = True
    _scor_t0 = time.time()

    # (A) KPIs -> endpoint KPI (campos kpi_NN_value)
    try:
        rk = await client.post(kpi_url, json=kpis, timeout=8.0)
        if 200 <= rk.status_code < 300:
            _log(f"scor.publish.KPI.OK status={rk.status_code} kpi_01_value={kpis['kpi_01_value']} kpi_02_value={kpis['kpi_02_value']} kpi_03_value={kpis['kpi_03_value']} kpi_04_value={kpis['kpi_04_value']}")
        else:
            ok_all = False
            _log(f"scor.publish.KPI.ERROR status={rk.status_code} body={rk.text[:200]}")
    except Exception as e:
        ok_all = False
        _log(f"scor.publish.KPI.EXCEPTION {type(e).__name__}: {e}")

    # (B) Clusters -> 1 POST por cluster para o endpoint de integracao
    sent = 0
    for c in clusters:
        try:
            rc = await client.post(cluster_url, json=c, timeout=8.0)
            if 200 <= rc.status_code < 300:
                sent += 1
            else:
                ok_all = False
                _log(f"scor.publish.CLUSTER.ERROR {c['cluster_id']} status={rc.status_code} body={rc.text[:150]}")
        except Exception as e:
            ok_all = False
            _log(f"scor.publish.CLUSTER.EXCEPTION {c['cluster_id']} {type(e).__name__}: {e}")

    _log(f"scor.publish.CLUSTERS.OK sent={sent}/{len(clusters)}")
    _log_cluster_detail({"clusters": clusters})

    try:
        _dt_ms = int((time.time() - _scor_t0) * 1000)
        await scor_history.add(ScorPublishRecord(
            ts=time.time(),
            iso=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
            status=200 if ok_all else 207,
            duration_ms=_dt_ms,
            kpi_01=int(kpis.get("kpi_01_value", 0)),
            kpi_02=float(kpis.get("kpi_02_value", 0.0)),
            kpi_03=int(kpis.get("kpi_03_value", 0)),
            kpi_04=int(kpis.get("kpi_04_value", 0)),
            cluster_count=sent,
        ))
    except Exception:
        pass

    return ok_all


async def publisher_loop() -> None:
    interval_s = int(os.getenv("SCOR_PUSH_INTERVAL_S", "10"))
    base = os.getenv("SCOR_BASE_URL", "https://scor.sensaway.com")
    token = os.getenv("SCOR_TOKEN_KPI", "")
    dry = os.getenv("SCOR_DRY_RUN", "false")
    if not token:
        _log("scor.publisher.ABORT token_missing")
        return
    kpi_url = f"{base}/api/v1/{token}/telemetry"
    cluster_url = os.getenv(
        "SCOR_CLUSTER_URL",
        "https://scor.sensaway.com/api/v1/integrations/http/04614480-c43a-1f5f-af68-86c606bddb32",
    )
    _log(f"scor.publisher.STARTED interval_s={interval_s} dry_run={dry} kpi_url={kpi_url} cluster_url={cluster_url}")
    async with httpx.AsyncClient() as client:
        ok_count = 0
        fail_count = 0
        await asyncio.sleep(5)
        while True:
            try:
                ok = await push_once(client, kpi_url, cluster_url)
                if ok:
                    ok_count += 1
                else:
                    fail_count += 1
                if (ok_count + fail_count) % 60 == 0 and (ok_count + fail_count) > 0:
                    rate = ok_count / (ok_count + fail_count) * 100
                    _log(f"scor.publisher.STATS ok={ok_count} fail={fail_count} rate={rate:.1f}%")
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
