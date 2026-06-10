"""
PlantaOS — Motor de alertas. Calcula alertas inteligentes a partir do estado
atual da frota e da fusao. Sem estado interno — chamadas idempotentes. Cada
alerta tem gravidade (crit|warn|info), categoria, mensagem PT-PT, sugestao
acionavel e timestamp. Ordenado por gravidade.
"""
from __future__ import annotations
import time
from statistics import mean, pstdev

GRAV_RANK = {"crit": 0, "warn": 1, "info": 2}

# Limiares (ajustaveis sem mexer no codigo)
BAT_CRIT = 10
BAT_WARN = 20
OCUP_CRIT = 95
OCUP_WARN = 85
FILA_CRIT = 30
FILA_WARN = 15
DISCORD_CV = 0.40   # coeficiente de variacao entre fontes acima disto = discord


def _alert(grav: str, categoria: str, alvo: str, mensagem: str,
           sugerido: str = "", **meta) -> dict:
    return {
        "id": f"{categoria}-{alvo}-{int(time.time())}",
        "gravidade": grav, "categoria": categoria, "alvo": alvo,
        "mensagem": mensagem, "sugerido": sugerido, "ts": time.time(),
        "meta": meta,
    }


def alertas_da_frota(sensors: list) -> list:
    """Alertas ao nivel de sensores."""
    out = []
    # offline
    for s in sensors:
        if s.get("status") == "offline":
            out.append(_alert("crit", "sensor_offline", s["id"],
                f"Sensor {s['id']} offline",
                "verificar gateway do cluster e bateria"))
        elif s.get("status") == "degraded":
            out.append(_alert("warn", "sensor_instavel", s["id"],
                f"Sensor {s['id']} instavel (RSSI {s.get('rssi_dbm','?')}dBm)",
                "verificar ponto de acesso WiFi mais proximo"))
        # bateria
        bat = (s.get("battery") or {}).get("pct")
        if bat is not None:
            if bat <= BAT_CRIT:
                out.append(_alert("crit", "bateria_critica", s["id"],
                    f"Bateria {bat}% em {s['id']}",
                    "substituir powerbank dentro de 30 min"))
            elif bat <= BAT_WARN:
                out.append(_alert("warn", "bateria_baixa", s["id"],
                    f"Bateria {bat}% em {s['id']}",
                    "preparar powerbank de reserva"))
    return out


def alertas_de_cluster(cluster_id: str, fus: dict) -> list:
    """Alertas ao nivel de cluster: ocupacao, fila, discordancia."""
    out = []
    if fus.get("estado") != "ok":
        return out
    ocup = fus.get("ocupacao_pct", 0)
    fila = fus.get("fila_atual", 0)
    espera = fus.get("tempo_espera_min", 0)

    if ocup >= OCUP_CRIT:
        out.append(_alert("crit", "cluster_saturado", cluster_id,
            f"{cluster_id.upper()} a {ocup:.0f}% — saturado",
            "redirecionar fluxo para cluster vizinho"))
    elif ocup >= OCUP_WARN:
        out.append(_alert("warn", "cluster_alta_ocupacao", cluster_id,
            f"{cluster_id.upper()} a {ocup:.0f}%",
            "stewards reforcam orientacao"))

    if fila >= FILA_CRIT:
        out.append(_alert("crit", "fila_longa", cluster_id,
            f"Fila de {fila} pessoas em {cluster_id.upper()} ({espera:.0f}min espera)",
            "abrir cluster overflow proximo"))
    elif fila >= FILA_WARN:
        out.append(_alert("warn", "fila_media", cluster_id,
            f"Fila de {fila} em {cluster_id.upper()} ({espera:.0f}min)",
            "monitorar"))

    # discordancia entre fontes
    ests = fus.get("estimativas_por_fonte", {})
    if len(ests) >= 2:
        vals = list(ests.values())
        m = mean(vals) if vals else 0
        if m > 5:  # ignorar quando ocupacao baixa
            cv = pstdev(vals) / m
            if cv >= DISCORD_CV:
                out.append(_alert("warn", "fontes_discordam", cluster_id,
                    f"{cluster_id.upper()}: fontes discordam (cv={cv:.2f})",
                    f"verificar calibracao: {', '.join(f'{k}={v:.0f}' for k,v in ests.items())}"))
    return out


