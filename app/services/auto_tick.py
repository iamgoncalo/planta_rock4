"""
Auto-tick — avança o simulador em background.

Chama state.advance_tick(scenario) a cada AUTO_TICK_INTERVAL_S segundos
(default 10s). Isto faz com que /api/v1/state devolva valores que mudam
ao longo do tempo, sem precisar de um cliente chamar /simulate/tick.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone


def _log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


async def auto_tick_loop() -> None:
    interval_s = int(os.getenv("AUTO_TICK_INTERVAL_S", "10"))
    scenario = os.getenv("AUTO_TICK_SCENARIO", "normal")
    _log(f"auto_tick.STARTED interval_s={interval_s} scenario={scenario}")

    # Pequeno delay para deixar a app estabilizar
    await asyncio.sleep(3)

    try:
        from app.services.state import advance_tick
    except Exception as e:
        _log(f"auto_tick.ABORT cannot_import_advance_tick {type(e).__name__}: {e}")
        return

    ticks = 0
    while True:
        try:
            advance_tick(scenario)
            ticks += 1
            if ticks % 30 == 0:  # log a cada 30 ticks (~5min)
                _log(f"auto_tick.STATS ticks={ticks} scenario={scenario}")
        except asyncio.CancelledError:
            _log("auto_tick.STOPPED")
            break
        except Exception as e:
            _log(f"auto_tick.error {type(e).__name__}: {e}")

        try:
            await asyncio.sleep(interval_s)
        except asyncio.CancelledError:
            _log("auto_tick.STOPPED")
            break
