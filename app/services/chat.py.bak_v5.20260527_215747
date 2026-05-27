"""
PlantaOS · Chat service
========================
Resposta via Gemini 2.5 Flash com contexto live injectado.
Fallback regra-based em PT-PT se a key falhar.

Mantém a assinatura: answer_chat(message, live_payload, route) -> ChatResponse
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from app.models.chat import ChatResponse
from app.models.sections import LivePayload  # type: ignore
from app.models.routing import BathroomRouteDecision  # type: ignore

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Gemini config (env-driven, sem fallback hardcoded)
# ----------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "8"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "512"))
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.4"))

# Tenta importar SDK uma única vez (cold start). Se faltar, fica em fallback.
_GEMINI_CLIENT: Optional[Any] = None
_GEMINI_AVAILABLE = False
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=GEMINI_API_KEY)
        _GEMINI_CLIENT = genai
        _GEMINI_AVAILABLE = True
        log.info(f"Gemini SDK ready · model={GEMINI_MODEL}")
    except Exception as e:
        log.warning(f"Gemini SDK indisponível: {e} — fallback regra-based PT-PT")
        _GEMINI_AVAILABLE = False
else:
    log.info("GEMINI_API_KEY não definida — fallback regra-based PT-PT")

# ----------------------------------------------------------------------------
# Keywords para intent detection (fallback)
# ----------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------
# Contexto: monta resumo compacto da realidade live para alimentar o LLM
# ----------------------------------------------------------------------------
def _build_context_block(
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision],
) -> str:
    """Constrói o bloco de contexto live em texto Markdown compacto.

    O Gemini recebe isto como ground-truth e foi instruído a nunca inventar."""
    if live_payload is None:
        return "ESTADO: sem dados live disponíveis neste momento."

    kpis = live_payload.kpis
    sections = list(live_payload.sections)

    lines: list[str] = []
    lines.append("## ESTADO LIVE DO FESTIVAL (Rock in Rio Lisboa · Parque Tejo)")
    lines.append(
        f"- Ocupação média: {kpis.avg_ocupacao_pct:.0f}%  "
        f"· Fila total: {kpis.total_fila}  "
        f"· Críticos: {kpis.critical_sections}"
    )
    lines.append(
        f"- Redirecionadas hoje: {kpis.redirected_count}  "
        f"· Dados {'simulados' if kpis.any_simulated else 'live'}"
    )
    lines.append("")
    lines.append("## 8 CLUSTERS WC (cada um pode ter secção M e F)")
    # Agrupa por cluster
    by_cluster: dict[str, list] = {}
    for s in sections:
        cid = s.section_id.split("_")[0]
        by_cluster.setdefault(cid, []).append(s)

    for cid in sorted(by_cluster.keys()):
        secs = by_cluster[cid]
        is_unisex = cid in ("WC-05", "WC-06")
        kind = "unisex" if is_unisex else "M+F"
        avg = sum(s.ocupacao_pct for s in secs) / max(1, len(secs))
        fila = sum(s.fila_atual for s in secs)
        wait = sum(s.tempo_espera_min for s in secs) / max(1, len(secs))
        worst = max(secs, key=lambda x: x.ocupacao_pct)
        status_word = {"normal": "OK", "warning": "atenção", "critical": "crítico", "offline": "offline"}.get(
            worst.status, worst.status
        )
        lines.append(
            f"- {cid} ({kind}): ocup {avg:.0f}% · fila {fila} · espera {wait:.1f}min · status {status_word}"
        )

    if route is not None:
        lines.append("")
        lines.append("## ROUTING RECOMENDADO AGORA")
        lines.append(
            f"- WC sugerido: {route.recommended_section}  "
            f"· caminhada {route.walk_min:.1f}min  "
            f"· fila {route.queue_min:.1f}min  "
            f"· custo total {route.total_cost_min:.1f}min"
        )
        if getattr(route, "alternatives", None):
            alts = ", ".join(route.alternatives[:3])
            lines.append(f"- Alternativas: {alts}")

    return "\n".join(lines)


# ----------------------------------------------------------------------------
# System prompt — PT-PT, factual, sem inventar
# ----------------------------------------------------------------------------
_SYSTEM_PROMPT = """És o assistente PlantaOS, ligado em tempo real aos 8 clusters WC do Rock in Rio Lisboa 2026 (Parque Tejo). Falas EXCLUSIVAMENTE em português europeu (PT-PT, não brasileiro).

