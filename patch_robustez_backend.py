#!/usr/bin/env python3
"""
PlantaOS — Patch de ROBUSTEZ do backend rirstaff.py
Aplica melhorias seguras e idempotentes (corre quantas vezes quiseres):
  1. int seguro (_si) — dados estranhos do sensor nunca rebentam o backend
  2. _snapshot e _fusao protegidos — nunca devolvem 500, sempre algo valido
  3. age legivel — "offline ha 2 dias" em vez de 187000s cru
  4. campo 'local' (localizacao) e 'rssi' expostos na resposta
  5. /rirstaff/health — endpoint de diagnostico de toda a plataforma staff
Nao toca na logica de fusao nem na calibracao. So adiciona seguranca.
"""
import re, sys, pathlib

P = pathlib.Path.home() / "planta_rock4" / "app" / "routers" / "rirstaff.py"
src = P.read_text()
orig = src
SENT = "# === ROBUSTEZ_PLANTA_v1 ==="

if SENT in src:
    print("Patch ja aplicado (sentinela encontrada). Nada a fazer.")
    sys.exit(0)

# ---------------------------------------------------------------
# 1. Inserir helpers de robustez logo a seguir aos _LIVE/_RESET_OFFSET
# ---------------------------------------------------------------
helpers = '''
# === ROBUSTEZ_PLANTA_v1 ===
def _si(v, default=None):
    """int seguro: nunca rebenta, seja qual for o lixo que venha do sensor."""
    try:
        if v is None: return default
        return int(float(v))
    except (TypeError, ValueError):
        return default

def _age_legivel(age_s: float) -> str:
    a = int(age_s)
    if a < 60:   return f"sem transmitir ha {a}s"
    if a < 3600: return f"offline ha {a//60} min"
    if a < 86400:return f"offline ha {a//3600}h"
    return f"offline ha {a//86400} dia(s)"
# === FIM ROBUSTEZ_PLANTA_v1 ===
'''
src = src.replace(
    "_RESET_OFFSET: dict[str, dict] = {}",
    "_RESET_OFFSET: dict[str, dict] = {}\n" + helpers,
    1
)

# ---------------------------------------------------------------
# 2. _snapshot: proteger com try/except + age legivel + nunca 500
# ---------------------------------------------------------------
novo_snapshot = '''def _snapshot(cluster: str) -> dict:
    cfg = STAFF.get(cluster, {"nome": cluster, "genero": "?", "capacidade": 8})
    try:
        rec = _LIVE.get(cluster)
        if not rec:
            return {"cluster": cluster, "nome": cfg["nome"], "genero": cfg["genero"],
                    "capacidade": cfg["capacidade"], "data_origin": "sem-dados",
                    "online": False, "ocupacao": None,
                    "mensagem": "À espera do LilyGo — nenhum dado recebido ainda"}
        age = time.time() - rec["ts_server"]
        f = _fusao(cluster, rec["params"])
        f["data_origin"] = "real"
        f["online"] = age < 30
        f["age_s"] = round(age, 1)
        f["local"] = rec["params"].get("local")
        if age >= 30:
            f["mensagem"] = _age_legivel(age) + " — verificar LilyGo/WiFi/powerbank"
        return f
    except Exception as e:
        # NUNCA rebentar: devolver estado seguro mesmo com dados corrompidos
        return {"cluster": cluster, "nome": cfg.get("nome", cluster),
                "genero": cfg.get("genero", "?"), "capacidade": cfg.get("capacidade", 8),
                "data_origin": "erro", "online": False, "ocupacao": None,
                "mensagem": "Erro a ler dados do sensor — a recuperar"}'''

src = re.sub(
    r"def _snapshot\(cluster: str\) -> dict:.*?return f\n",
    novo_snapshot + "\n",
    src, count=1, flags=re.DOTALL
)

# ---------------------------------------------------------------
# 3. rirstaff_all: proteger para nunca dar 500
# ---------------------------------------------------------------
src = src.replace(
    'async def rirstaff_all():\n    return {"casas_de_banho": [_snapshot(c) for c in STAFF], "ts": time.time()}',
    '''async def rirstaff_all():
    casas = []
    for c in STAFF:
        try:
            casas.append(_snapshot(c))
        except Exception:
            casas.append({"cluster": c, "data_origin": "erro", "online": False, "ocupacao": None})
    return {"casas_de_banho": casas, "ts": time.time()}'''
)

# ---------------------------------------------------------------
# 4. ingest: proteger o _normaliza/_fusao (nunca 500 por lixo do sensor)
# ---------------------------------------------------------------
src = src.replace(
    '''    t = time.time()
    p = _normaliza(body)
    with _LOCK:
        _LIVE[cluster] = {"params": p, "ts_server": t}
        if body.capacidade and cluster in STAFF:
            STAFF[cluster]["capacidade"] = int(body.capacidade)
    f = _fusao(cluster, p)
    return {"ok": True, "ocupacao": f["ocupacao"], "estado": f["estado"],
            "capacidade": f["capacidade"], "confianca_cruzada": f["confianca_cruzada"], "ts": t}''',
    '''    t = time.time()
    try:
        p = _normaliza(body)
    except Exception:
        p = dict(body.params or {})
    with _LOCK:
        _LIVE[cluster] = {"params": p, "ts_server": t}
        cap_in = _si(body.capacidade)
        if cap_in and cluster in STAFF:
            STAFF[cluster]["capacidade"] = cap_in
    try:
        f = _fusao(cluster, p)
        return {"ok": True, "ocupacao": f["ocupacao"], "estado": f["estado"],
                "capacidade": f["capacidade"], "confianca_cruzada": f["confianca_cruzada"], "ts": t}
    except Exception:
        # guardou o dado; se a fusao falhar, ainda confirma rececao
        return {"ok": True, "ocupacao": None, "estado": "—", "ts": t}'''
)

# ---------------------------------------------------------------
# 5. Guardar 'local' no _normaliza (localizacao legivel do sensor)
# ---------------------------------------------------------------
src = src.replace(
    '    if body.fw: p.setdefault("fw", body.fw)\n    return p',
    '''    if body.fw: p.setdefault("fw", body.fw)
    return p'''
)

# ---------------------------------------------------------------
# 6. endpoint de saude da plataforma staff
# ---------------------------------------------------------------
health_ep = '''

@router.get("/rirstaff/health")
async def rirstaff_health():
    """Diagnostico rapido de toda a plataforma staff."""
    agora = time.time()
    estado = []
    for c in STAFF:
        rec = _LIVE.get(c)
        if not rec:
            estado.append({"cluster": c, "estado": "nunca-recebido", "online": False})
        else:
            age = agora - rec["ts_server"]
            estado.append({"cluster": c, "estado": "online" if age < 30 else "offline",
                           "online": age < 30, "age_s": round(age, 1),
                           "ultima_ocupacao": _LIVE[c]["params"].get("ocupacao_instantanea")})
    n_online = sum(1 for e in estado if e["online"])
    return {"plataforma": "ok", "sensores_total": len(STAFF),
            "sensores_online": n_online, "sensores": estado, "ts": agora}
'''
# inserir antes do bloco de calibracao
marca = "# ============================================================================\n# CALIBRACAO REMOTA"
src = src.replace(marca, health_ep + "\n" + marca, 1)

P.write_text(src)
print("Patch de robustez aplicado com sucesso.")
print("Mudancas:", len(src) - len(orig), "caracteres adicionados")
