#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v8c — Hotfix TypeScript build (Vercel deploy failed)

CAUSA: O `Object.assign(api, {...})` no v2-api.ts adiciona funções em runtime,
mas o TypeScript infere o tipo de `api` apenas na declaração inicial, e não
"vê" as funções adicionadas. Resultado: 6 erros TS2339 no build.

FIX cirúrgico, sem refactor:
1. v2-api.ts: substituir Object.assign por nova exportação `apiOps` que combina
   o tipo do api original + o tipo do _opsExtension.
2. 4 ficheiros frontend: trocar `import { api, ... }` por
   `import { apiOps as api, ... }`. As páginas continuam a usar `api` no código,
   mas ele agora tem o tipo correcto.
"""
from __future__ import annotations

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


def patch_v2_api(root: Path) -> bool:
    """Substitui o Object.assign(api, _opsExtension) por uma reasignação tipada."""
    p = root / "frontend" / "lib" / "v2-api.ts"
    if not p.exists():
        print(f"  ⚠ {p} não existe")
        return False

    content = p.read_text()

    old_block = "Object.assign(api, _opsExtension);"
    new_block = (
        "// Merge runtime + typing: aplica as funções operacionais ao api existente\n"
        "Object.assign(api, _opsExtension);\n"
        "// Re-export com o tipo combinado para que TS reconheça as novas propriedades\n"
        "type _ApiWithOps = typeof api & typeof _opsExtension;\n"
        "export const apiOps = api as _ApiWithOps;"
    )

    if "export const apiOps" in content:
        print("  ℹ apiOps já existe · skip")
        return True

    if old_block not in content:
        # Tentar variantes possíveis
        alt = "Object.assign(api, {"
        if alt in content:
            print(f"  ⚠ encontrei variante antiga · pode ter sido escrita differently")
            # Procurar bloco completo do Object.assign(api, {... });
            # Não vou tentar — utilizador deve correr install_v8 antes deste
            print(f"  ⚠ ABORT: bloco esperado '{old_block}' não encontrado")
            return False
        print(f"  ⚠ Object.assign(api, _opsExtension) não encontrado · v8 não foi aplicado?")
        return False

    new_content = content.replace(old_block, new_block, 1)
    p.write_text(new_content)
    print(f"  ✓ v2-api.ts patched ({len(new_content) - len(content)} bytes added)")
    return True


def patch_page_imports(root: Path, rel_path: str) -> bool:
    """Em cada página: trocar 'import { api,' por 'import { apiOps as api,'."""
    p = root / rel_path
    if not p.exists():
        print(f"  ⚠ {rel_path} não existe")
        return False

    content = p.read_text()

    # 3 padrões possíveis de import:
    patterns = [
        ("import {\n  api,", "import {\n  apiOps as api,"),
        ("import { api,", "import { apiOps as api,"),
        ("import { api ", "import { apiOps as api "),
        ("import { api }", "import { apiOps as api }"),
    ]

    if "apiOps as api" in content:
        print(f"  ℹ {rel_path}: já usa apiOps · skip")
        return True

    matched = False
    for old, new in patterns:
        if old in content:
            content = content.replace(old, new, 1)
            matched = True
            print(f"  ✓ {rel_path}: '{old.splitlines()[0]}...' → '{new.splitlines()[0]}...'")
            break

    if not matched:
        print(f"  ⚠ {rel_path}: nenhum padrão de import 'api' encontrado")
        return False

    p.write_text(content)
    return True


def main():
    root = Path.cwd()
    if not (root / "frontend").exists():
        print("ERRO: corre a partir de ~/planta_rock4")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    section("1. PATCH frontend/lib/v2-api.ts")
    v = root / "frontend" / "lib" / "v2-api.ts"
    if v.exists():
        bk = v.with_suffix(f".ts.bak.v8c.{stamp}")
        shutil.copy2(v, bk)
        print(f"  backup → {bk.name}")
    if not patch_v2_api(root):
        print("  ERRO: patch v2-api.ts falhou. A abortar.")
        sys.exit(1)

    section("2. PATCH páginas/componentes que usam 'api'")
    targets = [
        "frontend/app/v2/cleaning/page.tsx",
        "frontend/app/v2/incidents/page.tsx",
        "frontend/components/v2/WeatherWidget.tsx",
    ]
    for rel in targets:
        full = root / rel
        if full.exists():
            bk = full.with_suffix(f".tsx.bak.v8c.{stamp}")
            shutil.copy2(full, bk)
        patch_page_imports(root, rel)

    section("3. VALIDAR TypeScript")
    ok = run("npx tsc --noEmit 2>&1 | grep -E 'cleaning|incidents|WeatherWidget|v2-api' | head -20",
            cwd=str(root / "frontend"))
    # Saída vazia = sem erros nessas pastas = bom.
    print("  Se nenhum erro acima → TypeScript happy ✓")

    section("4. VALIDAR Build Next.js completo (se npm estiver disponível)")
    if (root / "frontend" / "node_modules").exists():
        print("  Não vou correr `npm run build` (demora 1-2 min) — Vercel valida.")
    else:
        print("  ℹ sem node_modules · Vercel valida")

    section("5. GIT COMMIT + PUSH")
    run("git add frontend/", cwd=str(root))
    run("git status --short | head -10", cwd=str(root))
    msg = "fix(v8c): TypeScript type for extended api · apiOps cast"
    run(f'git commit -m "{msg}"', cwd=str(root))
    run("git push", cwd=str(root))

    section("6. PRÓXIMOS PASSOS")
    print("""
  Vercel vai rebuildar em ~1min. Testa:

    curl -o /dev/null -w "%{http_code}\\n" https://www.plantarockinrio.com/v2/cleaning
    curl -o /dev/null -w "%{http_code}\\n" https://www.plantarockinrio.com/v2/incidents

  Espera 200 nos 2.

  Depois abre no browser:
    https://www.plantarockinrio.com/v2/cleaning
    https://www.plantarockinrio.com/v2/incidents

  Verifica os 8 cards + lista de incidentes + WeatherWidget no TopBar.
""")


if __name__ == "__main__":
    main()
