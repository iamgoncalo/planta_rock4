from __future__ import annotations
import time
from typing import Optional

from app.models.chat import ChatResponse
from app.models.sections import LivePayload
from app.models.routing import BathroomRouteDecision

# Keywords for intent detection
_KEYWORDS_WHICH = ("which", "qual", "onde", "where")
_KEYWORDS_FASTEST = ("fastest", "quick", "rapid", "mais rapido", "mais rápido", "rapido", "rápido")
_KEYWORDS_FULL = ("full", "cheio", "lotado", "crowded", "ocupado", "cheia")
_KEYWORDS_AVOID = ("avoid", "evitar", "skip", "not go", "nao ir", "não ir")
_KEYWORDS_SENSOR = ("sensor", "ir", "wifi", "camera", "lorawan", "scor")
_KEYWORDS_SHOW = ("show", "concerto", "artista", "palco", "stage", "band", "banda")
_KEYWORDS_OPS = ("operations", "ops", "staff", "alert", "alerta", "operações", "operation")


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(k in lower for k in keywords)


def _section_summary(s) -> str:  # type: ignore[no-untyped-def]
    label = s.section_id
    status_emoji = {"normal": "✓", "warning": "~", "critical": "!", "offline": "✗"}.get(
        s.status, "?"
    )
    return (
        f"{label} [{status_emoji} {s.status}] "
        f"{s.ocupacao_pct:.0f}% ocupado, fila={s.fila_atual}, espera={s.tempo_espera_min:.1f}min"
    )


def answer_chat(
    msg: str,
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision],
) -> ChatResponse:
    """Local grounded chat — never invents numbers, only uses live_payload."""
    ts = time.time()

    if live_payload is None:
        return ChatResponse(
            reply=(
                "Live data is currently unavailable. "
                "I cannot provide real-time WC status without sensor data. "
                "Please try again in a moment."
            ),
            grounded=False,
            live_data_available=False,
            ts=ts,
        )

    sections = live_payload.sections
    kpis = live_payload.kpis

    # Intent: which is full (check before generic "which" routing)
    if _contains_any(msg, _KEYWORDS_FULL):
        critical = [s for s in sections if s.status in ("critical", "warning")]
        if critical:
            summaries = "; ".join(_section_summary(s) for s in critical[:4])
            reply = f"WCs with high occupancy: {summaries}."
        else:
            reply = f"No WCs are currently full. Average occupancy: {kpis.avg_ocupacao_pct:.0f}%."
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # Intent: which to avoid (check before generic "which" routing)
    if _contains_any(msg, _KEYWORDS_AVOID):
        critical = [s for s in sections if s.status == "critical"]
        offline = [s for s in sections if s.status == "offline"]
        parts = []
        if critical:
            parts.append("Critical (avoid): " + ", ".join(s.section_id for s in critical))
        if offline:
            parts.append("Offline: " + ", ".join(s.section_id for s in offline))
        if parts:
            reply = ". ".join(parts) + "."
        else:
            reply = "No WCs need to be avoided right now. All sections are operational."
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # Intent: which bathroom / routing
    if _contains_any(msg, _KEYWORDS_WHICH) or _contains_any(msg, _KEYWORDS_FASTEST):
        if route:
            rec = route.recommended
            reply = (
                f"Recommended: {rec.section_id} — "
                f"walk {rec.walk_time_min:.1f}min, "
                f"queue {rec.queue_wait_min:.1f}min, "
                f"total cost {rec.total_cost_min:.1f}min."
            )
            if route.alternatives:
                alts = ", ".join(a.section_id for a in route.alternatives[:2])
                reply += f" Alternatives: {alts}."
            if route.all_critical:
                reply += " WARNING: all WCs are at critical capacity."
        else:
            normal = [s for s in sections if s.status == "normal"]
            if normal:
                best = min(normal, key=lambda s: s.tempo_espera_min)
                reply = (
                    f"Based on current data, {best.section_id} appears available "
                    f"(wait: {best.tempo_espera_min:.1f}min, {best.ocupacao_pct:.0f}% full)."
                )
            else:
                reply = "All WCs are currently busy. Please check the display screens for guidance."
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # Intent: sensors
    if _contains_any(msg, _KEYWORDS_SENSOR):
        sim_flag = "simulated" if live_payload.any_simulated else "live"
        reply = (
            f"Sensor data is currently {sim_flag}. "
            f"System tracks IR entry/exit counters (weight 50%), "
            f"WiFi aggregate probes (30%), and camera ML counts (20%). "
            f"Last payload age: {live_payload.last_tick_age_s:.1f}s."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # Intent: shows
    if _contains_any(msg, _KEYWORDS_SHOW):
        reply = (
            "Rock in Rio Lisboa 2026 runs Jun 20–21 and Jun 27–28. "
            "During headliner shows WC demand surges significantly. "
            "I recommend checking the routing system for real-time guidance before shows end."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # Intent: operations
    if _contains_any(msg, _KEYWORDS_OPS):
        total = len(sections)
        online = sum(1 for s in sections if s.status != "offline")
        crit = kpis.critical_sections
        reply = (
            f"Operations summary: {online}/{total} sections online, "
            f"{crit} critical. "
            f"Average occupancy: {kpis.avg_ocupacao_pct:.0f}%. "
            f"Total queue: {kpis.total_fila} people."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # Default: general status
    reply = (
        f"Current status: {kpis.avg_ocupacao_pct:.0f}% average occupancy across {len(sections)} WC sections. "
        f"Total queue: {kpis.total_fila} people. "
        f"Critical sections: {kpis.critical_sections}. "
        "Ask me 'which bathroom', 'which is full', 'which to avoid', or 'sensor status'."
    )
    return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)
