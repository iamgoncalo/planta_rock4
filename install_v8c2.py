#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v8c2 — Hotfix TypeScript build (versao corrigida)

A versão v8c procurava "Object.assign(api, _opsExtension)" mas o ficheiro
tem o objecto INLINE: "Object.assign(api, { cleaningSchedule: ... })".

Esta versão patcha o ficheiro REAL.

Fix:
1. v2-api.ts: extrai o objecto inline para const + adiciona export apiOps tipado
2. 3 ficheiros frontend: troca "api," por "apiOps as api," nos imports
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


def section(msg):
    print()
    print("=" * 68)
    print("  " + msg)
    print("=" * 68)


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0


def patch_v2_api(root: Path) -> bool:
    """Reescreve a parte final do v2-api.ts (do Object.assign até fim) com versão tipada."""
    p = root / "frontend" / "lib" / "v2-api.ts"
    if not p.exists():
        print(f"  ⚠ {p} nao existe")
        return False

    content = p.read_text()

    if "export const apiOps" in content:
        print("  i apiOps ja existe · skip")
        return True

    # Localizar o "Object.assign(api, {"
    start_marker = "Object.assign(api, {"
    idx = content.find(start_marker)
    if idx == -1:
        print(f"  ⚠ '{start_marker}' nao encontrado")
        return False

    # Encontrar o "});" que fecha esse Object.assign — match de chavetas
    # O objecto é literal, precisamos do "})" seguido de ";"
    pos = idx + len("Object.assign(api, ")
    depth = 0
    end_pos = -1
    for i in range(pos, len(content)):
        c = content[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                # Esperamos: }) seguido eventualmente de ;
                # Procura o ); a seguir
                rest = content[i+1:i+10]
                m = re.match(r'\s*\)\s*;', rest)
                if m:
                    end_pos = i + 1 + m.end()
                    break
                else:
                    end_pos = i + 1
                    break

    if end_pos == -1:
        print("  ⚠ nao consegui encontrar fim do Object.assign")
        return False

    block_before = content[:idx]
    block_after = content[end_pos:]
    inline_block = content[idx:end_pos]
    print(f"  detectado bloco Object.assign · {len(inline_block)} chars")

    # Extrair o conteudo do objecto (entre o "{" inicial e o "}" final)
    inner_start = inline_block.find('{') + 1
    inner_end = inline_block.rfind('}')
    inner_obj = inline_block[inner_start:inner_end]

    # Construir nova versão tipada
    new_block = (
        "const _opsExtension = {"
        + inner_obj
        + "};\n\n"
        "// Aplica em runtime\n"
        "Object.assign(api, _opsExtension);\n\n"
        "// Tipagem combinada para o TypeScript reconhecer os novos metodos\n"
        "type _ApiWithOps = typeof api & typeof _opsExtension;\n"
        "export const apiOps = api as _ApiWithOps;\n"
    )

    new_content = block_before + new_block + block_after
    p.write_text(new_content)
    delta = len(new_content) - len(content)
    print(f"  ✓ v2-api.ts reescrito · delta {delta:+d} bytes")
    return True


def patch_page_imports(root: Path, rel_path: str) -> bool:
    """Em cada página: trocar 'api' por 'apiOps as api' no import."""
    p = root / rel_path
    if not p.exists():
        print(f"  ⚠ {rel_path} nao existe")
        return False

    content = p.read_text()

    if "apiOps as api" in content:
        print(f"  i {rel_path}: ja usa apiOps · skip")
        return True

    # Regex que apanha import { ... api ... } from '@/lib/v2-api'
    pattern = re.compile(
        r"import\s*\{([^}]*?)\}\s*from\s*['\"]@/lib/v2-api['\"]",
        re.DOTALL,
    )

    m = pattern.search(content)
    if not m:
        print(f"  ⚠ {rel_path}: import nao encontrado")
        return False

    imports_inner = m.group(1)
    # Trocar 'api,' por 'apiOps as api,' ou 'api ' por 'apiOps as api '
    # Cuidado: deve apanhar apenas o token 'api' isolado, nao 'apiCenas'
    new_imports_inner = re.sub(
        r"(^|[\s,])api(\s*,|\s*$|\s+as\s)",
        lambda mm: mm.group(1) + "apiOps as api" + mm.group(2),
        imports_inner,
    )

    if new_imports_inner == imports_inner:
        print(f"  ⚠ {rel_path}: nao consegui substituir 'api' no import")
        return False

    new_content = content[:m.start(1)] + new_imports_inner + content[m.end(1):]
    p.write_text(new_content)
    print(f"  ✓ {rel_path}: import patched")
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
        bk = v.with_suffix(f".ts.bak.v8c2.{stamp}")
        shutil.copy2(v, bk)
        print(f"  backup -> {bk.name}")
    if not patch_v2_api(root):
        print("  ERRO: patch v2-api.ts falhou.")
        sys.exit(1)

    section("2. PATCH paginas/componentes")
    targets = [
        "frontend/app/v2/cleaning/page.tsx",
        "frontend/app/v2/incidents/page.tsx",
        "frontend/components/v2/WeatherWidget.tsx",
    ]
    for rel in targets:
        full = root / rel
        if full.exists():
            bk = full.with_suffix(f".tsx.bak.v8c2.{stamp}")
            shutil.copy2(full, bk)
        patch_page_imports(root, rel)

    section("3. VALIDAR TypeScript localmente")
    if (root / "frontend" / "node_modules").exists():
        ok = run(
            "npx tsc --noEmit 2>&1 | grep -E 'cleaning|incidents|WeatherWidget|v2-api' | head -20",
            cwd=str(root / "frontend"),
        )
        print("  (sem output acima = ZERO erros nestes ficheiros = bom)")
    else:
        print("  i sem node_modules · Vercel valida")

    section("4. GIT COMMIT + PUSH")
    run("git add frontend/", cwd=str(root))
    run("git status --short | head -10", cwd=str(root))
    msg = "fix(v8c2): TypeScript-aware extension of api via apiOps cast"
    run(f'git commit -m "{msg}"', cwd=str(root))
    run("git push", cwd=str(root))

    section("5. AGUARDA Vercel rebuildar (~90s)")
    print("""
  Aguarda 90s e testa:
    sleep 90
    for p in /v2 /v2/cleaning /v2/incidents /v2/operations; do
      CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://www.plantarockinrio.com${p}")
      echo "  ${CODE}  ${p}"
    done

  Esperado: 4x HTTP 200.
""")


if __name__ == "__main__":
    main()
