"""
PlantaOS — Simulador de frota v2 (demo-grade).
Vida realista: curva por cluster (proximidade ao palco), bateria suave e unica
por sensor, wifi_factor adaptativo a hora, coerencia total (ping=diagnostico).
Tudo determinista por (sensor, janela de tempo) -> estavel entre chamadas proximas
mas vivo ao longo do tempo.
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
    """Hash estavel (nao muda com o tempo) — para 'personalidade' do sensor."""
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def hora_festival(t: float) -> float:
    """Hora decimal de Lisboa (0-24)."""
    g = time.gmtime(t)
    return (g.tm_hour + 1 + g.tm_min/60.0) % 24


def curva_base(t: float) -> float:
    """Enchimento global [0.02..1.0]. Pico 22h."""
    h = hora_festival(t)
    if 2.5 < h < 13.5:
        return 0.02
    hh = h if h >= 13.5 else h + 24
    return max(0.02, min(1.0, math.exp(-((hh - 22.0) ** 2) / (2 * 4.0 ** 2))))


def evento_surto(t: float) -> float:
    """Surto pos-concerto: multiplicador >1 em janelas curtas (fim de show)."""
    h = hora_festival(t)
    # surtos as 23:48 (fim Katy Perry) e 00:06 — picos de 1.3x por ~20min
    for centro in (23.8, 24.1):
        hh = h if h >= 13.5 else h + 24
        if abs(hh - centro) < 0.33:
            return 1.0 + 0.3 * (1 - abs(hh - centro)/0.33)
    return 1.0


def cluster_fill(cluster: str, t: float) -> float:
    """Enchimento de um cluster: curva base modulada por proximidade ao palco."""
    c = CAP[cluster]
    base = curva_base(t)
    # clusters perto do palco enchem mais cedo e mais; longe, menos
    palco = c["palco"]
    prox = 1.0 - min(1.0, (palco - 86) / (461 - 86))  # 1=perto, 0=longe
    fator_prox = 0.7 + 0.5 * prox  # 0.7 a 1.2
    surto = evento_surto(t)
    # ruido temporal suave por cluster
    noise = 0.9 + 0.2 * _h(cluster, t, 8)
    return max(0.0, min(1.15, base * fator_prox * surto * noise))


def wifi_factor_adaptativo(cluster: str, t: float) -> float:
    """Dispositivos por pessoa: sobe quando esta cheio (mais ruido MAC) e a noite."""
    c = CAP[cluster]
    fill = cluster_fill(cluster, t)
    base = 1.8 if c["uni"] else 2.5
    # +0.6 no pico (multidao densa infla MACs), suave
    return round(base + 0.6 * fill, 2)


def simulate_cluster_params(cluster: str, t: float | None = None) -> dict:
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


def sim_sensor_state(sensor_id: str, tipo: str, t: float | None = None) -> dict:
    """Estado coerente e ESTAVEL de um sensor. A 'personalidade' (saude, drain
    de bateria) e fixa; so o tempo a faz evoluir suavemente."""
    t = t or time.time()
    saude = _h_static(sensor_id + "health")  # 0=fragil, 1=robusto
    # estado: sensores frageis falham mais, mas estavel por janelas de 20s
    r = 0.5 * saude + 0.5 * _h(sensor_id, t, 20)
    if r > 0.18: status = "online"
    elif r > 0.08: status = "degraded"
    else: status = "offline"

    bat = None
    if tipo in ("lilygo", "camera"):
        # drenagem unica por sensor + perfil (camara gasta mais)
        drain_rate = (0.35 if tipo == "camera" else 0.10)  # %/h aproximado na demo
        drain_var = 0.8 + 0.4 * _h_static(sensor_id + "drain")
        horas_ligado = hora_festival(t) - 13.0 if hora_festival(t) > 13 else 0
        horas_ligado = max(0, horas_ligado)
        consumido = drain_rate * drain_var * horas_ligado * 10  # escala demo
        bat = max(12, min(100, int(round(100 - consumido))))

    uptime_s = int((hora_festival(t) % 24) * 3600 * 0.5 + _h_static(sensor_id+"up") * 7200)
    rssi = int(-58 - _h_static(sensor_id+"rssi") * 32)  # estavel por sensor
    return {"status": status, "battery": bat, "uptime_s": uptime_s, "rssi_dbm": rssi}


if __name__ == "__main__":
    t = time.time()
    print(f"Hora festival simulada: {hora_festival(t):.1f}h · enchimento base {curva_base(t)*100:.0f}%")
    print("\n=== ENCHIMENTO POR CLUSTER (proximidade ao palco) ===")
    for cid in CAP:
        p = simulate_cluster_params(cid, t)
        cap = CAP[cid]["m"]+CAP[cid]["f"]
        ocup = round(p["pessoas_estimadas"]/cap*100)
        print(f"  {cid} (palco {CAP[cid]['palco']}m): {p['pessoas_estimadas']:>3} pessoas ({ocup:>3}%) · wifi_factor {p['_wifi_factor']}")

    print("\n=== CURVA AO LONGO DO DIA (wc-02, perto do palco) ===")
    for h in [14,17,20,22,23,0,2]:
        tt = time.mktime((2026,6,20,h,0,0,0,0,0)) - 3600
        p = simulate_cluster_params("wc-02", tt)
        print(f"  {h:>2}h: {p['pessoas_estimadas']:>3} pessoas · wifi_factor {p['_wifi_factor']} · fill {p['_fill']}")

    print("\n=== ESTADO DE SENSORES (estavel + bateria unica) ===")
    for sid,tp in [("wc-06-lilygo-1","lilygo"),("wc-06-cam-1","camera"),("wc-04-cam-1","camera"),("wc-01-ir-m-1","ir")]:
        s = sim_sensor_state(sid,tp,t)
        print(f"  {sid}: {s['status']} · bat {s['battery']} · uptime {s['uptime_s']//3600}h · rssi {s['rssi_dbm']}")

    print("\n=== COERÊNCIA: 3 chamadas seguidas dão o mesmo (estável) ===")
    for i in range(3):
        s = sim_sensor_state("wc-06-lilygo-1","lilygo",t)
        print(f"  chamada {i+1}: bat={s['battery']} rssi={s['rssi_dbm']} status={s['status']}")
