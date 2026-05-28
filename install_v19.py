#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_v19 — Footer tagline editorial em vez de FCT grant code

Substitui o texto FCT 2025.00020.AIVLAB.DEUCALION (que era visível no footer
da home /v2) por uma tagline com humor editorial:

  "Someone has to take care of your needs." — Planta

Alternativas comentadas inline para troca rapida:
  - "Holding it in is so 2024."
  - "When nature calls, we answer first."
"""

import os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = ":".join([
    "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    "/usr/local/bin", "/opt/homebrew/bin",
    os.environ.get("PATH", ""),
])


OLD = """        <div className=\"mono\" style={{ fontSize: 10.5, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          FCT 2025.00020.AIVLAB.DEUCALION
        </div>"""

NEW = """        {/* Tagline editorial — alternativas comentadas para troca rapida */}
        {/* "Holding it in is so 2024." */}
        {/* "When nature calls, we answer first." */}
        <div style={{
          fontSize: 'clamp(12px, 1.3vw, 14px)',
          color: 'var(--muted)',
          fontStyle: 'italic',
          letterSpacing: '-0.005em',
          maxWidth: '60ch',
          lineHeight: 1.4,
        }}>
          Someone has to take care of your needs.
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontStyle: 'normal',
            fontSize: '0.78em',
            letterSpacing: '0.12em',
            marginLeft: 10,
            color: 'var(--faint)',
            textTransform: 'uppercase',
          }}>— Planta</span>
        </div>"""


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)


def main():
    root = Path.cwd()
    page = root / "frontend" / "app" / "v2" / "page.tsx"
    if not page.exists():
        print("ERRO: frontend/app/v2/page.tsx nao encontrado")
        sys.exit(1)
    
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    c = page.read_text()
    
    if "FCT 2025.00020.AIVLAB.DEUCALION" not in c:
        if "Someone has to take care" in c:
            print("  i tagline ja aplicada — nada a fazer")
            return
        print("  WARN: nao encontrei o texto FCT no page.tsx")
        print("  Mostra-me as ultimas 30 linhas:")
        print()
        for line in c.splitlines()[-30:]:
            print(f"    {line}")
        sys.exit(1)
    
    shutil.copy2(page, page.with_suffix(f".tsx.bak.v19.{stamp}"))
    
    if OLD in c:
        c = c.replace(OLD, NEW)
        print("  OK substituido bloco completo via match exacto")
    else:
        # Fallback: substituir so o texto interior (frágil)
        c = c.replace(
            "FCT 2025.00020.AIVLAB.DEUCALION",
            "Someone has to take care of your needs.",
            1,
        )
        print("  OK substituido APENAS o texto (fallback)")
        print("  i podes querer ajustar estilo manualmente em page.tsx")
    
    page.write_text(c)
    print(f"  OK page.tsx actualizado ({len(c)} B)")
    
    print()
    run("git add frontend/app/v2/page.tsx", cwd=str(root))
    run('git commit -m "feat(v19): footer tagline editorial — Someone has to take care of your needs"', cwd=str(root))
    run("git push", cwd=str(root))
    
    print()
    print("  Aguarda ~90s, CMD+SHIFT+R e ve o footer da home.")
    print("  Frase agora: \"Someone has to take care of your needs.\"  — Planta")


if __name__ == "__main__":
    main()
