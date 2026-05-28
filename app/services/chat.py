"""
PlantaOS · Chat service · v5 (google-genai novo SDK)
======================================================
Resposta via Gemini 2.5 Flash com contexto live injectado.
Fallback regra-based em PT-PT se a key falhar.

Mantém a assinatura: answer_chat(message, live_payload, route) -> ChatResponse
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any, Optional

from app.models.chat import ChatResponse
from app.models.sections import LivePayload  # type: ignore
from app.models.routing import BathroomRouteDecision  # type: ignore


def _log(level: str, msg: str) -> None:
    """Log com flush para garantir visibilidade nos logs Railway."""
    print(f"[chat.v5] {level}: {msg}", flush=True)


# ----------------------------------------------------------------------------
# Gemini config
# ----------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "30"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.55"))

_log("BOOT", f"chat.v5 a iniciar · model={GEMINI_MODEL} · key={'set' if GEMINI_API_KEY else 'MISSING'}")

# ----------------------------------------------------------------------------
# Init Gemini client (cold start) — usa SDK novo "google-genai"
# ----------------------------------------------------------------------------
_GEMINI_CLIENT: Optional[Any] = None
_GEMINI_TYPES: Optional[Any] = None
_GEMINI_AVAILABLE = False
_GEMINI_INIT_ERROR: Optional[str] = None
_LAST_CALL_ERROR: Optional[str] = None
_LAST_CALL_OK_TS: Optional[float] = None
_LAST_CALL_ERR_TS: Optional[float] = None

if GEMINI_API_KEY:
    try:
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore
        _GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
        _GEMINI_TYPES = genai_types
        _GEMINI_AVAILABLE = True
        _log("BOOT", f"google-genai SDK OK · client criado · model={GEMINI_MODEL}")
    except ImportError as e:
        _GEMINI_INIT_ERROR = f"ImportError: {e}"
        _log("BOOT", f"google-genai NÃO instalado: {e}")
    except Exception as e:
        _GEMINI_INIT_ERROR = f"{e.__class__.__name__}: {e}"
        _log("BOOT", f"google-genai falhou no init: {_GEMINI_INIT_ERROR}")
        traceback.print_exc()
else:
    _GEMINI_INIT_ERROR = "GEMINI_API_KEY não definida"
    _log("BOOT", _GEMINI_INIT_ERROR)


# ----------------------------------------------------------------------------
# Keywords (fallback)
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
# Contexto live → bloco compacto para o LLM
# ----------------------------------------------------------------------------
def _build_context_block(
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision],
) -> str:
    if live_payload is None:
        return ("ESTADO: o feed ao vivo esta a ligar agora. Mesmo assim, recomenda o cluster que costuma estar mais livre e convida a pessoa a tentar dentro de segundos ou a partilhar a localizacao (toca no marcador).")

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
        status_word = {
            "normal": "OK",
            "warning": "atenção",
            "critical": "crítico",
            "offline": "offline",
        }.get(worst.status, worst.status)
        lines.append(
            f"- {cid} ({kind}): ocup {avg:.0f}% · fila {fila} · espera {wait:.1f}min · status {status_word}"
        )

    if route is not None:
        lines.append("")
        lines.append("## ROUTING RECOMENDADO AGORA")
        try:
            lines.append(
                f"- WC sugerido: {route.recommended_section}  "
                f"· caminhada {route.walk_min:.1f}min  "
                f"· fila {route.queue_min:.1f}min  "
                f"· custo total {route.total_cost_min:.1f}min"
            )
        except AttributeError:
            # caso o schema de route seja diferente
            lines.append(f"- Routing: {route}")
        alts = getattr(route, "alternatives", None)
        if alts:
            try:
                lines.append(f"- Alternativas: {', '.join(alts[:3])}")
            except Exception:
                pass

    return "\n".join(lines)


# ----------------------------------------------------------------------------
# System prompt PT-PT estrito
# ----------------------------------------------------------------------------
_SYSTEM_PROMPT = """És o assistente da Planta no Rock in Rio Lisboa 2026 — ligado em tempo real aos 8 clusters de casas-de-banho do Parque Tejo. Falas em português europeu (PT-PT), com calor, clareza e um toque de humor quando encaixa.

A TUA MISSÃO: para cada pessoa, encontrar o caminho mais rápido e leve até uma casa-de-banho disponível. Há SEMPRE uma resposta útil — nunca deixes ninguém sem direcção.

