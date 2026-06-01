#!/usr/bin/env python3
"""
CORRECAO: _CLUSTERS_VALIDOS foi inserido ENTRE o decorator e a funcao,
o que parte o arranque (healthcheck falha). Move para sitio seguro.
Idempotente e validado.
"""
import pathlib, sys, ast

P = pathlib.Path.home() / "planta_rock4" / "app" / "routers" / "rirstaff.py"
src = P.read_text()

# 1. Remover a linha mal colocada (entre decorator e funcao)
bad = '@router.get("/rirstaff/config/{cluster}")\n_CLUSTERS_VALIDOS = ("rirstaff-f", "rirstaff-m")\n'
good = '@router.get("/rirstaff/config/{cluster}")\n'

if bad in src:
    src = src.replace(bad, good, 1)
    print("Linha mal colocada removida.")
elif '_CLUSTERS_VALIDOS = ("rirstaff-f", "rirstaff-m")' in src:
    # ja foi removida do sitio mau? verificar se esta nalgum sitio
    print("Linha mal colocada nao encontrada nesse formato exato.")
    # tentar remover qualquer ocorrencia solta entre decorator e funcao
else:
    print("AVISO: nao encontrei o padrao. A abortar para nao estragar.")
    sys.exit(1)

# 2. Garantir que _CLUSTERS_VALIDOS existe num sitio seguro (antes do bloco calibracao)
if '_CLUSTERS_VALIDOS = ("rirstaff-f", "rirstaff-m")' not in src:
    # inserir antes do comentario do bloco de calibracao
    marca = "# CALIBRACAO REMOTA"
    if marca in src:
        src = src.replace(marca, '_CLUSTERS_VALIDOS = ("rirstaff-f", "rirstaff-m")\n# CALIBRACAO REMOTA', 1)
        print("_CLUSTERS_VALIDOS reinserido em sitio seguro.")
    else:
        print("AVISO: nao encontrei sitio para reinserir. A abortar.")
        sys.exit(1)
else:
    print("_CLUSTERS_VALIDOS ja existe noutro sitio (ok).")

# 3. VALIDAR que o ficheiro fica sintaticamente correto (isto apanha o erro de arranque!)
try:
    ast.parse(src)
    print("Sintaxe Python VALIDA (vai arrancar).")
except SyntaxError as e:
    print(f"ERRO de sintaxe apos correcao: {e}. A ABORTAR (nada gravado).")
    sys.exit(1)

P.write_text(src)
print("Correcao aplicada e validada com sucesso.")
