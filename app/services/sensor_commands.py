"""
PlantaOS — Motor de comandos por SENSOR INDIVIDUAL.
Funciona em dois mundos:
  SIM  -> devolve resposta simulada COERENTE com o estado do sensor (online/offline,
          bateria, tipo). Nunca um botao morto.
  REAL -> fala com o MQTT verdadeiro (send_command + espera resposta).

Comandos: ping, diagnostics, restart, reset_counters, calibrate, identify, ota.
Cada sensor individual (lilygo/camera/ir) pode receber comandos.
IR nao tem radio -> o comando vai ao LilyGo pai, resposta inclui leitura do IR.
"""
from __future__ import annotations
import time, hashlib, random


def _h(key: str, t: float, bucket: int = 30) -> float:
    b = int(t // bucket)
    return int(hashlib.md5(f"{key}:{b}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def sim_sensor_state(sensor_id: str, tipo: str, t: float | None = None) -> dict:
    """Estado coerente simulado de um sensor (mesma base que o fleet_sim)."""
    t = t or time.time()
    r = _h(sensor_id, t)
    if r < 0.88: status = "online"
    elif r < 0.96: status = "degraded"
    else: status = "offline"
    # bateria so para powerbank (lilygo/camera)
    bat = None
    if tipo in ("lilygo", "camera"):
        frac_dia = (time.gmtime(t).tm_hour % 24) / 24.0
        bat = max(15, min(100, int(100 - frac_dia*55 - 10*_h(sensor_id+"b", t, 60))))
    uptime_s = int(3600 * 4 + _h(sensor_id+"u", t, 300) * 3600 * 8)  # 4-12h
    rssi = int(-55 - _h(sensor_id+"r", t, 60) * 35)  # -55 a -90 dBm
    return {"status": status, "battery": bat, "uptime_s": uptime_s, "rssi_dbm": rssi}


def _fmt_uptime(s: int) -> str:
    h = s // 3600; m = (s % 3600) // 60
    return f"{h}h {m}m"


def simulate_command(sensor_id: str, tipo: str, cluster: str, cmd: str,
                     value=None, t: float | None = None) -> dict:
    """Resposta SIMULADA coerente com o estado do sensor."""
    t = t or time.time()
    st = sim_sensor_state(sensor_id, tipo, t)
    offline = st["status"] == "offline"

    base = {"sensor_id": sensor_id, "cmd": cmd, "mode": "sim", "ts": t}

    if offline and cmd in ("ping", "diagnostics", "calibrate", "identify"):
        return {**base, "ok": False, "resposta": "sem resposta — sensor offline (timeout 5s)"}

    if cmd == "ping":
        return {**base, "ok": True,
                "resposta": f"pong · uptime {_fmt_uptime(st['uptime_s'])} · RSSI {st['rssi_dbm']}dBm"
                            + (f" · bateria {st['battery']}%" if st['battery'] is not None else "")
                            + " · fw 6.0.0"}

    if cmd == "diagnostics":
        diag = {
            "estado": st["status"],
            "uptime": _fmt_uptime(st["uptime_s"]),
            "rssi_dbm": st["rssi_dbm"],
            "firmware": "6.0.0",
            "heap_livre_kb": int(180 + _h(sensor_id+"heap", t)*60),
            "temperatura_cpu_c": round(38 + _h(sensor_id+"tmp", t)*12, 1),
        }
        if st["battery"] is not None:
            diag["bateria_pct"] = st["battery"]
            diag["tensao_v"] = round(3.3 + st["battery"]/100*0.9, 2)
        if tipo == "lilygo":
            # o LilyGo reporta os IR que le
            diag["ir_ligados"] = 0 if cluster in ("wc-05","wc-06") else 8
            diag["wifi_devices_vistos"] = int(80 + _h(sensor_id+"wd", t)*200)
        if tipo == "camera":
            diag["fps"] = 12
            diag["modelo"] = "OAK 4 D" if cluster == "wc-06" else "OAK-D Lite" if cluster == "wc-04" else "ESP32-CAM"
            diag["pessoas_no_frame"] = int(_h(sensor_id+"ppl", t)*40)
        if tipo == "ir":
            diag["entradas"] = int(_h(sensor_id+"in", t)*200)
            diag["saidas"] = int(_h(sensor_id+"out", t)*180)
            diag["lido_por"] = f"{cluster}-lilygo-1"
        return {**base, "ok": True, "diagnostico": diag}

    if cmd == "restart":
        return {**base, "ok": True, "resposta": f"reinício enviado · {sensor_id} volta em ~3s"}

    if cmd == "reset_counters":
        return {**base, "ok": True, "resposta": "contadores a zero"}

    if cmd == "calibrate":
        # value = pessoas reais contadas
        real = value or 20
        ir_count = int(real * (0.85 + _h(sensor_id+"cal", t)*0.3))
        factor = round(real / max(1, ir_count), 3)
        return {**base, "ok": True,
                "resposta": f"calibrado · {real} pessoas reais / {ir_count} contadas = fator {factor}",
                "factor": factor}

    if cmd == "identify":
        return {**base, "ok": True, "resposta": f"LED a piscar em {sensor_id} por 5s"}

    if cmd == "ota":
        return {**base, "ok": True, "resposta": "OTA iniciado · descarrega fw 6.0.0 · reinicia em ~30s"}

    return {**base, "ok": False, "resposta": f"comando desconhecido: {cmd}"}