REGRAS ESTRITAS:
- Responde sempre com base no bloco "ESTADO LIVE" que recebes na pergunta. Esse bloco é a única fonte de verdade.
- Se a informação não estiver no bloco, diz claramente: "Sem dados disponíveis sobre isso neste momento." NUNCA inventes valores.
- Sê conciso: 2-4 frases. Sem listas longas a menos que peçam.
- Usa números reais do bloco (ocupação %, filas, esperas). Refere clusters como WC-01, WC-02, etc.
- Quando recomendares um WC, justifica com 1-2 métricas (ex: "WC-03 está com 28% e meio minuto de espera").
- WC-05 e WC-06 são unisex. WC-01/02/03/04/07/08 têm secções masculino (M) e feminino (F) separadas.
- Nunca cites: "F=P/D", "Freedom Index", "Distortion", "seed", "hipótese", "Deucalion", "FREE algorithm". Foca-te no produto: contar pessoas, recomendar WC, alertar sobre filas.
- Tom: directo, profissional, calmo. Não és vendedor.
"""


# ----------------------------------------------------------------------------
# Gemini call
# ----------------------------------------------------------------------------
def _answer_via_gemini(
    message: str,
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision],
    ts: float,
) -> ChatResponse:
    """Chama Gemini 2.5 Flash com contexto + system prompt. Pode levantar."""
    assert _GEMINI_CLIENT is not None  # garantido pelo gating
    genai = _GEMINI_CLIENT

    context_block = _build_context_block(live_payload, route)

    # User prompt = contexto + pergunta do utilizador
    user_prompt = (
        f"{context_block}\n\n"
        f"## PERGUNTA DO UTILIZADOR\n"
        f"{message.strip()}"
    )

    # SDK genai >= 0.5: GenerativeModel + system_instruction
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=_SYSTEM_PROMPT,
        generation_config={
            "temperature": GEMINI_TEMPERATURE,
            "max_output_tokens": GEMINI_MAX_TOKENS,
            "top_p": 0.95,
        },
    )

    # Timeout via request_options (suportado pelo SDK)
    response = model.generate_content(
        user_prompt,
        request_options={"timeout": GEMINI_TIMEOUT_S},
    )

    reply_text: str = ""
    try:
        reply_text = (response.text or "").strip()
    except Exception:
        # Resposta bloqueada por safety filter ou estrutura inesperada
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            parts = getattr(candidates[0].content, "parts", None) or []
            reply_text = "".join(getattr(p, "text", "") for p in parts).strip()

    if not reply_text:
        raise RuntimeError("Gemini devolveu resposta vazia")

    return ChatResponse(
        reply=reply_text,
        grounded=True,
        live_data_available=live_payload is not None,
        ts=ts,
    )


# ----------------------------------------------------------------------------
# Fallback regra-based em PT-PT (não em inglês)
# ----------------------------------------------------------------------------
def _answer_via_rules_pt(
    message: str,
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision],
    ts: float,
) -> ChatResponse:
    msg = (message or "").strip()
    if live_payload is None:
        return ChatResponse(
            reply="Sem dados live disponíveis neste momento. Tenta de novo em alguns segundos.",
            grounded=False,
            live_data_available=False,
            ts=ts,
        )

    kpis = live_payload.kpis
    sections = list(live_payload.sections)
    if not sections:
        return ChatResponse(
            reply="Nenhuma secção a reportar dados agora.",
            grounded=True,
            live_data_available=True,
            ts=ts,
        )

    # ROUTING / qual WC ir
    if _contains_any(msg, _KEYWORDS_WHICH) or _contains_any(msg, _KEYWORDS_FASTEST):
        if route is not None:
            reply = (
                f"Recomendo {route.recommended_section}: caminhada de {route.walk_min:.1f} min "
                f"e fila de {route.queue_min:.1f} min — custo total {route.total_cost_min:.1f} min."
            )
            if getattr(route, "alternatives", None):
                alts = ", ".join(route.alternatives[:2])
                reply += f" Alternativas: {alts}."
        else:
            best = min(sections, key=lambda s: s.ocupacao_pct + s.tempo_espera_min * 5)
            reply = (
                f"O mais rápido agora é {best.section_id}: {best.ocupacao_pct:.0f}% de ocupação, "
                f"espera de {best.tempo_espera_min:.1f} min."
            )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # CHEIO / EVITAR
    if _contains_any(msg, _KEYWORDS_FULL) or _contains_any(msg, _KEYWORDS_AVOID):
        worst = max(sections, key=lambda s: s.ocupacao_pct)
        reply = (
            f"Mais cheio agora: {worst.section_id} com {worst.ocupacao_pct:.0f}% de ocupação "
            f"e fila de {worst.fila_atual} pessoas (espera {worst.tempo_espera_min:.1f} min). "
            "Considera outro cluster."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # SENSORES
    if _contains_any(msg, _KEYWORDS_SENSOR):
        sim_flag = "simulados" if kpis.any_simulated else "live"
        reply = (
            f"Os dados estão {sim_flag}. O sistema combina contadores IR de entrada e saída (peso 50%), "
            "agregação WiFi (30%) e validação por câmara (20%)."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # SHOWS
    if _contains_any(msg, _KEYWORDS_SHOW):
        reply = (
            "Rock in Rio Lisboa 2026 decorre nos dias 20–21 e 27–28 de Junho. "
            "Durante os headliners o pico de utilização dos WC é significativo — "
            "consulta /v2/shows para o surge esperado por show."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # OPS
    if _contains_any(msg, _KEYWORDS_OPS):
        total = len(sections)
        online = sum(1 for s in sections if s.status != "offline")
        reply = (
            f"Operações: {online} de {total} secções online · {kpis.critical_sections} críticas · "
            f"ocupação média {kpis.avg_ocupacao_pct:.0f}% · fila total {kpis.total_fila} pessoas."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    # Default
    reply = (
        f"Estado actual: {kpis.avg_ocupacao_pct:.0f}% de ocupação média em {len(sections)} secções WC, "
        f"fila total de {kpis.total_fila} pessoas, {kpis.critical_sections} secções críticas. "
        "Pergunta-me 'qual o WC mais rápido?', 'onde está mais cheio?' ou 'estado dos sensores'."
    )
    return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)


# ----------------------------------------------------------------------------
# Entrypoint público (assinatura preservada)
# ----------------------------------------------------------------------------
def answer_chat(
    message: str,
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision] = None,
) -> ChatResponse:
    """Responde a uma mensagem do utilizador. Tenta Gemini primeiro, depois cai em regras PT-PT."""
    ts = time.time()
    safe_msg = (message or "").strip()
    if not safe_msg:
        return ChatResponse(
            reply="Faz-me uma pergunta sobre os clusters WC, filas, ou shows.",
            grounded=False,
            live_data_available=live_payload is not None,
            ts=ts,
        )

    # 1) Tenta Gemini
    if _GEMINI_AVAILABLE:
        try:
            return _answer_via_gemini(safe_msg, live_payload, route, ts)
        except Exception as e:
            log.warning(f"Gemini falhou ({e.__class__.__name__}: {e}) — fallback PT-PT")

    # 2) Fallback regra-based PT-PT
    return _answer_via_rules_pt(safe_msg, live_payload, route, ts)
