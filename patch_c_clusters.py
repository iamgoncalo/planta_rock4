#!/usr/bin/env python3
"""
PASSO C — Config aceita SO clusters validos (rirstaff-f / rirstaff-m).
Rejeita nomes inventados com 404. Idempotente e seguro (aborta se nao bater).
"""
import pathlib, sys

P = pathlib.Path.home() / "planta_rock4" / "app" / "routers" / "rirstaff.py"
src = P.read_text()

if "_CLUSTERS_VALIDOS" in src:
    print("Passo C ja aplicado. Nada a fazer.")
    sys.exit(0)

# 1. Definir o conjunto de clusters validos (antes do get_config)
anchor = "def rirstaff_get_config(cluster: str):"
if anchor not in src:
    print("AVISO: get_config nao encontrado. Abortado (nada alterado).")
    sys.exit(1)
src = src.replace(
    anchor,
    '_CLUSTERS_VALIDOS = ("rirstaff-f", "rirstaff-m")\n\n' + anchor,
    1
)

# 2. Validar no SET (a parte importante: muda config)
old_set = '''def rirstaff_set_config(cluster: str, upd: _CfgUpd):
    if upd.password != _ADMIN_PASS:
        raise _HTTPException(status_code=401, detail="Password errada")'''
new_set = '''def rirstaff_set_config(cluster: str, upd: _CfgUpd):
    if cluster not in _CLUSTERS_VALIDOS:
        raise _HTTPException(status_code=404, detail="cluster desconhecido")
    if upd.password != _ADMIN_PASS:
        raise _HTTPException(status_code=401, detail="Password errada")'''
if old_set not in src:
    print("AVISO: set_config nao bate certo. Abortado (nada alterado).")
    sys.exit(1)
src = src.replace(old_set, new_set, 1)

P.write_text(src)
print("Passo C aplicado: config so aceita rirstaff-f / rirstaff-m.")
