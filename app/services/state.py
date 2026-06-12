from __future__ import annotations
import time
import time as _time_module
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.models.sections import (
    SECTION_IDS,
    UNISEX_SECTIONS,
    SectionState,
    GlobalKPIs,
    LivePayload,
)
from app.models.sensors import IRReading, WiFiAggregateReading, CameraMLReading, SensorHealth
from app.clusters_geo import ANCHOR_GPS as _ANCHOR_GPS
from app.models.alerts import Alert
from app.models.shows import Show
from app.models.tv import TVScreenState
from app.services.simulation import simulate_tick

# ---------------------------------------------------------------------------
# Global mutable state (in-memory, single-process)
# ---------------------------------------------------------------------------
CURRENT_SCENARIO: str = "normal"
TICK: int = 0
LIVE_DATA: bool = False          # set True once real sensor data ingested
_TICK_TS: float = time.time()

# Latest ingested sensor readings (keyed by source_id)
_IR_STORE: dict[str, IRReading] = {}
_WIFI_STORE: dict[str, WiFiAggregateReading] = {}
_CAMERA_STORE: dict[str, CameraMLReading] = {}

# Alert log
_ALERTS: list[Alert] = []

# ---------------------------------------------------------------------------
# Rock in Rio Lisboa 2026 show schedule (hardcoded, at least 5 shows)
# ---------------------------------------------------------------------------
_SHOWS: list[Show] = [
    Show(
        show_id="show_jun20_headliner",
        name="Doja Cat",
        stage="Palco Mundo",
        start_iso="2026-06-20T22:00:00+01:00",
        end_iso="2026-06-20T23:30:00+01:00",
        headliner=True,
        expected_surge_pct=85.0,
    ),
    Show(
        show_id="show_jun20_superbock",
        name="Ivete Sangalo",
        stage="Super Bock Stage",
        start_iso="2026-06-20T20:00:00+01:00",
        end_iso="2026-06-20T21:30:00+01:00",
        headliner=False,
        expected_surge_pct=60.0,
    ),
    Show(
        show_id="show_jun21_headliner",
        name="Olivia Rodrigo",
        stage="Palco Mundo",
        start_iso="2026-06-21T22:00:00+01:00",
        end_iso="2026-06-21T23:30:00+01:00",
        headliner=True,
        expected_surge_pct=90.0,
    ),
    Show(
        show_id="show_jun27_headliner",
        name="Bruno Mars",
        stage="Palco Mundo",
        start_iso="2026-06-27T22:30:00+01:00",
        end_iso="2026-06-28T00:00:00+01:00",
        headliner=True,
        expected_surge_pct=95.0,
    ),
    Show(
        show_id="show_jun27_superbock",
        name="Luísa Sonza",
        stage="Super Bock Stage",
        start_iso="2026-06-27T20:30:00+01:00",
        end_iso="2026-06-27T22:00:00+01:00",
        headliner=False,
        expected_surge_pct=55.0,
    ),
    Show(
        show_id="show_jun28_headliner",
        name="Ed Sheeran",
        stage="Palco Mundo",
        start_iso="2026-06-28T22:00:00+01:00",
        end_iso="2026-06-28T23:45:00+01:00",
        headliner=True,
        expected_surge_pct=92.0,
    ),
    Show(
        show_id="show_jun28_superbock",
        name="Sam Smith",
        stage="Super Bock Stage",
        start_iso="2026-06-28T19:30:00+01:00",
        end_iso="2026-06-28T21:00:00+01:00",
        headliner=False,
        expected_surge_pct=50.0,
    ),
]


# ---------------------------------------------------------------------------
# Static GPS centroids for direction text (used by TV screens)
# ---------------------------------------------------------------------------
_WC_DIRECTIONS: dict[str, str] = {
    "WC-01": "Norte — junto à entrada principal",
    "WC-02": "Nordeste — perto do Palco Mundo",
    "WC-03": "Sul — junto ao Super Bock Stage",
    "WC-04": "Este — Zona VIP",
    "WC-05": "Oeste — Praça da Alimentação",
    "WC-06": "Sudeste — Área de Campismo",
    "WC-07": "Noroeste — Estacionamento",
    "WC-08": "Centro — Praça Central",
}


def _cluster_id(section_id: str) -> str:
    return section_id.split("_")[0] if "_" in section_id else section_id


