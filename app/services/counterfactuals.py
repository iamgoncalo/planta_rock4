"""
PlantaOS — Motor de CONTRAFACTUAIS. Responde a "e se?" sem mexer no estado real.
Cada cenario devolve {atual, simulado, delta, recomendacao}. Util para a demo:
mostra que o sistema sabe pensar em cenarios e nao so reportar.
"""
from __future__ import annotations
import time
from app.services import fleet_sim
from app.services import fusion as fusion_engine

# Mapa cluster -> fontes (igual ao router)
CLUSTER_SOURCES = {
    "wc-01": ["camera","ir","wifi"], "wc-02": ["camera","ir","wifi"],
    "wc-03": ["camera","ir","wifi"], "wc-04": ["camera","ir","wifi"],
    "wc-05": ["camera","wifi"],      "wc-06": ["camera","wifi"],
    "wc-07": ["camera","ir","wifi"], "wc-08": ["camera","ir","wifi"],
}


def _fusao_simulada(cluster_id: str, t: float, **overrides) -> dict:
    """Calcula fusao para cluster com parametros opcionalmente sobrepostos."""
    cap = fleet_sim.CAP[cluster_id]
    cap_in = cap["m"] + cap["f"]
    srcs = overrides.get("sources_present") or CLUSTER_SOURCES.get(cluster_id, ["camera","ir","wifi"])
    p = fleet_sim.simulate_cluster_params(cluster_id, t)
    args = {
        "cap_inside": cap_in, "espera_max": cap["esp"], "sources_present": srcs,
        "camera_people": p.get("pessoas_estimadas") if "camera" in srcs else None,
        "ir_in": p.get("entradas_ir") if "ir" in srcs else None,
        "ir_out": p.get("saidas_ir") if "ir" in srcs else None,
        "wifi_devices": p.get("telemoveis_detectados") if "wifi" in srcs else None,
        "wifi_factor": p.get("_wifi_factor", 2.5),
    }
    args.update({k: v for k, v in overrides.items() if k in args})
    r = fusion_engine.fuse_cluster(**args)
    r["cluster_id"] = cluster_id
    r["capacidade_dentro"] = cap_in
    return r


def _delta(atual: dict, sim: dict) -> dict:
    """Calcula diferenças chave entre dois estados."""
    return {
        "pessoas": sim.get("pessoas",0) - atual.get("pessoas",0),
        "ocupacao_pct": round(sim.get("ocupacao_pct",0) - atual.get("ocupacao_pct",0), 1),
        "fila_atual": sim.get("fila_atual",0) - atual.get("fila_atual",0),
        "tempo_espera_min": round(sim.get("tempo_espera_min",0) - atual.get("tempo_espera_min",0), 1),
        "confianca": round(sim.get("confianca",0) - atual.get("confianca",0), 2),
    }


# ─── CENARIOS ────────────────────────────────────────────────────────────

def disable_source(cluster_id: str, fonte: str) -> dict:
    """E se desligarmos a {fonte} no {cluster}?"""
    t = time.time()
    atual = _fusao_simulada(cluster_id, t)
    srcs = [s for s in CLUSTER_SOURCES.get(cluster_id, []) if s != fonte]
    if not srcs:
        return {"erro": "ficaria sem fontes"}
    sim = _fusao_simulada(cluster_id, t, sources_present=srcs)
    d = _delta(atual, sim)
    rec = ""
    if abs(d["pessoas"]) < 5 and d["confianca"] > -0.15:
        rec = f"Seguro desligar {fonte} — fusao mantem-se confiavel."
    elif d["confianca"] < -0.20:
        rec = f"Nao desligar {fonte} — confianca cai {abs(d['confianca'])*100:.0f}pp. Reparar primeiro."
    else:
        rec = f"Aceitavel desligar {fonte} brevemente, mas restaurar quanto antes."
    return {"cenario": f"disable_source:{fonte}", "cluster": cluster_id,
            "atual": atual, "simulado": sim, "delta": d, "recomendacao": rec}


def close_cluster(cluster_id: str) -> dict:
    """E se fecharmos este cluster? Para onde vai o fluxo?"""
    t = time.time()
    atual = _fusao_simulada(cluster_id, t)
    # vizinhos por proximidade ao palco (heuristica: cluster mais perto e nao saturado)
    vizinhos = sorted(
        [c for c in fleet_sim.CAP if c != cluster_id],
        key=lambda c: abs(fleet_sim.CAP[c]["palco"] - fleet_sim.CAP[cluster_id]["palco"])
    )[:3]
    # 60% do fluxo vai para o 1o vizinho, 25% para o 2o, 15% para o 3o
    pessoas = atual.get("pessoas", 0)
    redirect = []
    for i, c in enumerate(vizinhos):
        peso = [0.60, 0.25, 0.15][i]
        sim_v = _fusao_simulada(c, t)
        cap = sim_v.get("capacidade_dentro", 1)
        novo = sim_v.get("pessoas", 0) + int(pessoas * peso)
        novo_ocup = round(novo / cap * 100, 1) if cap else 0
        redirect.append({"cluster": c, "absorve_pessoas": int(pessoas * peso),
                         "novo_total": novo, "nova_ocupacao_pct": novo_ocup,
                         "satura": novo_ocup > 100})
    saturadores = [r["cluster"] for r in redirect if r["satura"]]
    rec = "Vizinhos absorvem sem saturar." if not saturadores \
        else f"Fechar este cluster faz saturar: {', '.join(saturadores)}. Evitar."
    return {"cenario": "close_cluster", "cluster": cluster_id,
            "atual": atual, "redireciona_para": redirect, "recomendacao": rec}


