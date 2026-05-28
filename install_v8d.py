#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v8d — Hotfix CORS

CAUSA: app/main.py tem allow_origins=[localhost:3000, localhost:5173, localhost:8000]
       — não inclui o frontend de produção em www.plantarockinrio.com.
       Browser bloqueia → "Failed to fetch" nas páginas /v2/cleaning e /v2/incidents.

FIX: adicionar os 3 hostnames de produção à lista de allow_origins no main.py.
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = ":".join([
    "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    "/usr/local/bin", "/opt/homebrew/bin",
    os.environ.get("PATH", ""),
])


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0


def main():
    root = Path.cwd()
    if not (root / "app" / "main.py").exists():
        print("ERRO: corre a partir de ~/planta_rock4")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    main_py = root / "app" / "main.py"

    print("=" * 68)
    print("  HOTFIX CORS · adicionar www.plantarockinrio.com aos allow_origins")
    print("=" * 68)

    # Backup
    bk = main_py.with_suffix(f".py.bak.cors.{stamp}")
    shutil.copy2(main_py, bk)
    print(f"  backup → {bk.name}")

    content = main_py.read_text()

    # Bloco a substituir (vi no grep do utilizador)
    old_block = '''        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
        ],'''

    new_block = '''        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "https://www.plantarockinrio.com",
            "https://plantarockinrio.com",
            "https://plantarockinrio.vercel.app",
        ],
        allow_origin_regex=r"https://planta-rock4-.*\\.vercel\\.app",
        allow_credentials=True,'''

    if "www.plantarockinrio.com" in content:
        print("  ℹ www.plantarockinrio.com já está nos allow_origins · skip")
        sys.exit(0)

    if old_block not in content:
        print("  ⚠ bloco esperado não encontrado · vou tentar alternativa")
        # Tentar com indentação alternativa
        alt_old = '''allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
        ],'''
        if alt_old not in content:
            print("  ERRO: não consigo localizar bloco CORS no main.py")
            sys.exit(1)
        old_block = alt_old
        new_block = new_block.lstrip()

    new_content = content.replace(old_block, new_block, 1)
    main_py.write_text(new_content)
    delta = len(new_content) - len(content)
    print(f"  ✓ allow_origins extendido · delta {delta:+d} bytes")

    # Também actualizar o config.py para coerência (não estritamente necessário)
    cfg = root / "app" / "config.py"
    if cfg.exists():
        cfg_content = cfg.read_text()
        cfg_old = '''cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]'''
        cfg_new = '''cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://www.plantarockinrio.com",
        "https://plantarockinrio.com",
    ]'''
        if cfg_old in cfg_content and "www.plantarockinrio.com" not in cfg_content:
            bk2 = cfg.with_suffix(f".py.bak.cors.{stamp}")
            shutil.copy2(cfg, bk2)
            cfg.write_text(cfg_content.replace(cfg_old, cfg_new, 1))
            print(f"  ✓ app/config.py também actualizado (coerência)")

    # Validar Python
    if not run("python3 -m py_compile app/main.py", cwd=str(root)):
        print("  ERRO: syntax inválida no main.py")
        sys.exit(1)
    print("  ✓ Python OK")

    print()
    print("  GIT COMMIT + PUSH")
    run("git add app/main.py app/config.py 2>/dev/null", cwd=str(root))
    msg = "fix(cors): allow www.plantarockinrio.com origin"
    run(f'git commit -m "{msg}"', cwd=str(root))
    run("git push", cwd=str(root))

    print()
    print("  Aguarda Railway rebuildar (~90s). Depois testa:")
    print()
    print("  sleep 90")
    print("  curl -s -I -H 'Origin: https://www.plantarockinrio.com' \\")
    print("    -X OPTIONS https://api.plantarockinrio.com/api/v1/cleaning/schedule | head -10")
    print()
    print("  Vais ver: access-control-allow-origin: https://www.plantarockinrio.com")
    print("  E o browser /v2/cleaning vai começar a mostrar os 8 cards.")


if __name__ == "__main__":
    main()
