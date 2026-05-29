"""
PlantaOS · Rock in Rio Lisboa 2026
Endpoint do chat Gemini para a pagina /v2/ambientes/rirstaff

Adicionar ao backend FastAPI (app/ ou api.py). Liga ao Gemini 2.5 Flash
e responde com base no estado REAL das casas de banho do staff.

INSTALAR:  pip install google-generativeai
VARIAVEL DE AMBIENTE (no Railway):  GEMINI_RIRSTAFF_KEY=<a tua key>
  (key separada, so para esta pagina, como pediste)
"""
import os
import time
import google.generativeai as genai
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/rirstaff", tags=["rirstaff-chat"])

# key SEPARADA so para esta pagina (mete a tua no Railway)
GEMINI_KEY = os.getenv("GEMINI_RIRSTAFF_KEY", "POE_A_TUA_KEY_AQUI")
genai.configure(api_key=GEMINI_KEY)

MODELO = "gemini-2.5-flash"

# o estado atual vem do teu store de telemetria (a mesma fonte que /rirstaff)
# substitui esta funcao pela tua leitura real do estado dos clusters
def estado_casas_banho() -> dict:
    """Devolve o estado atual das casas de banho staff.
    LIGAR aqui a tua fonte real (a mesma que alimenta GET /api/v1/rirstaff)."""
    from app.store import get_rirstaff_state  # adapta ao teu projeto
    try:
        return get_rirstaff_state()
    except Exception:
        return {}

def contexto_sistema(estado: dict) -> str:
    linhas = []
    for cid, d in (estado or {}).items():
        nome = d.get("nome", cid)
        ocup = d.get("ocupacao", "?")
        cap = d.get("capacidade", "?")
        pct = d.get("ocupacao_pct", "?")
        est = d.get("estado", "?")
        online = d.get("online", False)
        linhas.append(f"- {nome}: {ocup}/{cap} pessoas ({pct}%), estado={est}, online={online}")
    estado_txt = "\n".join(linhas) if linhas else "Sem dados em tempo real neste momento."
    return f"""Es o assistente do PlantaOS para o staff do Rock in Rio Lisboa 2026.
Ajudas o staff a saber se podem ir a casa de banho agora, qual a menos cheia, e quanto tempo esperar.

ESTADO ATUAL DAS CASAS DE BANHO DO STAFF (tempo real):
{estado_txt}

REGRAS:
- Responde curto, simples, em portugues de Portugal. Maximo 2-3 frases.
- Se perguntarem "posso ir agora?": olha o estado. LIVRE/MEDIO = sim, vai. QUASE/CHEIO = sugere esperar uns minutos ou ir a outra.
- Se houver mais que uma casa de banho, recomenda a menos cheia.
- Se nao houver dados (online=false), diz que nao tens leitura agora e que e melhor verificar no local.
- Nunca inventes numeros. Usa so os do estado acima.
- Tom amigavel e direto, como um colega prestavel."""

class ChatPedido(BaseModel):
    mensagem: str
    historico: list[dict] = []   # [{role:"user"/"model", text:"..."}]

@router.post("/chat")
def chat(pedido: ChatPedido):
    estado = estado_casas_banho()
    sistema = contexto_sistema(estado)
    try:
        model = genai.GenerativeModel(MODELO, system_instruction=sistema)
        # reconstroi o historico para dar continuidade
        hist = []
        for h in pedido.historico[-10:]:
            hist.append({"role": h.get("role", "user"),
                         "parts": [h.get("text", "")]})
        chat = model.start_chat(history=hist)
        resp = chat.send_message(pedido.mensagem)
        return {"resposta": resp.text, "estado_usado": estado, "ts": int(time.time())}
    except Exception as e:
        return {"resposta": f"Desculpa, nao consigo responder agora ({e}).",
                "erro": str(e), "ts": int(time.time())}

# No teu main.py / api.py:  app.include_router(router)