def surge_concert(cluster_id: str, multiplicador: float = 1.6) -> dict:
    """E se houver um surto pos-concerto agora? (multiplica entradas IR)"""
    t = time.time()
    atual = _fusao_simulada(cluster_id, t)
    p = fleet_sim.simulate_cluster_params(cluster_id, t)
    # multiplica pessoas estimadas
    sim = _fusao_simulada(cluster_id, t,
        camera_people=int((p.get("pessoas_estimadas") or 0) * multiplicador),
        ir_in=int((p.get("entradas_ir") or 0) * multiplicador) if p.get("entradas_ir") else None,
        wifi_devices=int((p.get("telemoveis_detectados") or 0) * multiplicador))
    d = _delta(atual, sim)
    if sim.get("ocupacao_pct", 0) > 120:
        rec = f"SURTO crítico: {sim.get('pessoas',0)} pessoas, fila {sim.get('fila_atual',0)}. Abrir overflow."
    elif sim.get("ocupacao_pct", 0) > 95:
        rec = "Saturação iminente. Stewards reforçam, abrir vizinhos."
    else:
        rec = "Cluster absorve sem stress."
    return {"cenario": f"surge_concert:{multiplicador}x", "cluster": cluster_id,
            "atual": atual, "simulado": sim, "delta": d, "recomendacao": rec}


def rain(cluster_id: str, permanencia_extra: float = 0.40) -> dict:
    """E se chover? Pessoas ficam +40% tempo dentro."""
    t = time.time()
    atual = _fusao_simulada(cluster_id, t)
    p = fleet_sim.simulate_cluster_params(cluster_id, t)
    pessoas_extra = int((p.get("pessoas_estimadas") or 0) * permanencia_extra)
    sim = _fusao_simulada(cluster_id, t,
        camera_people=(p.get("pessoas_estimadas") or 0) + pessoas_extra,
        wifi_devices=int(((p.get("telemoveis_detectados") or 0)) * (1+permanencia_extra)))
    d = _delta(atual, sim)
    rec = f"Chuva aumenta permanencia +{int(permanencia_extra*100)}%. "
    rec += "Stewards orientam, abrir cobertos." if sim.get("ocupacao_pct",0) > 90 else "Cluster gere."
    return {"cenario": f"rain:+{int(permanencia_extra*100)}%", "cluster": cluster_id,
            "atual": atual, "simulado": sim, "delta": d, "recomendacao": rec}


def gateway_down(cluster_id: str) -> dict:
    """E se o LilyGo cair? Perdem-se IR — fusão fica sem essa fonte."""
    t = time.time()
    atual = _fusao_simulada(cluster_id, t)
    srcs = [s for s in CLUSTER_SOURCES.get(cluster_id, []) if s != "ir"]
    sim = _fusao_simulada(cluster_id, t, sources_present=srcs) if "ir" in CLUSTER_SOURCES.get(cluster_id, []) else atual
    d = _delta(atual, sim) if sim != atual else {}
    if "ir" not in CLUSTER_SOURCES.get(cluster_id, []):
        rec = "Este cluster nao tem IR — gateway down nao afeta a fusao das fontes restantes."
    else:
        rec = f"Sem IR, confianca cai {abs(d.get('confianca',0))*100:.0f}pp. Substituir powerbank do LilyGo URGENTE."
    return {"cenario": "gateway_down", "cluster": cluster_id,
            "atual": atual, "simulado": sim, "delta": d, "recomendacao": rec}


CENARIOS = {
    "disable_source": disable_source,
    "close_cluster": close_cluster,
    "surge_concert": surge_concert,
    "rain": rain,
    "gateway_down": gateway_down,
}


def aplicar(cluster_id: str, cenario: str, **params) -> dict:
    if cenario not in CENARIOS:
        return {"erro": f"cenario desconhecido: {cenario}",
                "disponiveis": list(CENARIOS.keys())}
    fn = CENARIOS[cenario]
    try:
        return fn(cluster_id, **params)
    except TypeError:
        return fn(cluster_id)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, "/tmp/t58")
    print("=== CONTRAFACTUAIS ===\n")

    for cid, ce, kw in [
        ("wc-06", "disable_source", {"fonte":"camera"}),
        ("wc-05", "close_cluster", {}),
        ("wc-02", "surge_concert", {"multiplicador": 1.6}),
        ("wc-04", "rain", {}),
        ("wc-03", "gateway_down", {}),
    ]:
        print(f"[{ce}] em {cid}: {kw}")
        r = aplicar(cid, ce, **kw)
        if "atual" in r:
            print(f"  atual: {r['atual'].get('pessoas',0)} pessoas, ocup={r['atual'].get('ocupacao_pct',0)}%")
            if "simulado" in r:
                print(f"  simulado: {r['simulado'].get('pessoas',0)} pessoas, ocup={r['simulado'].get('ocupacao_pct',0)}%")
            if "delta" in r and r["delta"]:
                d = r["delta"]
                print(f"  delta: pessoas {d.get('pessoas',0):+d}, ocup {d.get('ocupacao_pct',0):+.1f}pp, conf {d.get('confianca',0):+.2f}")
            if "redireciona_para" in r:
                for rd in r["redireciona_para"]:
                    flag = " (SATURA!)" if rd["satura"] else ""
                    print(f"  → {rd['cluster']}: +{rd['absorve_pessoas']} pessoas, nova ocup {rd['nova_ocupacao_pct']}%{flag}")
        print(f"  RECOMENDA: {r.get('recomendacao','')}\n")
