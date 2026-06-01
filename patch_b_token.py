#!/usr/bin/env python3
"""
PASSO B — Token opcional no ingest (impede dados falsos).
SEGURO: se RIRSTAFF_INGEST_TOKEN nao estiver definido, aceita tudo como hoje.
So quando defines a variavel no Railway e que passa a exigir o token.
Idempotente: corre as vezes que quiseres.
"""
import pathlib, sys

P = pathlib.Path.home() / "planta_rock4" / "app" / "routers" / "rirstaff.py"
src = P.read_text()

if "RIRSTAFF_INGEST_TOKEN" in src:
    print("Passo B ja aplicado. Nada a fazer.")
    sys.exit(0)

# 1. Garantir 'Header' importado
old_imp = "from fastapi import APIRouter, Query, HTTPException"
new_imp = "from fastapi import APIRouter, Query, HTTPException, Header"
if old_imp in src:
    src = src.replace(old_imp, new_imp, 1)
elif "Header" not in src:
    print("AVISO: linha de import nao encontrada como esperado. A abortar por seguranca.")
    sys.exit(1)

# 2. Substituir a assinatura e adicionar verificacao do token
old_sig = '''@router.post("/ingest_staff/{cluster}")
async def ingest(cluster: str, body: IngestIn):
    cluster = (cluster or body.cluster_id or body.cluster or "").lower()'''

new_sig = '''@router.post("/ingest_staff/{cluster}")
async def ingest(cluster: str, body: IngestIn, x_sensor_token: str | None = Header(default=None)):
    import os as _os_tok
    _tok = _os_tok.getenv("RIRSTAFF_INGEST_TOKEN")
    if _tok and x_sensor_token != _tok:
        raise HTTPException(401, "token invalido")
    cluster = (cluster or body.cluster_id or body.cluster or "").lower()'''

if old_sig not in src:
    print("AVISO: assinatura do ingest nao bate certo. A abortar por seguranca (nada alterado).")
    sys.exit(1)

src = src.replace(old_sig, new_sig, 1)
P.write_text(src)
print("Passo B aplicado: token OPCIONAL no ingest.")
print("Enquanto RIRSTAFF_INGEST_TOKEN nao existir no Railway, aceita tudo (nada muda).")