def deteta_gateway_down(sensors: list) -> list:
    """Se TODOS os IR de um cluster estao offline, o LilyGo gateway caiu."""
    out = []
    by_cluster = {}
    for s in sensors:
        if s.get("tipo") == "ir":
            c = s.get("cluster")
            if c:
                by_cluster.setdefault(c, []).append(s)
    for c, irs in by_cluster.items():
        if irs and all(x.get("status") in ("offline","sem-dados") for x in irs):
            out.append(_alert("crit", "gateway_down", c,
                f"Gateway de {c.upper()} caiu — {len(irs)} IRs sem resposta",
                "verificar LilyGo + powerbank do cluster"))
    return out


def calcular(sensors: list, fusions: dict) -> dict:
    """Devolve {alertas, sumario, ts}. Sumario tem contagens por gravidade."""
    alertas = []
    alertas += alertas_da_frota(sensors)
    alertas += deteta_gateway_down(sensors)
    for cid, fus in (fusions or {}).items():
        if isinstance(fus, dict):
            alertas += alertas_de_cluster(cid, fus)
    alertas.sort(key=lambda a: (GRAV_RANK.get(a["gravidade"], 9), a["alvo"]))
    sumario = {"crit": 0, "warn": 0, "info": 0, "total": len(alertas)}
    for a in alertas:
        sumario[a["gravidade"]] = sumario.get(a["gravidade"], 0) + 1
    return {"alertas": alertas, "sumario": sumario, "ts": time.time()}


if __name__ == "__main__":
    # Teste com cenarios sinteticos
    sensors = [
        {"id":"wc-01-lilygo-1","tipo":"lilygo","cluster":"wc-01","status":"online","battery":{"pct":15}},
        {"id":"wc-02-cam-1","tipo":"camera","cluster":"wc-02","status":"offline","battery":{"pct":8}},
        {"id":"wc-03-ir-m-1","tipo":"ir","cluster":"wc-03","status":"online"},
        {"id":"wc-03-ir-m-2","tipo":"ir","cluster":"wc-03","status":"offline"},
        {"id":"wc-03-ir-m-3","tipo":"ir","cluster":"wc-03","status":"offline"},
        {"id":"wc-03-ir-m-4","tipo":"ir","cluster":"wc-03","status":"offline"},
        {"id":"wc-03-ir-f-1","tipo":"ir","cluster":"wc-03","status":"offline"},
        {"id":"wc-03-ir-f-2","tipo":"ir","cluster":"wc-03","status":"offline"},
        {"id":"wc-03-ir-f-3","tipo":"ir","cluster":"wc-03","status":"offline"},
        {"id":"wc-03-ir-f-4","tipo":"ir","cluster":"wc-03","status":"offline"},
    ]
    fusions = {
        "wc-02": {"estado":"ok","ocupacao_pct":118,"fila_atual":48,"tempo_espera_min":9,
                  "estimativas_por_fonte":{"camera":150,"ir":50,"wifi":140}},
        "wc-06": {"estado":"ok","ocupacao_pct":78,"fila_atual":2,"tempo_espera_min":0.5,
                  "estimativas_por_fonte":{"camera":160,"wifi":155}},
        "wc-05": {"estado":"ok","ocupacao_pct":92,"fila_atual":18,"tempo_espera_min":4,
                  "estimativas_por_fonte":{"camera":120,"wifi":118}},
    }
    r = calcular(sensors, fusions)
    print(f"SUMARIO: {r['sumario']}")
    print()
    for a in r["alertas"]:
        print(f"  [{a['gravidade'].upper():4}] {a['categoria']:>20} · {a['alvo']:<12} · {a['mensagem']}")
        if a['sugerido']: print(f"          → {a['sugerido']}")
