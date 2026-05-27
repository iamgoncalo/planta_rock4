"""
PlantaOS · WC Units — fonte única de verdade
=============================================
Hard limits oficiais do XLSX RIRLX_limiteocupacaobanheiros.xlsx
14 unidades operacionais:
  - 12 cluster×género (M/F separados em WC-01,02,03,04,07,08)
  - 2 unissex (WC-05, WC-06 — FEM=0 em ambos, capacidade toda em MASC)

Estes números NUNCA mudam. São restrições físicas das casas de banho.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Gender = Literal["M", "F", "U"]  # M=masculino, F=feminino, U=unissex


@dataclass(frozen=True)
class WCUnit:
    """Uma unidade operacional de WC — combinação cluster×género."""
    unit_id: str        # "WC-04_M", "WC-04_F", "WC-05" (unissex sem sufixo)
    cluster_id: str     # "WC-04"
    gender: Gender
    masc: int           # capacidade masc (do XLSX)
    fem: int            # capacidade fem (do XLSX)
    espera: float       # capacidade espera (do XLSX)
    total: float        # capacidade total (do XLSX)
    label: str          # nome legível, ex: "WC-04 Masculino"
    note: str = ""      # nota especial (ex: UNISSEX)


# ════════════════════════════════════════════════════════════════════
# Dados oficiais — copiados literalmente do XLSX
# ════════════════════════════════════════════════════════════════════
WC_UNITS: list[WCUnit] = [
    # WC-01 — M/F separados
    WCUnit("WC-01_M", "WC-01", "M", 72, 0, 0,    72,    "WC-01 Masculino"),
    WCUnit("WC-01_F", "WC-01", "F", 0,  63, 0,   63,    "WC-01 Feminino"),

    # WC-02 — M/F separados (FEMALE-DOMINANT no XLSX)
    WCUnit("WC-02_M", "WC-02", "M", 54, 0, 0,    54,    "WC-02 Masculino"),
    WCUnit("WC-02_F", "WC-02", "F", 0,  72, 0,   72,    "WC-02 Feminino"),

    # WC-03 — M/F separados
    WCUnit("WC-03_M", "WC-03", "M", 54, 0, 0,    54,    "WC-03 Masculino"),
    WCUnit("WC-03_F", "WC-03", "F", 0,  48, 0,   48,    "WC-03 Feminino"),

    # WC-04 — M/F separados
    WCUnit("WC-04_M", "WC-04", "M", 84, 0, 0,    84,    "WC-04 Masculino"),
    WCUnit("WC-04_F", "WC-04", "F", 0,  66, 0,   66,    "WC-04 Feminino"),

    # WC-05 — UNISSEX (FEM=0 no XLSX, toda a capacidade vai em MASC)
    WCUnit("WC-05",   "WC-05", "U", 133, 0, 106.4, 239.4, "WC-05 Unissex", "UNISSEX"),

    # WC-06 — UNISSEX (maior cluster, FEM=0)
    WCUnit("WC-06",   "WC-06", "U", 208, 0, 166.4, 374.4, "WC-06 Unissex", "UNISSEX"),

    # WC-07 — M (masculinos via CALHA URINÓIS) + F
    WCUnit("WC-07_M", "WC-07", "M", 84, 0, 0,    84,    "WC-07 Masculino"),
    WCUnit("WC-07_F", "WC-07", "F", 0,  54, 0,   54,    "WC-07 Feminino"),

    # WC-08 — M/F separados
    WCUnit("WC-08_M", "WC-08", "M", 84, 0, 0,    84,    "WC-08 Masculino"),
    WCUnit("WC-08_F", "WC-08", "F", 0,  61, 0,   61,    "WC-08 Feminino"),
]


# ════════════════════════════════════════════════════════════════════
# Totais oficiais (validados contra o XLSX)
# ════════════════════════════════════════════════════════════════════
TOTAL_MASC = sum(u.masc for u in WC_UNITS)         # 773
TOTAL_FEM = sum(u.fem for u in WC_UNITS)           # 364
TOTAL_ESPERA = sum(u.espera for u in WC_UNITS)     # 882.6
TOTAL_CAPACITY = sum(u.total for u in WC_UNITS)    # 2019.6 (sem espera)


def units_by_cluster(cluster_id: str) -> list[WCUnit]:
    """Devolve unidades de um cluster (1 para unissex, 2 para M/F)."""
    return [u for u in WC_UNITS if u.cluster_id == cluster_id]


def unit_by_id(unit_id: str) -> WCUnit | None:
    """Procura unidade pelo ID."""
    for u in WC_UNITS:
        if u.unit_id == unit_id:
            return u
    return None


def all_unit_ids() -> list[str]:
    return [u.unit_id for u in WC_UNITS]
