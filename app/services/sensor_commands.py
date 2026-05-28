"""
PlantaOS — Motor de comandos por sensor v2. COERENCIA TOTAL: o ping, o diagnostico
e o detalhe usam o MESMO estado (sim_sensor_state do fleet_sim). Mesmo sensor =
mesmos numeros, sempre.
"""
from __future__ import annotations
import time
from app.services.fleet_sim import sim_sensor_state, simulate_cluster_params, CAP


def _fmt_uptime(s: int) -> str:
    return f"{s//3600}h {(s%3600)//60}m"


def simulate_command(sensor_id: str, tipo: str, cluster: str, cmd: str,
                     value=None, t: float | None = None) -> dict:
    t = t or time.time()
    st = sim_sensor_state(sensor_id, tipo, t)
    offline = st["status"] == "offline"
    base = {"sensor_id": sensor_id, "cmd": cmd, "mode": "sim", "ts": t}

    if offline and cmd in ("ping", "diagnostics", "calibrate", "identify"):
        return {**base, "ok": False, "resposta": "sem resposta — sensor offline (timeout 5s)"}

    bat_txt = f" · bateria {st['battery']}%" if st["battery"] is not None else ""

    if cmd == "ping":
        return {**base, "ok": True,
                "resposta": f"pong · uptime {_fmt_uptime(st['uptime_s'])} · RSSI {st['rssi_dbm']}dBm{bat_txt} · fw 6.0.0"}

    if cmd == "diagnostics":
        diag = {
            "estado": st["status"],
            "uptime": _fmt_uptime(st["uptime_s"]),
            "rssi_dbm": st["rssi_dbm"],
            "firmware": "6.0.0",
            "heap_livre_kb": int(180 + (st["uptime_s"] % 60)),
            "temperatura_cpu_c": round(40 + abs(st["rssi_dbm"]) % 10, 1),
        }
        if st["battery"] is not None:
            diag["bateria_pct"] = st["battery"]
            diag["tensao_v"] = round(3.3 + st["battery"]/100*0.9, 2)
        if tipo == "lilygo":
            diag["ir_ligados"] = 0 if cluster in ("wc-05","wc-06") else 8
            p = simulate_cluster_params(cluster, t)
            diag["wifi_devices_vistos"] = p["telemoveis_detectados"]
        if tipo == "camera":
            diag["fps"] = 12
            diag["modelo"] = "OAK 4 D" if cluster == "wc-06" else "OAK-D Lite" if cluster == "wc-04" else "ESP32-CAM"
            p = simulate_cluster_params(cluster, t)
            diag["pessoas_no_frame"] = p["pessoas_estimadas"]
        if tipo == "ir":
            p = simulate_cluster_params(cluster, t)
            diag["entradas"] = p.get("entradas_ir") or 0
            diag["saidas"] = p.get("saidas_ir") or 0
            diag["lido_por"] = f"{cluster}-lilygo-1"
        return {**base, "ok": True, "diagnostico": diag}

    if cmd == "restart":
        return {**base, "ok": True, "resposta": f"reinício enviado · {sensor_id} volta em ~3s"}
    if cmd == "reset_counters":
        return {**base, "ok": True, "resposta": "contadores a zero"}
    if cmd == "calibrate":
        real = value or 20
        p = simulate_cluster_params(cluster, t)
        wf = p.get("_wifi_factor", 2.5)
        ir_count = int(real * (wf / 2.5))
        factor = round(real / max(1, ir_count), 3)
        return {**base, "ok": True,
                "resposta": f"calibrado · {int(real)} reais / {ir_count} detetados = fator {factor} (wifi_factor atual {wf})",
                "factor": factor}
    if cmd == "identify":
        return {**base, "ok": True, "resposta": f"LED a piscar em {sensor_id} por 5s"}
    if cmd == "ota":
        return {**base, "ok": True, "resposta": "OTA iniciado · fw 6.0.0 · reinicia em ~30s"}
    return {**base, "ok": False, "resposta": f"comando desconhecido: {cmd}"}