COMO RESPONDES:
- Usa o bloco "ESTADO LIVE" como fonte dos números (ocupação %, filas, esperas). Refere clusters como WC-01, WC-02, etc.
- Quando recomendas um WC, justifica com 1-2 métricas reais ("WC-03 está a 28%, meio minuto de espera").
- Se te perguntam pela casa-de-banho mais próxima mas não sabes onde a pessoa está, NUNCA digas "sem dados". Em vez disso: recomenda o cluster menos cheio agora E convida-a a tocar no 📍 para partilhar a localização e afinares a sugestão.
- Se algo não está no estado live, diz o que SABES e oferece o próximo passo. Nunca um beco sem saída.
- Responde o que for preciso para ser claro — sem travar a meio, sem encolher artificialmente.

LIMITES:
- WC-05 e WC-06 são unisex. WC-01/02/03/04/07/08 têm secções masculina (M) e feminina (F).
- Nunca menciones: "F=P/D", "Freedom Index", "Distortion", "seed", "hipótese", "Deucalion". O foco é o produto: contar pessoas, recomendar WC, avisar de filas.

ESTRUTURA: respostas claras e bem organizadas, em parágrafos curtos. Quando o tema justifica, desenvolve até ~400 palavras. Termina sempre o raciocínio — nunca cortes uma ideia a meio.

