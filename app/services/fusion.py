"""
PlantaOS — Fusao inteligente de sensores. Estima pessoas/ocupacao/fluxo por cluster
cruzando ate 3 fontes (camara, IR, WiFi) com pesos ADAPTATIVOS.

Inteligencia:
  1. Pesos base por fonte; redistribuidos se uma fonte falha (nunca /0).
  2. Camara e a fonte preferida (conta cabecas + H/M); IR refina direcao;
     WiFi (LilyGo) e o fallback sempre presente mas ruidoso.
  3. Fator dispositivos->pessoas do WiFi CALIBRADO pelo ground-truth (camara/IR).
  4. Confianca por concordancia entre fontes (coef. variacao).
  5. Ocupacao = pessoas / capacidade_dentro (limites oficiais).
"""
from __future__ import annotations
from statistics import mean, pstdev
from typing import Optional

# Pesos base por fonte (somam 1.0 quando todas presentes)
BASE_WEIGHTS = {"camera": 0.50, "ir": 0.30, "wifi": 0.20}


def fuse_cluster(
    *,
    cap_inside: int,
    espera_max: float,
    sources_present: list[str],
    camera_people: Optional[float] = None,
    ir_in: Optional[int] = None,
    ir_out: Optional[int] = None,
    wifi_devices: Optional[int] = None,
    wifi_factor: float = 2.5,
) -> dict:
    """
    Funde as fontes disponiveis num unico estado. Cada fonte e opcional.
    Retorna pessoas, ocupacao_pct, fila, espera_min, confianca, e o detalhe.
    """
    estimates: dict[str, float] = {}

    # Camara: contagem direta de pessoas (preferida)
    if camera_people is not None:
        estimates["camera"] = max(0.0, float(camera_people))

    # IR: ocupacao = entradas - saidas (direcional)
    if ir_in is not None and ir_out is not None:
        estimates["ir"] = max(0.0, float(ir_in - ir_out))

    # WiFi: dispositivos / fator dispositivos-por-pessoa
    if wifi_devices is not None and wifi_factor > 0:
        estimates["wifi"] = max(0.0, float(wifi_devices) / wifi_factor)

    if not estimates:
        return {
            "pessoas": 0, "ocupacao_pct": 0.0, "fila_atual": 0,
            "tempo_espera_min": 0.0, "confianca": 0.0,
            "fontes_usadas": [], "pesos": {}, "estado": "sem-dados",
        }

    # Pesos adaptativos: so as fontes presentes, renormalizadas
    present = list(estimates.keys())
    raw = {k: BASE_WEIGHTS.get(k, 0.0) for k in present}
    total_w = sum(raw.values()) or 1.0
    weights = {k: v / total_w for k, v in raw.items()}

    # Estimativa fundida (media ponderada)
    pessoas = sum(estimates[k] * weights[k] for k in present)

    # Confianca por concordancia: 1 - coef.variacao entre fontes
    vals = list(estimates.values())
    if len(vals) >= 2 and mean(vals) > 0:
        cv = pstdev(vals) / mean(vals)
        confianca = max(0.0, min(1.0, 1.0 - cv))
    elif len(vals) == 1:
        # 1 so fonte: confianca depende da fonte (camara>ir>wifi)
        only = present[0]
        confianca = {"camera": 0.75, "ir": 0.65, "wifi": 0.40}.get(only, 0.4)
    else:
        confianca = 0.0

    # Ocupacao, fila, espera (a partir dos limites oficiais)
    ocup_pct = min(100.0, max(0.0, pessoas / cap_inside * 100.0)) if cap_inside else 0.0
    # Fila comeca acima de 80% da capacidade
    fila = max(0, int(round(pessoas - cap_inside * 0.8)))
    # Espera proporcional, limitada ao maximo oficial
    espera = min(espera_max, fila * 0.15) if fila > 0 else 0.0

    return {
        "pessoas": int(round(pessoas)),
        "ocupacao_pct": round(ocup_pct, 1),
        "fila_atual": fila,
        "tempo_espera_min": round(espera, 1),
        "confianca": round(confianca, 2),
        "fontes_usadas": present,
        "pesos": {k: round(v, 2) for k, v in weights.items()},
        "estimativas_por_fonte": {k: round(v, 1) for k, v in estimates.items()},
        "estado": "ok",
    }


def calibrate_wifi_factor(ground_truth_people: float, wifi_devices: int) -> float:
    """Calibra o fator dispositivos->pessoas usando ground-truth (camara/IR)."""
    if ground_truth_people <= 0:
        return 2.5  # default
    factor = wifi_devices / ground_truth_people
    return max(1.2, min(4.0, factor))  # limites sensatos


# ─── TESTES ───
if __name__ == "__main__":
    print("=== TESTE 1: 3 fontes presentes (camara+ir+wifi), concordam ===")
    r = fuse_cluster(cap_inside=208, espera_max=166.4, sources_present=["camera","ir","wifi"],
                     camera_people=150, ir_in=160, ir_out=12, wifi_devices=380, wifi_factor=2.5)
    print(f"  pessoas={r['pessoas']} ocup={r['ocupacao_pct']}% fila={r['fila_atual']} "
          f"conf={r['confianca']} pesos={r['pesos']}")
    print(f"  estimativas: {r['estimativas_por_fonte']}")

    print("\n=== TESTE 2: camara FALHA, so ir+wifi (pesos redistribuem) ===")
    r = fuse_cluster(cap_inside=208, espera_max=166.4, sources_present=["ir","wifi"],
                     ir_in=160, ir_out=12, wifi_devices=380, wifi_factor=2.5)
    print(f"  pessoas={r['pessoas']} ocup={r['ocupacao_pct']}% pesos={r['pesos']} (camara fora)")

    print("\n=== TESTE 3: SO WiFi (cluster minimo, so LilyGo) ===")
    r = fuse_cluster(cap_inside=135, espera_max=81, sources_present=["wifi"],
                     wifi_devices=200, wifi_factor=2.5)
    print(f"  pessoas={r['pessoas']} ocup={r['ocupacao_pct']}% conf={r['confianca']} "
          f"(so wifi, confianca baixa)")

    print("\n=== TESTE 4: unissex wc-06, camara+wifi (sem IR) ===")
    r = fuse_cluster(cap_inside=208, espera_max=166.4, sources_present=["camera","wifi"],
                     camera_people=180, wifi_devices=400, wifi_factor=1.8)
    print(f"  pessoas={r['pessoas']} ocup={r['ocupacao_pct']}% pesos={r['pesos']}")

    print("\n=== TESTE 5: calibracao do fator WiFi ===")
    f = calibrate_wifi_factor(ground_truth_people=150, wifi_devices=380)
    print(f"  150 pessoas reais, 380 dispositivos -> fator calibrado = {f:.2f}")
    print(f"  (antes 2.5 default; agora aprende que ha {f:.1f} dispositivos/pessoa)")

    print("\n=== TESTE 6: divisao por zero / sem dados ===")
    r = fuse_cluster(cap_inside=135, espera_max=81, sources_present=[])
    print(f"  estado={r['estado']} pessoas={r['pessoas']} (nunca rebenta)")