# ---------------------------------------------------------------------------
# SNAPSHOT ÚNICO POR TICK (in-memory, single-process)
# ---------------------------------------------------------------------------
# O motor canónico gera UM objecto de estado por tick: payload (14 secções)
# + vista telemetry (8 clusters + kpis), construídos UMA vez e servidos a
# TODOS os endpoints de leitura (/flow, /telemetry, /state, /kpis, /tv,
# /sections). Dois curls no mesmo tick devolvem números idênticos por
# construção — é este objecto que o cache edge serve a 100k pessoas.
# Invalidação: advance_tick / ingest / fusão demo põem data=None.
# NOTA multi-worker: o Railway corre 1 processo uvicorn (railway.json);
# com vários workers este cache passaria a Redis com TTL=70s.
_PAYLOAD_CACHE: dict = {"data": None, "ts": 0.0, "derived": None}
_PAYLOAD_TTL = 60.0   # fallback — o tick (advance_tick) invalida primeiro


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_live_payload() -> LivePayload:
    """Return the current live (or simulated) state (cached 5 s)."""
    now = _time_module.monotonic()
    if _PAYLOAD_CACHE["data"] is not None and (now - _PAYLOAD_CACHE["ts"]) < _PAYLOAD_TTL:
        return _PAYLOAD_CACHE["data"]  # type: ignore[return-value]

    sections = simulate_tick(CURRENT_SCENARIO, TICK)

    # Enriquecer com resultados de fusao canonicos (§3.5) quando disponiveis
    from app.fusion import get_fused
    enriched: list[SectionState] = []
    for s in sections:
        fr = get_fused(s.section_id.lower())
        if fr is not None and not fr.stale:
            enriched.append(s.model_copy(update={
                "ocupacao_pct": fr.ocupacao_pct,
                "fila_atual": fr.fila_actual,
                "tempo_espera_min": fr.tempo_espera_min,
                "fluxo_entrada_pmin": fr.fluxo_entrada_pmin,
                "confianca": fr.confianca,
                "fontes_activas": fr.fontes_activas,
                "stale": fr.stale,
                "simulated": False,
            }))
        else:
            enriched.append(s)
    sections = enriched

    # Fusão rolante (cabeças + WiFi): expõe ocupacao/fila/confianca_cruzada/
    # a_actual/idade_ancora_s/nos_online/flag_anomalia por secção com dados
    try:
        from app.services import fusao_rolante, secoes_mf
        rolante = fusao_rolante.get_all()
        fechados = secoes_mf.estado_fechados()
        if rolante or fechados:
            enriched2: list[SectionState] = []
            for s in sections:
                sid = s.section_id.lower()
                cid = sid.split("_")[0]
                rp = rolante.get(sid)
                extra: dict = {}
                if rp is not None:
                    # Denominador: capacidade do payload rolante; se faltar,
                    # cai para a tabela oficial (clusters_capacity) — NUNCA
                    # para 1, que produzia um falso ocupacao_pct=100 nas
                    # secções unissexo (WC-05/WC-06, sem chave de género).
                    cap = int(rp.get("capacidade") or 0)
                    if cap <= 0:
                        from app.clusters_capacity import (
                            capacity_gender, capacity_inside, is_unisex,
                        )
                        cap = (capacity_inside(cid) if is_unisex(cid)
                               else capacity_gender(cid, sid.split("_")[-1].upper()))
                    cap = max(cap, 1)
                    fila = float(rp["fila_estimada"])
                    extra = {
                        "ocupacao_pct": round(min(100.0, max(
                            0.0, float(rp["ocupacao"]) / cap * 100.0)), 1),
                        "fila_estimada": fila,
                        "confianca_cruzada": rp["confianca_cruzada"],
                        "a_actual": rp["a_actual"],
                        "idade_ancora_s": rp["idade_ancora_s"],
                        "nos_online": rp["nos_online"],
                        "flag_anomalia": rp["flag_anomalia"],
                        "espera_prevista_min": secoes_mf.espera_prevista_min(sid, fila),
                        "queue_cap": secoes_mf.queue_cap(sid),
                        "alerta_fila": secoes_mf.alerta_fila(sid, fila),
                        "simulated": False,
                    }
                if fechados.get(cid, {}).get("fechado"):
                    extra["fechado"] = True
                    extra["alerta_fila"] = "CRIT"
                enriched2.append(s.model_copy(update=extra) if extra else s)
            sections = enriched2
    except Exception:
        pass  # a fusão rolante nunca pode derrubar o /state

    # Ocupação absoluta canónica: round(pct × cap oficial / 100), calculada
    # UMA vez aqui — /flow e /telemetry consomem ESTE inteiro (mesmo
    # arredondamento por construção). Secções U usam a capacidade única do
    # cluster (133/208), sem chave de género.
    try:
        from app.clusters_capacity import capacity_gender, capacity_inside
        com_abs: list[SectionState] = []
        for s in sections:
            cid = _cluster_id(s.section_id).lower()
            if s.section_id in UNISEX_SECTIONS:
                cap = capacity_inside(cid)
            else:
                cap = capacity_gender(cid, s.section_id.split("_")[1])
            abs_ = int(round(s.ocupacao_pct * cap / 100.0)) if cap > 0 else 0
            com_abs.append(s.model_copy(update={"ocupacao_abs": abs_}))
        sections = com_abs
    except Exception:
        pass  # sem capacidades, as secções seguem com ocupacao_abs=None

    # Flags de ambiente (chuva/calor/vento) — informativo, nunca parte o /state
    ambiente_estado: Optional[dict] = None
    try:
        from app.services import ambiente
        ambiente_estado = ambiente.estado_resumo()
    except Exception:
        ambiente_estado = None

    # Compute KPIs
    total = len(sections)
    avg_occ = sum(s.ocupacao_pct for s in sections) / total if total else 0.0
    total_fila = sum(s.fila_atual for s in sections)
    critical_count = sum(1 for s in sections if s.status == "critical")
    redirected = sum(1 for s in sections if s.status == "critical" and s.fila_atual > 10)
    any_sim = any(s.simulated for s in sections)

    # Carimbo único do snapshot (ms) — TODOS os endpoints devolvem este valor
    snapshot_ts = int(time.time() * 1000)

    kpis = GlobalKPIs(
        avg_ocupacao_pct=round(avg_occ, 1),
        total_fila=total_fila,
        critical_sections=critical_count,
        redirected_count=redirected,
        any_simulated=any_sim,
        snapshot_ts=snapshot_ts,
    )

    # Build alert messages
    alert_msgs = [a.message for a in _ALERTS if not a.acknowledged]

    result = LivePayload(
        kpis=kpis,
        sections=sections,
        alerts=alert_msgs,
        last_tick_age_s=round(time.time() - _TICK_TS, 1),
        any_simulated=any_sim,
        ambiente=ambiente_estado,
        snapshot_ts=snapshot_ts,
    )
    # Vista telemetry (8 clusters + kpis) derivada do MESMO objecto, no MESMO
    # build — /telemetry serve isto sem recomputar nada por request.
    try:
        from app.services import cluster_telemetry
        state_dict = result.model_dump()
        derived = {
            "clusters": cluster_telemetry.build_cluster_payload(state_dict),
            "kpis": cluster_telemetry.build_kpis(state_dict),
        }
    except Exception:
        derived = None  # /telemetry recompõe defensivamente se faltar

    _PAYLOAD_CACHE["data"] = result
    _PAYLOAD_CACHE["ts"] = now
    _PAYLOAD_CACHE["derived"] = derived
    return result