TOM: caloroso e esperto, como um amigo que conhece o recinto de cor. Conciso mas completo."""


# ----------------------------------------------------------------------------
# Chamada Gemini com SDK NOVO
# ----------------------------------------------------------------------------
def _trim_to_last_sentence(text: str) -> str:
    """Se o texto parece cortado a meio (nao termina em pontuacao), apara
    ate a ultima frase completa. Blindagem contra respostas truncadas."""
    import re as _re
    t = (text or "").rstrip()
    if not t:
        return t
    if t[-1] in '.!?…")»':
        return t
    matches = list(_re.finditer(r"[.!?…](?=\s|$)", t))
    if matches:
        cut = matches[-1].end()
        trimmed = t[:cut].rstrip()
        if len(trimmed) >= 20:
            return trimmed
    return t


def _answer_via_gemini(
    message: str,
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision],
    ts: float,
) -> ChatResponse:
    """Chama Gemini 2.5 Flash com SDK google-genai (novo). Pode levantar."""
    global _LAST_CALL_ERROR, _LAST_CALL_OK_TS, _LAST_CALL_ERR_TS

    assert _GEMINI_CLIENT is not None
    assert _GEMINI_TYPES is not None

    context_block = _build_context_block(live_payload, route)
    user_prompt = (
        f"{context_block}\n\n"
        f"## PERGUNTA DO UTILIZADOR\n"
        f"{message.strip()}"
    )

    _log("CALL", f"a invocar {GEMINI_MODEL} · contexto_len={len(context_block)} chars")

    # SDK novo: client.models.generate_content(model=..., contents=..., config=GenerateContentConfig(...))
    config = _GEMINI_TYPES.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_TOKENS,
        top_p=0.95,
    )

    response = _GEMINI_CLIENT.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=config,
    )

    reply_text: str = ""
    try:
        reply_text = (response.text or "").strip()
    except Exception:
        # Tenta extrair de candidates manualmente
        try:
            cands = getattr(response, "candidates", None) or []
            if cands:
                parts = getattr(cands[0].content, "parts", None) or []
                reply_text = "".join(getattr(p, "text", "") for p in parts).strip()
        except Exception as e:
            _log("CALL", f"falha a extrair texto: {e}")

    if not reply_text:
        _LAST_CALL_ERROR = "Gemini devolveu resposta vazia"
        _LAST_CALL_ERR_TS = ts
        raise RuntimeError(_LAST_CALL_ERROR)

    reply_text = _trim_to_last_sentence(reply_text)
    _LAST_CALL_OK_TS = ts
    _LAST_CALL_ERROR = None
    _log("CALL", f"OK · reply_len={len(reply_text)} chars")

    return ChatResponse(
        reply=reply_text,
        grounded=True,
        live_data_available=live_payload is not None,
        ts=ts,
    )


# ----------------------------------------------------------------------------
# Fallback regra-based PT-PT
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

    if _contains_any(msg, _KEYWORDS_WHICH) or _contains_any(msg, _KEYWORDS_FASTEST):
        if route is not None:
            try:
                reply = (
                    f"Recomendo {route.recommended_section}: caminhada de {route.walk_min:.1f} min "
                    f"e fila de {route.queue_min:.1f} min — custo total {route.total_cost_min:.1f} min."
                )
                alts = getattr(route, "alternatives", None)
                if alts:
                    reply += f" Alternativas: {', '.join(alts[:2])}."
            except AttributeError:
                best = min(sections, key=lambda s: s.ocupacao_pct + s.tempo_espera_min * 5)
                reply = (
                    f"O mais rápido agora é {best.section_id}: {best.ocupacao_pct:.0f}% de ocupação, "
                    f"espera de {best.tempo_espera_min:.1f} min."
                )
        else:
            best = min(sections, key=lambda s: s.ocupacao_pct + s.tempo_espera_min * 5)
            reply = (
                f"O mais rápido agora é {best.section_id}: {best.ocupacao_pct:.0f}% de ocupação, "
                f"espera de {best.tempo_espera_min:.1f} min."
            )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    if _contains_any(msg, _KEYWORDS_FULL) or _contains_any(msg, _KEYWORDS_AVOID):
        worst = max(sections, key=lambda s: s.ocupacao_pct)
        reply = (
            f"Mais cheio agora: {worst.section_id} com {worst.ocupacao_pct:.0f}% de ocupação "
            f"e fila de {worst.fila_atual} pessoas (espera {worst.tempo_espera_min:.1f} min). "
            "Considera outro cluster."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    if _contains_any(msg, _KEYWORDS_SENSOR):
        sim_flag = "simulados" if kpis.any_simulated else "live"
        reply = (
            f"Os dados estão {sim_flag}. O sistema combina contadores IR de entrada e saída (peso 50%), "
            "agregação WiFi (30%) e validação por câmara (20%)."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    if _contains_any(msg, _KEYWORDS_SHOW):
        reply = (
            "Rock in Rio Lisboa 2026 decorre nos dias 20–21 e 27–28 de Junho. "
            "Durante os headliners o pico de utilização dos WC é significativo — "
            "consulta /v2/shows para o surge esperado por show."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    if _contains_any(msg, _KEYWORDS_OPS):
        total = len(sections)
        online = sum(1 for s in sections if s.status != "offline")
        reply = (
            f"Operações: {online} de {total} secções online · {kpis.critical_sections} críticas · "
            f"ocupação média {kpis.avg_ocupacao_pct:.0f}% · fila total {kpis.total_fila} pessoas."
        )
        return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)

    reply = (
        f"Estado actual: {kpis.avg_ocupacao_pct:.0f}% de ocupação média em {len(sections)} secções WC, "
        f"fila total de {kpis.total_fila} pessoas, {kpis.critical_sections} secções críticas. "
        "Pergunta-me 'qual o WC mais rápido?', 'onde está mais cheio?' ou 'estado dos sensores'."
    )
    return ChatResponse(reply=reply, grounded=True, live_data_available=True, ts=ts)


# ----------------------------------------------------------------------------
# Entrypoint público
# ----------------------------------------------------------------------------
def answer_chat(
    message: str,
    live_payload: Optional[LivePayload],
    route: Optional[BathroomRouteDecision] = None,
) -> ChatResponse:
    """Tenta Gemini · fallback PT-PT regra-based."""
    global _LAST_CALL_ERROR, _LAST_CALL_ERR_TS
    ts = time.time()
    safe_msg = (message or "").strip()
    if not safe_msg:
        return ChatResponse(
            reply="Faz-me uma pergunta sobre os clusters WC, filas, ou shows.",
            grounded=False,
            live_data_available=live_payload is not None,
            ts=ts,
        )

    if _GEMINI_AVAILABLE:
        try:
            return _answer_via_gemini(safe_msg, live_payload, route, ts)
        except Exception as e:
            err = f"{e.__class__.__name__}: {e}"
            _LAST_CALL_ERROR = err
            _LAST_CALL_ERR_TS = ts
            _log("FALL", f"Gemini falhou ({err}) — fallback PT-PT")
            traceback.print_exc()

    return _answer_via_rules_pt(safe_msg, live_payload, route, ts)


# ----------------------------------------------------------------------------
# Diagnostic snapshot (usado pelo endpoint /api/v1/chat/_debug)
# ----------------------------------------------------------------------------
def gemini_debug_state() -> dict:
    return {
        "version": "chat.v5",
        "model": GEMINI_MODEL,
        "api_key_set": bool(GEMINI_API_KEY),
        "api_key_prefix": GEMINI_API_KEY[:10] + "..." if GEMINI_API_KEY else None,
        "sdk_available": _GEMINI_AVAILABLE,
        "init_error": _GEMINI_INIT_ERROR,
        "last_call_ok_ts": _LAST_CALL_OK_TS,
        "last_call_err_ts": _LAST_CALL_ERR_TS,
        "last_call_error": _LAST_CALL_ERROR,
        "temperature": GEMINI_TEMPERATURE,
        "max_tokens": GEMINI_MAX_TOKENS,
        "timeout_s": GEMINI_TIMEOUT_S,
    }
