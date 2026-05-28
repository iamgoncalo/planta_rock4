"""
PlantaOS — Simulador de frota. Da vida aos 78 sensores em modo SIMULADO.
A proveniencia dos dados REAIS usa o ingest_store.freshness() que ja existe.
Os dois mundos nunca se misturam: simulado e sempre rotulado; real e carimbado.
"""
from __future__ import annotations
import math, time, hashlib

CAP = {
    "wc-01": {"m":72,"f":63,"esp":81.0,"uni":False},
    "wc-02": {"m":54,"f":72,"esp":100.8,"uni":False},
    "wc-03": {"m":54,"f":48,"esp":81.6,"uni":False},
    "wc-04": {"m":84,"f":66,"esp":120.0,"uni":False},
    "wc-05": {"m":133,"f":0,"esp":106.4,"uni":True},
    "wc-06": {"m":208,"f":0,"esp":166.4,"uni":True},
    "wc-07": {"m":84,"f":54,"esp":110.4,"uni":False},
    "wc-08": {"m":84,"f":61,"esp":116.0,"uni":False},
}


def _curva_festival(t: float) -> float:
    h = (time.gmtime(t).tm_hour + 1) % 24
    if 2 < h < 14:
        return 0.02
    centro, larg = 22.0, 4.0
    hh = h if h >= 14 else h + 24
    return max(0.02, min(1.0, math.exp(-((hh - centro) ** 2) / (2 * larg ** 2))))


def _seed(key: str, t: float, bucket_s: int = 10) -> float:
    b = int(t // bucket_s)
    hh = hashlib.md5(f"{key}:{b}".encode()).hexdigest()
    return int(hh[:8], 16) / 0xFFFFFFFF


def simulate_cluster_params(cluster: str, t: float | None = None) -> dict:
    """Params simulados de um cluster (mesmo formato do /ingest)."""
    t = t or time.time()
    c = CAP[cluster]
    cap_in = c["m"] + c["f"]
    frac = _curva_festival(t)
    pessoas = max(0, min(int(cap_in*1.15), int(round(cap_in*frac*(0.85+0.3*_seed(cluster,t))))))
    ratio = 1.8 if c["uni"] else 2.5
    telemoveis = int(pessoas*ratio*(0.9+0.2*_seed(cluster+"w",t)))
    ir_in = ir_out = None
    if not c["uni"]:
        ir_in = pessoas + int(pessoas*0.6)
        ir_out = int(pessoas*0.6)
    return {
        "pessoas_estimadas": pessoas,
        "telemoveis_detectados": telemoveis,
        "entradas_ir": ir_in,
        "saidas_ir": ir_out,
    }


def simulate_sensor_status(sensor: dict, t: float | None = None) -> tuple[str, int | None]:
    """Estado + bateria simulados de um sensor individual."""
    t = t or time.time()
    sid = sensor["id"]
    r = _seed(sid, t, 30)
    # 88% online, 8% degraded, 4% offline
    if r < 0.88: st = "online"
    elif r < 0.96: st = "degraded"
    else: st = "offline"
    # bateria: powerbank desce ao longo do dia; eletrico/poe nao tem
    bat = None
    prof = sensor.get("power_profile", {})
    if prof.get("battery") == "powerbank":
        # desce de ~100 para ~40 ao longo de 24h, + ruido por sensor
        frac_dia = (time.gmtime(t).tm_hour % 24) / 24.0
        base = 100 - frac_dia*55
        bat = max(15, min(100, int(base - 10*_seed(sid+"b", t, 60))))
    return st, bat


if __name__ == "__main__":
    print("=== params simulados (formato /ingest) ===")
    t = time.time()
    for cid in CAP:
        p = simulate_cluster_params(cid, t)
        print(f"  {cid}: {p}")
    print("\n=== estado+bateria de sensores exemplo ===")
    for s in [
        {"id":"wc-06-lilygo-1","power_profile":{"battery":"powerbank","ma":35}},
        {"id":"wc-06-cam-1","power_profile":{"battery":"powerbank","ma":200}},
        {"id":"wc-01-ir-m-1","power_profile":{"battery":"electric","ma":0}},
    ]:
        st, bat = simulate_sensor_status(s, t)
        print(f"  {s['id']}: estado={st} bateria={bat if bat is not None else 'n/a (eletrico)'}")
