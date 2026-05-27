"""
PlantaOS · SCOR publisher v9 — instrumented
============================================
Wrapper que reescreve as chamadas do scor_publisher para também escrever
no scor_history buffer (in-memory) para observability.

Esta NÃO substitui o publisher original — apenas adiciona instrumentação.
O install_v9 vai patchar 2 sítios no scor_publisher.py:
  - antes do POST: capturar t0
  - depois do POST (sucesso ou erro): registar no buffer
"""
# Snippet a inserir no scor_publisher.py após o "import" inicial:
INSTRUMENT_IMPORT = """from app.services.scor_history import scor_history, ScorPublishRecord
"""

# Snippet a inserir antes do `r = await client.post(...)`:
INSTRUMENT_BEFORE = """        _scor_t0 = time.time()"""

# Snippet a inserir após a chamada do POST (sucesso 2xx):
INSTRUMENT_AFTER_OK = """            _scor_dt_ms = int((time.time() - _scor_t0) * 1000)
            try:
                await scor_history.add(ScorPublishRecord(
                    ts=time.time(),
                    iso=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                    status=r.status_code,
                    duration_ms=_scor_dt_ms,
                    kpi_01=payload.get("kpi_01", 0),
                    kpi_02=payload.get("kpi_02", 0.0),
                    kpi_03=payload.get("kpi_03", 0),
                    kpi_04=payload.get("kpi_04", 0),
                    cluster_count=len(payload.get("clusters", [])) if isinstance(payload.get("clusters"), list) else 8,
                ))
            except Exception:
                pass"""

# Snippet a inserir após erro (status != 2xx):
INSTRUMENT_AFTER_ERR = """        try:
            await scor_history.add(ScorPublishRecord(
                ts=time.time(),
                iso=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                status=r.status_code,
                duration_ms=int((time.time() - _scor_t0) * 1000),
                kpi_01=payload.get("kpi_01", 0),
                kpi_02=payload.get("kpi_02", 0.0),
                kpi_03=payload.get("kpi_03", 0),
                kpi_04=payload.get("kpi_04", 0),
                cluster_count=8,
                error=f"http {r.status_code}",
            ))
        except Exception:
            pass"""
