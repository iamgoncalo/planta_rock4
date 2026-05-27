"""
PlantaOS · SCOR history buffer
===============================
Mantém em memória as últimas N publicações do SCOR para visualização live.
Thread-safe (asyncio.Lock). FIFO bounded.

Não persiste — reset em cada restart. Para histórico persistente seria preciso
DB, mas isso aumenta latência. Em memória é suficiente para dashboard live.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any


# Buffer máximo: 1 hora a 10s/publicação = 360 entradas
# 6 horas seriam 2160 — escolho 1000 para ter margem
MAX_HISTORY = 1000


@dataclass
class ScorPublishRecord:
    """Snapshot de uma publicação SCOR."""
    ts: float                    # epoch seconds
    iso: str                     # ISO 8601
    status: int                  # HTTP status (200, 4xx, 5xx, 0=exception)
    duration_ms: int             # tempo da chamada
    kpi_01: int                  # Flow Index 0-100
    kpi_02: float                # Avg WC Occupancy %
    kpi_03: int                  # Active Critical Alerts
    kpi_04: int                  # People Redirected
    cluster_count: int           # quantos clusters reportados neste payload
    error: str | None = None     # se status >= 400 ou exception


class ScorHistory:
    """Buffer thread-safe das últimas N publicações."""

    def __init__(self, max_entries: int = MAX_HISTORY):
        self._buf: deque[ScorPublishRecord] = deque(maxlen=max_entries)
        self._lock = asyncio.Lock()
        self._total_ok = 0
        self._total_err = 0

    async def add(self, record: ScorPublishRecord) -> None:
        async with self._lock:
            self._buf.append(record)
            if 200 <= record.status < 300:
                self._total_ok += 1
            else:
                self._total_err += 1

    async def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Devolve as últimas N entradas, mais recentes primeiro."""
        async with self._lock:
            items = list(self._buf)[-limit:]
        return [asdict(r) for r in reversed(items)]

    async def stats(self) -> dict[str, Any]:
        async with self._lock:
            total = self._total_ok + self._total_err
            success_rate = (self._total_ok / total * 100) if total > 0 else 0.0

            last_5min = []
            now_ts = time.time()
            for r in self._buf:
                if (now_ts - r.ts) <= 300:
                    last_5min.append(r)

            avg_latency = (
                sum(r.duration_ms for r in last_5min) / len(last_5min)
                if last_5min else 0
            )
            return {
                "total_publications": total,
                "ok_count": self._total_ok,
                "error_count": self._total_err,
                "success_rate_pct": round(success_rate, 2),
                "buffered_entries": len(self._buf),
                "last_5min_count": len(last_5min),
                "avg_latency_ms_5min": round(avg_latency, 0),
            }

    async def latest(self) -> dict[str, Any] | None:
        async with self._lock:
            if not self._buf:
                return None
            return asdict(self._buf[-1])


# Singleton — partilhado entre o publisher (escreve) e o router (lê)
scor_history = ScorHistory()