def get_tick_snapshot() -> dict:
    """Snapshot único do tick: payload canónico + vista telemetry.

    TODOS os endpoints de leitura servem deste objecto — um tick, um objecto,
    todos leem o mesmo."""
    payload = get_live_payload()
    derived = _PAYLOAD_CACHE.get("derived")
    if derived is None:  # build da vista falhou — recompõe uma vez, defensivo
        from app.services import cluster_telemetry
        state_dict = payload.model_dump()
        derived = {
            "clusters": cluster_telemetry.build_cluster_payload(state_dict),
            "kpis": cluster_telemetry.build_kpis(state_dict),
        }
        _PAYLOAD_CACHE["derived"] = derived
    return {"payload": payload, **derived}


def get_section_state(section_id: str) -> SectionState:
    payload = get_live_payload()
    for s in payload.sections:
        if s.section_id == section_id:
            return s
    raise KeyError(section_id)


def get_sensor_health() -> list[SensorHealth]:
    """Return SensorHealth for each of the 8 clusters."""
    now = time.time()
    clusters = ["WC-01", "WC-02", "WC-03", "WC-04", "WC-05", "WC-06", "WC-07", "WC-08"]
    result = []

    ir_degraded = CURRENT_SCENARIO in ("ir_offline",)
    wifi_degraded = CURRENT_SCENARIO in ("wifi_offline",)
    camera_degraded = CURRENT_SCENARIO in ("camera_offline",)
    all_degraded = CURRENT_SCENARIO == "all_sensors_degraded"

    for cluster in clusters:
        ir_ok = not (ir_degraded or all_degraded)
        wifi_ok = not (wifi_degraded or all_degraded)
        cam_ok = not (camera_degraded or all_degraded)
        lorawan_ok = CURRENT_SCENARIO != "lorawan_fallback"

        active = []
        issues: list[str] = []
        if ir_ok:
            active += ["ir_entry", "ir_exit"]
        else:
            issues.append("ir_offline")
        if wifi_ok:
            active.append("wifi")
        else:
            issues.append("wifi_offline")
        if cam_ok:
            active.append("camera")
        else:
            issues.append("camera_offline")

        # Confidence: proportional to active sensors
        max_sources = 4  # ir_entry, ir_exit, wifi, camera
        confidence = len(active) / max_sources

        result.append(SensorHealth(
            cluster_id=cluster,
            lilygo_online=ir_ok or wifi_ok,
            lilygo_last_seen=now if (ir_ok or wifi_ok) else now - 120,
            ir_entry_online=ir_ok,
            ir_exit_online=ir_ok,
            wifi_online=wifi_ok,
            camera_online=cam_ok,
            lorawan_available=lorawan_ok,
            active_sources=active,
            confidence=round(confidence, 3),
            issues=issues,
            last_update_ts=now,
            simulated=True,
        ))

    return result


