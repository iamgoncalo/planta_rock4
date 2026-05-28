"""
PlantaOS — Simulador de frota v3 (demo-grade).
v3: thresholds amigaveis (online por defeito), estado coerente e estavel.
"""
from __future__ import annotations
import math, time, hashlib

CAP = {
    "wc-01": {"m":72,"f":63,"esp":81.0,"uni":False,"palco":399},
    "wc-02": {"m":54,"f":72,"esp":100.8,"uni":False,"palco":86},
    "wc-03": {"m":54,"f":48,"esp":81.6,"uni":False,"palco":128},
    "wc-04": {"m":84,"f":66,"esp":120.0,"uni":False,"palco":283},
    "wc-05": {"m":133,"f":0,"esp":106.4,"uni":True,"palco":308},
    "wc-06": {"m":208,"f":0,"esp":166.4,"uni":True,"palco":255},
    "wc-07": {"m":84,"f":54,"esp":110.4,"uni":False,"palco":310},
    "wc-08": {"m":84,"f":61,"esp":116.0,"uni":False,"palco":461},
}

def _h(key: str, t: float, bucket: int = 10) -> float:
    b = int(t // bucket)
    return int(hashlib.md5(f"{key}:{b}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF

def _h_static(key: str) -> float:
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def hora_festival(t: float) -> float:
    g = time.gmtime(t)
    return (g.tm_hour + 1 + g.tm_min/60.0) % 24


def curva_base(t: float) -> float:
    h = hora_festival(t)
    if 2.5 < h < 13.5:
        return 0.05
    hh = h if h >= 13.5 else h + 24
    return max(0.05, min(1.0, math.exp(-((hh - 22.0) ** 2) / (2 * 4.0 ** 2))))


def evento_surto(t: float) -> float:
    h = hora_festival(t)
    for centro in (23.8, 24.1):
        hh = h if h >= 13.5 else h + 24
        if abs(hh - centro) < 0.33:
            return 1.0 + 0.3 * (1 - abs(hh - centro)/0.33)
    return 1.0


def cluster_fill(cluster: str, t: float) -> float:
    c = CAP[cluster]
    base = curva_base(t)
    palco = c["palco"]
    prox = 1.0 - min(1.0, (palco - 86) / (461 - 86))
    fator_prox = 0.7 + 0.5 * prox
    surto = evento_surto(t)
    noise = 0.9 + 0.2 * _h(cluster, t, 8)
    return max(0.0, min(1.15, base * fator_prox * surto * noise))


def wifi_factor_adaptativo(cluster: str, t: float) -> float:
    c = CAP[cluster]
    fill = cluster_fill(cluster, t)
    base = 1.8 if c["uni"] else 2.5
    return round(base + 0.6 * fill, 2)


def simulate_cluster_params(cluster: str, t=None) -> dict:
    t = t or time.time()
    c = CAP[cluster]
    cap_in = c["m"] + c["f"]
    fill = cluster_fill(cluster, t)
    pessoas = int(round(cap_in * fill))
    wf = wifi_factor_adaptativo(cluster, t)
    telemoveis = int(pessoas * wf)
    ir_in = ir_out = None
    if not c["uni"]:
        ir_in = pessoas + int(pessoas * 0.6)
        ir_out = int(pessoas * 0.6)
    return {
        "pessoas_estimadas": pessoas,
        "telemoveis_detectados": telemoveis,
        "entradas_ir": ir_in,
        "saidas_ir": ir_out,
        "_wifi_factor": wf,
        "_fill": round(fill, 3),
    }


def sim_sensor_state(sensor_id: str, tipo: str, t=None) -> dict:
    """Estado coerente e ESTAVEL. v3: thresholds amigaveis (100% online tipico).
    'health' nunca penaliza muito — so 1-2% degraded em casos extremos."""
    t = t or time.time()
    saude = _h_static(sensor_id + "health")
    r = 0.5 * saude + 0.5 * _h(sensor_id, t, 20)
    # demo-grade: quase tudo online; raros degraded; nada offline em sim
    if r > 0.04: status = "online"
    elif r > 0.01: status = "degraded"
    else: status = "online"  # fallback: nunca offline em sim para nao quebrar a demo

    # bateria: SEMPRE em lilygo e camera; estavel; demo entre 65-98%
    bat = None
    if tipo in ("lilygo", "camera"):
        base = 88 if tipo == "lilygo" else 78
        var = int(_h_static(sensor_id + "bat") * 15)  # 0-15
        # leve descida ao longo do dia (max -8 pp do almoco a noite)
        h = hora_festival(t)
        drift = int(max(0, (h - 14) * 0.6)) if 14 <= h <= 27 else 0
        bat = max(45, min(98, base + var - drift))

    uptime_s = int((hora_festival(t) % 24) * 3600 * 0.4 + _h_static(sensor_id+"up") * 7200)
    rssi = int(-58 - _h_static(sensor_id+"rssi") * 32)
    return {"status": status, "battery": bat, "uptime_s": uptime_s, "rssi_dbm": rssi}


if __name__ == "__main__":
    t = time.time()
    print(f"Hora festival: {hora_festival(t):.1f}h · enchimento base {curva_base(t)*100:.0f}%\n")
    # Testar TODOS os 78 sensores
    sensores = []
    for c in CAP:
        sensores.append((f"{c}-lilygo-1","lilygo"))
        if c in ("wc-06",): sensores.append((f"{c}-lilygo-2","lilygo"))
        if c == "wc-04": sensores.append((f"{c}-cam-1","camera"))
        if c == "wc-06": sensores.append((f"{c}-cam-1","camera"))
        if not CAP[c]["uni"]:
            for g in ["m","f"]:
                for n in range(1,5):
                    sensores.append((f"{c}-ir-{g}-{n}","ir"))
    n_on=n_deg=0; n_bat=0; bat_total=0
    for sid,tp in sensores:
        s = sim_sensor_state(sid,tp,t)
        if s["status"]=="online": n_on+=1
        elif s["status"]=="degraded": n_deg+=1
        if s["battery"] is not None:
            n_bat+=1; bat_total+=s["battery"]
    print(f"total: {len(sensores)} · online={n_on} ({100*n_on//len(sensores)}%) · degraded={n_deg}")
    print(f"com bateria: {n_bat} · media {bat_total//n_bat}%")
