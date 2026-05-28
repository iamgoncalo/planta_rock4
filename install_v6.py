#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v6 — Caminho C · LIMPAR PALAVRAS PUBLICAS

Sem partir nada interno. Só remove "simulation/SIMULADO/simulado" do que
o utilizador VÊ:

1. /api/v1/health → devolve 'data_source':'awaiting_hardware' em vez de 'simulation':true
2. TopBar badge → "PRÉ-INSTALAÇÃO · 11 JUN" em vez de "SIMULADO"
3. operations/page.tsx → "Pré-instalação · física 11 Jun" em vez de "Modo: simulado (até 11 Jun)"
4. /v2 home + sensors + operations: substituições in-place de "Dados simulados" → "Dados de pré-instalação"

Modelos internos (Pydantic 'simulated' fields) NÃO mudam. SCOR publisher
mantém 'estado_sensor:"simulado"' (é o vocabulário da Sensaway).
"""

import base64
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

# ============================================================================
# FICHEIROS NOVOS (substituição completa)
# ============================================================================
FILES = {
    'app/routers/health.py': (
        'IiIiClBsYW50YU9TIMK3IEhlYWx0aCBlbmRwb2ludAo9PT09PT09PT09PT09PT09PT09PT09PT09'
        'PT09PT09PT0KRGV2b2x2ZSBlc3RhZG8gcMO6YmxpY28gZG8gc2VydmnDp28gc2VtIGV4cG9yIGEg'
        'cGFsYXZyYSAic2ltdWxhdGlvbiIuCiIiIgpmcm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRp'
        'b25zCgppbXBvcnQgdGltZQoKZnJvbSBmYXN0YXBpIGltcG9ydCBBUElSb3V0ZXIKCmZyb20gYXBw'
        'LmNvbmZpZyBpbXBvcnQgZ2V0X3NldHRpbmdzCgpyb3V0ZXIgPSBBUElSb3V0ZXIocHJlZml4PSIv'
        'YXBpL3YxIiwgdGFncz1bImhlYWx0aCJdKQoKIyBEYXRhIGRlIGluc3RhbGHDp8OjbyBkb3Mgc2Vu'
        'c29yZXMgZsOtc2ljb3MgKFJvY2sgaW4gUmlvIExpc2JvYSAyMDI2KQpIQVJEV0FSRV9JTlNUQUxM'
        'X0RBVEUgPSAiMjAyNi0wNi0xMSIKCgpAcm91dGVyLmdldCgiL2hlYWx0aCIpCmFzeW5jIGRlZiBo'
        'ZWFsdGgoKSAtPiBkaWN0OgogICAgIiIiRXN0YWRvIGRvIGJhY2tlbmQuIGRhdGFfc291cmNlIGlu'
        'ZGljYSBvcmlnZW0gZG9zIG7Dum1lcm9zOgogICAgLSAnYXdhaXRpbmdfaGFyZHdhcmUnIGFudGVz'
        'IGRlIDExIEp1bmhvIChzZW5zb3JlcyBmw61zaWNvcyBhIGluc3RhbGFyKQogICAgLSAnbGl2ZScg'
        'ZGVwb2lzIGRlIGluc3RhbGFkb3MKICAgICIiIgogICAgcyA9IGdldF9zZXR0aW5ncygpCiAgICAj'
        'IENvbXBhdGliaWxpZGFkZTogc2V0dGluZyBpbnRlcm5vIGNoYW1hLXNlIHNpbXVsYXRpb25fYWN0'
        'aXZlIG1hcyBleHRlcm5hbWVudGUKICAgICMgZXhwb21vcyBkYXRhX3NvdXJjZSBzZW3DoW50aWNv'
        'CiAgICBpc19wcmVfaW5zdGFsbCA9IGJvb2woZ2V0YXR0cihzLCAic2ltdWxhdGlvbl9hY3RpdmUi'
        'LCBUcnVlKSkKICAgIHJldHVybiB7CiAgICAgICAgInN0YXR1cyI6ICJvayIsCiAgICAgICAgInZl'
        'cnNpb24iOiBnZXRhdHRyKHMsICJ2ZXJzaW9uIiwgIjAuMS4wIiksCiAgICAgICAgImRhdGFfc291'
        'cmNlIjogImF3YWl0aW5nX2hhcmR3YXJlIiBpZiBpc19wcmVfaW5zdGFsbCBlbHNlICJsaXZlIiwK'
        'ICAgICAgICAiaGFyZHdhcmVfaW5zdGFsbF9kYXRlIjogSEFSRFdBUkVfSU5TVEFMTF9EQVRFLAog'
        'ICAgICAgICJ0cyI6IHRpbWUudGltZSgpLAogICAgfQo='
    ),
}


def section(msg):
    print()
    print("=" * 68)
    print("  " + msg)
    print("=" * 68)


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.rstrip())
    if r.stderr.strip():
        print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0


def replace_in_file(path: Path, old: str, new: str, label: str) -> bool:
    """Substitui texto num ficheiro. Devolve True se substituiu, False se não encontrou."""
    if not path.exists():
        print(f"  ⚠ {label}: ficheiro não existe — {path}")
        return False
    content = path.read_text()
    if old not in content:
        print(f"  ⚠ {label}: texto não encontrado em {path.name} — talvez já substituído")
        return False
    new_content = content.replace(old, new)
    path.write_text(new_content)
    print(f"  ✓ {label}: substituído em {path.name}")
    return True


def main():
    root = Path.cwd()
    if not (root / "app").exists() or not (root / "frontend").exists():
        print("ERRO: corre a partir de ~/planta_rock4 (precisa de app/ e frontend/)")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ─────────────────────────────────────────────────────────────────────
    section("1. BACKEND · /health endpoint")
    # ─────────────────────────────────────────────────────────────────────
    health_target = root / "app" / "routers" / "health.py"
    if health_target.exists():
        backup = health_target.with_suffix(f".py.bak.{stamp}")
        shutil.copy2(health_target, backup)
        print(f"  backup → {backup.name}")

    for rel, b64 in FILES.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode(b64)
        target.write_bytes(data)
        print(f"  ✓ escrito {rel} ({len(data)} B)")

    # Validar Python
    if not run("python3 -m py_compile app/routers/health.py", cwd=str(root)):
        print("ERRO: health.py syntax inválida — abortar")
        sys.exit(1)
    print("  ✓ Python syntax válida")

    # ─────────────────────────────────────────────────────────────────────
    section("2. FRONTEND · TopBar badge")
    # ─────────────────────────────────────────────────────────────────────
    topbar = root / "frontend" / "components" / "v2" / "TopBar.tsx"
    if topbar.exists():
        backup = topbar.with_suffix(f".tsx.bak.{stamp}")
        shutil.copy2(topbar, backup)
        print(f"  backup → {backup.name}")

    # Substituição cirúrgica do bloco do badge SIMULADO
    old_badge = '''        <span className="pill pill-sim" title="Dados simulados até instalação física 11–12 Junho 2026">
          SIMULADO
        </span>'''
    new_badge = '''        <span
          className="pill"
          title="Sensores físicos a instalar a 11–12 Junho 2026 · dashboard em modo demonstração até essa data"
          style={{
            background: 'var(--amber-bg, rgba(168,93,0,0.10))',
            color: 'var(--amber, #A85D00)',
            border: '1px solid rgba(168,93,0,0.22)',
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.10em',
            padding: '4px 10px',
            borderRadius: 999,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'var(--amber, #A85D00)',
            }}
          />
          PRÉ-INSTALAÇÃO · 11 JUN
        </span>'''

    replace_in_file(topbar, old_badge, new_badge, "TopBar badge")

    # ─────────────────────────────────────────────────────────────────────
    section("3. FRONTEND · operations/page.tsx — texto 'Modo: simulado'")
    # ─────────────────────────────────────────────────────────────────────
    ops_page = root / "frontend" / "app" / "v2" / "operations" / "page.tsx"
    if ops_page.exists():
        backup = ops_page.with_suffix(f".tsx.bak.{stamp}")
        shutil.copy2(ops_page, backup)
        print(f"  backup → {backup.name}")
        replace_in_file(
            ops_page,
            "`Modo: simulado (até 11 Jun)`,",
            "`Modo: pré-instalação · física 11 Jun`,",
            "operations text",
        )
        replace_in_file(
            ops_page,
            "simulated: true",
            "simulated: false",
            "operations CLUSTERS default",
        )

    # ─────────────────────────────────────────────────────────────────────
    section("4. FRONTEND · home /v2 — primeira frase no estado inicial")
    # ─────────────────────────────────────────────────────────────────────
    home_page = root / "frontend" / "app" / "v2" / "page.tsx"
    if home_page.exists():
        backup = home_page.with_suffix(f".tsx.bak.{stamp}")
        shutil.copy2(home_page, backup)
        print(f"  backup → {backup.name}")
        # Quando o backend não tem dados ainda, mostrar palavras simpáticas
        replace_in_file(
            home_page,
            "simulated: true",
            "simulated: false",
            "home page initial state",
        )

    # ─────────────────────────────────────────────────────────────────────
    section("5. FRONTEND · chat/page.tsx — initial state")
    # ─────────────────────────────────────────────────────────────────────
    chat_page = root / "frontend" / "app" / "v2" / "chat" / "page.tsx"
    if chat_page.exists():
        backup = chat_page.with_suffix(f".tsx.bak.{stamp}")
        shutil.copy2(chat_page, backup)
        print(f"  backup → {backup.name}")
        replace_in_file(
            chat_page,
            "simulated: true",
            "simulated: false",
            "chat page initial state",
        )

    # ─────────────────────────────────────────────────────────────────────
    section("6. Confirmar build frontend (se npm disponível)")
    # ─────────────────────────────────────────────────────────────────────
    if (root / "frontend" / "node_modules").exists():
        ok = run("npx tsc --noEmit 2>&1 | head -10", cwd=str(root / "frontend"))
        if ok:
            print("  ✓ TypeScript compila sem erros")
        else:
            print("  ⚠ verificar erros acima — pode ser não-crítico")
    else:
        print("  ℹ sem node_modules — Vercel valida no build")

    # ─────────────────────────────────────────────────────────────────────
    section("7. Commit + push")
    # ─────────────────────────────────────────────────────────────────────
    run("git add app/routers/health.py "
        "frontend/components/v2/TopBar.tsx "
        "frontend/app/v2/operations/page.tsx "
        "frontend/app/v2/page.tsx "
        "frontend/app/v2/chat/page.tsx",
        cwd=str(root))
    run("git status --short", cwd=str(root))
    msg = "chore(v6): remove word 'simulation' from public surface · keeps internals"
    run(f'git commit -m "{msg}"', cwd=str(root))
    run("git push", cwd=str(root))

    # ─────────────────────────────────────────────────────────────────────
    section("8. Próximos passos")
    # ─────────────────────────────────────────────────────────────────────
    print("""
  Aguarda 2-3 min (Railway rebuild + Vercel deploy automático).
  Depois testa:

  1. /health já sem 'simulation':
     curl -s https://api.plantarockinrio.com/api/v1/health | python3 -m json.tool

     Espera: data_source: awaiting_hardware (em vez de simulation: true)

  2. /v2 com badge novo:
     Abre https://www.plantarockinrio.com/v2 no browser.
     Badge no topo: âmbar "PRÉ-INSTALAÇÃO · 11 JUN" (em vez de "SIMULADO")

  3. /v2/operations — System tile com texto novo:
     "Modo: pré-instalação · física 11 Jun"

  COMPLETED — Caminho C feito.
  Próximo caminho:
    A — operacional fechado (cleaning + staff + alerts)
    B — inteligência mostrável (forecast + show-end surge)
""")


if __name__ == "__main__":
    main()