def get_alerts() -> list[Alert]:
    """Return current alert list, auto-generating from critical sections."""
    now = time.time()
    sections = simulate_tick(CURRENT_SCENARIO, TICK)

    active_alerts: list[Alert] = list(_ALERTS)

    for s in sections:
        if s.status == "critical":
            # Check if we already have an unacknowledged alert for this section
            exists = any(
                a.section_id == s.section_id and not a.acknowledged
                for a in active_alerts
            )
            if not exists:
                active_alerts.append(Alert(
                    alert_id=f"auto_{s.section_id}_{int(now)}",
                    severity="critical",
                    section_id=s.section_id,
                    message=f"{s.section_id} at critical capacity ({s.ocupacao_pct:.0f}%)",
                    ts=now,
                    acknowledged=False,
                ))
        elif s.status == "warning":
            exists = any(
                a.section_id == s.section_id and a.severity == "warning" and not a.acknowledged
                for a in active_alerts
            )
            if not exists:
                active_alerts.append(Alert(
                    alert_id=f"warn_{s.section_id}_{int(now)}",
                    severity="warning",
                    section_id=s.section_id,
                    message=f"{s.section_id} approaching capacity ({s.ocupacao_pct:.0f}%)",
                    ts=now,
                    acknowledged=False,
                ))

    return active_alerts


def get_shows() -> list[Show]:
    return _SHOWS


def get_active_show() -> Optional[Show]:
    """Return the show currently active, or None."""
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    for show in _SHOWS:
        if show.start_iso <= now_iso <= show.end_iso:
            return show
    return None


def advance_tick(scenario: str) -> None:
    """Increment TICK and update scenario."""
    global CURRENT_SCENARIO, TICK, _TICK_TS
    CURRENT_SCENARIO = scenario
    TICK += 1
    _TICK_TS = time.time()
    # novo tick → novo snapshot único (o TTL é só fallback)
    _PAYLOAD_CACHE["data"] = None
    _PAYLOAD_CACHE["derived"] = None


def ingest_ir(reading: IRReading) -> None:
    """Store IR reading, mark live data active."""
    global LIVE_DATA
    _IR_STORE[reading.source_id] = reading
    LIVE_DATA = True


def ingest_wifi(reading: WiFiAggregateReading) -> None:
    """Store WiFi aggregate reading. No MAC addresses stored."""
    global LIVE_DATA
    _WIFI_STORE[reading.source_id] = reading
    LIVE_DATA = True


def ingest_camera(reading: CameraMLReading) -> None:
    """Store camera ML reading."""
    global LIVE_DATA
    _CAMERA_STORE[reading.source_id] = reading
    LIVE_DATA = True


def get_tv_state(screen_id: str) -> TVScreenState:
    """Compute TV screen state based on current live payload and routing."""
    from app.services.routing import compute_route

    now = time.time()
    payload = get_live_payload()
    active_show = get_active_show()

    # Use a fixed reference point for each screen (centre of venue as default)
    # Screens are assumed at the centre; a real implementation would map screen_id -> GPS
    user_lat = _ANCHOR_GPS["lat"]
    user_lon = _ANCHOR_GPS["lon"]

    try:
        route = compute_route(payload.sections, user_lat, user_lon, active_show)
        recommended = route.recommended.section_id
        alt = route.alternatives[0].section_id if route.alternatives else None
        walk_min = route.recommended.walk_time_min
        queue_min = route.recommended.queue_wait_min
        critical_override = route.all_critical
        avoid = [o.section_id for o in route.alternatives if "critical" in o.avoidance_reasons]
    except Exception:
        recommended = "WC-05"
        alt = None
        walk_min = 2.0
        queue_min = 1.0
        critical_override = False
        avoid = []

    cluster = _cluster_id(recommended)
    direction = _WC_DIRECTIONS.get(cluster, "Siga as indicações")

    return TVScreenState(
        screen_id=screen_id,
        recommended_section=recommended,
        direction=direction,
        walk_time_min=walk_min,
        queue_wait_min=queue_min,
        alternative_section=alt,
        avoid_list=avoid,
        critical_override=critical_override,
        last_update_ts=now,
        any_simulated=payload.any_simulated,
        snapshot_ts=payload.snapshot_ts,
    )
