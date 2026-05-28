#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v11b — Micro-fix: nome da marca correcto

Substitui no TopBar:
    "planta" / "smart homes"   (minúsculas, estilo lowercase)
        ↓
    "Planta Smart Homes"        (uma linha, proper noun)
"""
import os
import re
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
    tb = root / "frontend" / "components" / "v2" / "TopBar.tsx"
    if not tb.exists():
        print("ERRO: TopBar.tsx não encontrado")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(tb, tb.with_suffix(f".tsx.bak.v11b.{stamp}"))

    content = tb.read_text()
    original = content

    # Substituir bloco com 2 spans (planta + smart homes) por 1 span único
    new_brand_block = """          <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.05 }}>
            <span
              className="serif"
              style={{
                fontSize: 16,
                fontWeight: 600,
                color: 'var(--ink)',
                letterSpacing: '-0.01em',
                whiteSpace: 'nowrap',
              }}
            >
              Planta Smart Homes
            </span>
          </div>"""

    # Match flexivel do bloco antigo (2 spans)
    pattern = re.compile(
        r'<div style=\{\{ display: \'flex\', flexDirection: \'column\'.*?\}\}>\s*'
        r'<span[^>]*>\s*planta\s*</span>\s*'
        r'<span[^>]*>\s*smart homes\s*</span>\s*'
        r'</div>',
        re.DOTALL,
    )
    content = pattern.sub(new_brand_block, content)

    if content == original:
        # Fallback: replace simples
        if ">planta<" in content or ">planta<\n" in content:
            content = content.replace(">\n              planta\n            </span>", ">\n              Planta Smart Homes\n            </span>", 1)
            # Remover o "smart homes" span
            content = re.sub(
                r'\s*<span[^>]*>\s*smart homes\s*</span>',
                '',
                content,
                count=1,
            )

    if content == original:
        print("  WARN: não foi possível encontrar o padrão. Faço replace literal.")
        content = content.replace("planta", "Planta Smart Homes", 1)
        # Remover linha smart homes
        content = re.sub(r'\n.*smart homes.*\n', '\n', content, count=1)

    tb.write_text(content)
    print(f"  OK TopBar.tsx actualizado · delta {len(content)-len(original):+d} bytes")

    # Mostrar primeiras 60 linhas para confirmar
    print("\n  Conteúdo relevante:")
    for ln in content.splitlines()[20:60]:
        if "Planta" in ln or "smart" in ln or "planta" in ln:
            print(f"    > {ln}")

    print()
    print("  GIT COMMIT + PUSH")
    run("git add frontend/components/v2/TopBar.tsx", cwd=str(root))
    run('git commit -m "fix(brand): Planta Smart Homes (proper name)"', cwd=str(root))
    run("git push", cwd=str(root))

    print()
    print("  Aguarda 1min e CMD+SHIFT+R na app.")


if __name__ == "__main__":
    main()
