"""
PlantaOS — Perfil do festival. Os 4 dias do Rock in Rio Lisboa 2026 com os
seus headliners, multiplicadores de pressao WC (por genero) e janelas de surto.
"""
from __future__ import annotations
import time

DIAS = {
    "20-06": {
        "data": "20 Jun 2026", "weekday": "Sábado", "tema": "Pop",
        "palco_mundo": "Katy Perry", "palco_pmv": "Alok",
        "support": "Pedro Sampaio · Calema · NAPA · Charlie Puth · Audrey Nuna",
        "genero_pressao": 1.10,      # pop
        "alcool_factor": 1.15,
        "crowd_peak_h": 22.5,
        "show_end_surge_h": 23.8,    # 23:48
        "temp_pico_c": 29,
        "wc_pressure": "ALTA — pop, hidratação alta, surto pós-show",
    },
    "21-06": {
        "data": "21 Jun 2026", "weekday": "Domingo", "tema": "Rock",
        "palco_mundo": "Linkin Park", "palco_pmv": "Tara Perdida",
        "support": "Cypress Hill · Grandson · Kaiser Chiefs · The Pretty Reckless · Hoobastank · Sepultura · P.O.D.",
        "genero_pressao": 1.25,      # rock
        "alcool_factor": 1.35,       # PICO — rock + alcool
        "crowd_peak_h": 23.0,
        "show_end_surge_h": 24.1,    # 00:06
        "temp_pico_c": 30,
        "wc_pressure": "CRITICA — rock × álcool × surto mais tarde",
    },
    "27-06": {
        "data": "27 Jun 2026", "weekday": "Sábado", "tema": "Reggae / Lendas",
        "palco_mundo": "Rod Stewart", "palco_pmv": "The Wailers (50º Rastaman Vibration)",
        "support": "Cyndi Lauper · Joss Stone · Shaggy · 4 Non Blondes · Xutos & Pontapés",
        "genero_pressao": 1.05,      # reggae
        "alcool_factor": 1.20,
        "crowd_peak_h": 22.0,
        "show_end_surge_h": 23.5,
        "temp_pico_c": 28,
        "wc_pressure": "ALTA",
    },
    "28-06": {
        "data": "28 Jun 2026", "weekday": "Domingo", "tema": "Pop / Urban",
        "palco_mundo": "21 Savage", "palco_pmv": "Lola Índigo",
        "support": "Calema · Central Cee · Rema · Matuê · Filipe Ret",
        "genero_pressao": 1.10,
        "alcool_factor": 1.18,
        "crowd_peak_h": 22.8,
        "show_end_surge_h": 23.9,
        "temp_pico_c": 27,
        "wc_pressure": "ALTA",
    },
}

# Marcos horarios genericos (skip_to)
MARCOS = [
    ("14:00", "Portas abrem", "doors"),
    ("17:00", "Pré-pico", "buildup"),
    ("20:00", "Pico de chegada", "peak_arrival"),
    ("22:00", "Headliner começa", "headliner"),
    ("23:48", "Surto pós-concerto", "surge"),
    ("01:00", "Saída em massa", "exit"),
]


def perfil(dia: str = None) -> dict:
    """Devolve perfil completo de um dia ou do mais proximo no tempo."""
    if not dia or dia not in DIAS:
        dia = list(DIAS.keys())[0]
    d = DIAS[dia]
    return {
        "dia": dia, **d,
        "marcos": [{"hora": h, "label": l, "tag": t} for h, l, t in MARCOS],
    }


def todos() -> list:
    return [{"dia": k, **v} for k, v in DIAS.items()]


def pressao_estimada(dia: str, hora_decimal: float) -> dict:
    """Para uma combinacao dia+hora, estima a pressao nos WCs."""
    if dia not in DIAS:
        return {"erro": "dia desconhecido", "disponiveis": list(DIAS.keys())}
    d = DIAS[dia]
    # curva: pico em crowd_peak_h, surto em show_end_surge_h
    import math
    base = math.exp(-((hora_decimal - d["crowd_peak_h"]) ** 2) / (2 * 4.0 ** 2))
    if abs(hora_decimal - d["show_end_surge_h"]) < 0.33:
        base *= 1.3  # surto
    pressao = base * d["genero_pressao"] * d["alcool_factor"]
    nivel = "BAIXA" if pressao < 0.3 else "MEDIA" if pressao < 0.7 else "ALTA" if pressao < 1.1 else "CRITICA"
    return {
        "dia": dia, "hora": hora_decimal,
        "pressao_relativa": round(pressao, 2),
        "nivel": nivel,
        "headliner": d["palco_mundo"],
        "explicacao": f"{d['tema']} · ×{d['genero_pressao']} (género) · ×{d['alcool_factor']} (álcool)",
    }


if __name__ == "__main__":
    print("=== PERFIL DOS 4 DIAS ===\n")
    for k, d in DIAS.items():
        print(f"  {k}: {d['palco_mundo']:<22} · pressao×{d['genero_pressao']} · álcool×{d['alcool_factor']} · {d['wc_pressure']}")

    print("\n=== PRESSAO ESTIMADA 21/6 ao longo do dia ===")
    for h in [14, 17, 20, 22, 23, 23.8, 24.1, 1]:
        r = pressao_estimada("21-06", h)
        print(f"  {h:>5.1f}h: pressao={r['pressao_relativa']:.2f} · {r['nivel']}")
