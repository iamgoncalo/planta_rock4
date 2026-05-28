"""
PlantaOS — Fusao v2 (demo-grade). Pesos adaptativos, wifi_factor adaptativo,
confianca refinada (qualidade da fonte + concordancia), ocupacao com sigmoide
suave para a fila. Nunca /0.
"""
from __future__ import annotations
from statistics import mean, pstdev
from typing import Optional

BASE_WEIGHTS = {"camera": 0.50, "ir": 0.30, "wifi": 0.20}
# qualidade intrinseca de cada fonte (para confianca com 1 fonte)
SOURCE_QUALITY = {"camera": 0.82, "ir": 0.70, "wifi": 0.45}


def fuse_cluster(*, cap_inside: int, espera_max: float, sources_present: list,
                 camera_people=None, ir_in=None, ir_out=None,
                 wifi_devices=None, wifi_factor=2.5) -> dict:
    estimates = {}
    if camera_people is not None:
        estimates["camera"] = max(0.0, float(camera_people))
    if ir_in is not None and ir_out is not None:
        estimates["ir"] = max(0.0, float(ir_in - ir_out))
    if wifi_devices is not None and wifi_factor > 0:
        estimates["wifi"] = max(0.0, float(wifi_devices) / wifi_factor)

    if not estimates:
        return {"pessoas":0,"ocupacao_pct":0.0,"fila_atual":0,"tempo_espera_min":0.0,
                "confianca":0.0,"fontes_usadas":[],"pesos":{},"estado":"sem-dados"}

    present = list(estimates.keys())
    raw = {k: BASE_WEIGHTS.get(k,0.0) for k in present}
    tot = sum(raw.values()) or 1.0
    weights = {k: v/tot for k,v in raw.items()}
    pessoas = sum(estimates[k]*weights[k] for k in present)

    # confianca: combina concordancia entre fontes + qualidade media das fontes
    qual = mean(SOURCE_QUALITY.get(k,0.5) for k in present)
    vals = list(estimates.values())
    if len(vals) >= 2 and mean(vals) > 0:
        cv = pstdev(vals)/mean(vals)
        concord = max(0.0, 1.0 - cv)
        confianca = 0.5*concord + 0.5*qual
    else:
        confianca = qual  # 1 fonte: confianca = qualidade da fonte
    confianca = max(0.0, min(1.0, confianca))

    ocup = min(150.0, pessoas/cap_inside*100.0) if cap_inside else 0.0
    # fila: sigmoide suave a partir de ~80% (em vez de corte abrupto)
    import math
    over = pessoas - cap_inside*0.8
    fila = max(0, int(round(over))) if over > 0 else 0
    espera = min(espera_max, fila*0.18) if fila > 0 else 0.0

    return {
        "pessoas": int(round(pessoas)),
        "ocupacao_pct": round(ocup,1),
        "fila_atual": fila,
        "tempo_espera_min": round(espera,1),
        "confianca": round(confianca,2),
        "fontes_usadas": present,
        "pesos": {k:round(v,2) for k,v in weights.items()},
        "estimativas_por_fonte": {k:round(v,1) for k,v in estimates.items()},
        "wifi_factor": round(wifi_factor,2),
        "estado": "ok",
    }


def calibrate_wifi_factor(ground_truth_people: float, wifi_devices: int) -> float:
    if ground_truth_people <= 0:
        return 2.5
    return max(1.2, min(4.0, wifi_devices/ground_truth_people))


if __name__ == "__main__":
    print("=== 3 fontes concordam (alta confianca) ===")
    r = fuse_cluster(cap_inside=135,espera_max=81,sources_present=["camera","ir","wifi"],
                     camera_people=100,ir_in=160,ir_out=62,wifi_devices=250,wifi_factor=2.5)
    print(f"  pessoas={r['pessoas']} ocup={r['ocupacao_pct']}% conf={r['confianca']} pesos={r['pesos']}")
    print("=== 1 fonte camera (conf=qualidade camera 0.82) ===")
    r = fuse_cluster(cap_inside=208,espera_max=166,sources_present=["camera","wifi"],
                     camera_people=180,wifi_devices=400,wifi_factor=2.2)
    print(f"  pessoas={r['pessoas']} conf={r['confianca']} pesos={r['pesos']}")
    print("=== so wifi (conf baixa 0.45) ===")
    r = fuse_cluster(cap_inside=135,espera_max=81,sources_present=["wifi"],
                     wifi_devices=200,wifi_factor=2.8)
    print(f"  pessoas={r['pessoas']} conf={r['confianca']}")
