#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_v29 — corrige o TopBar (desbloqueia o build) + nav + logo->home

1. CORRIGE o item Chat partido na linha 21 (faltava 'hint' -> build falhava
   na Vercel -> nenhuma pagina nova aparecia). Da-lhe hint e separa do Shows.
2. REMOVE o "Inicio" do nav (irrelevante).
3. REMOVE o "Chat" duplicado antigo (/v2/chat), fica so o /v2/chat2.
4. Logo + "Planta Smart Homes" ja e um <Link> — garante que aponta para a home.
"""

import os, re, shutil, subprocess, sys
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
    f = root / "frontend" / "components" / "v2" / "TopBar.tsx"
    if not f.exists():
        print("ERRO: corre a partir de ~/planta_rock4")
        sys.exit(1)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(f, f.with_suffix(f".tsx.bak.v29.{stamp}"))
    c = f.read_text()
    orig = c
    changed = []

    # 1+2+3. Reconstruir o array NAV de forma limpa e deterministica.
    # Apanha do "const NAV" ate ao "];" que fecha.
    m = re.search(r"const NAV:\s*NavItem\[\]\s*=\s*\[(.*?)\];", c, re.DOTALL)
    if not m:
        print("ERRO: nao encontrei o array NAV. Aborta sem mexer.")
        sys.exit(1)

    new_nav = (
        "const NAV: NavItem[] = [\n"
        "  { href: '/v2/chat2',      label: 'Chat',       hint: 'G ?' },\n"
        "  { href: '/v2/twin',       label: 'Twin',       hint: 'G T' },\n"
        "  { href: '/v2/sensors',    label: 'Sensores',   hint: 'G S' },\n"
        "  { href: '/v2/shows',      label: 'Shows',      hint: 'G W' },\n"
        "  { href: '/v2/operations', label: 'Operações',  hint: 'G O' },\n"
        "  { href: '/v2/cleaning',   label: 'Limpeza',    hint: 'G L' },\n"
        "  { href: '/v2/incidents',  label: 'Incidentes', hint: 'G I' },\n"
        "  { href: '/v2/scor',       label: 'SCOR',       hint: 'G C' },\n"
        "  { href: '/v2/pipelines',  label: 'Pipelines',  hint: 'G P' },\n"
        "];"
    )
    c = c[:m.start()] + new_nav + c[m.end():]
    changed.append("NAV reconstruido: Chat (com hint) no topo, sem Inicio, sem Chat duplicado")

    # 4. Garantir que o <Link> do logo aponta para a home.
    # O logo esta na linha ~132 num <Link>. Procurar o primeiro <Link ... href="..."> que envolve o logo.
    # Se o href do bloco do logo nao for "/v2" nem "/", forcar "/v2".
    logo_idx = c.find('src="/planta-logo.svg"')
    if logo_idx != -1:
        # encontrar o <Link href=... mais proximo ANTES do logo
        link_open = c.rfind("<Link", 0, logo_idx)
        if link_open != -1:
            href_m = re.search(r'href=\{?["\']([^"\']+)["\']\}?', c[link_open:logo_idx])
            if href_m:
                cur_href = href_m.group(1)
                if cur_href not in ("/v2", "/"):
                    seg = c[link_open:logo_idx]
                    seg2 = seg.replace(href_m.group(0), 'href="/v2"', 1)
                    c = c[:link_open] + seg2 + c[logo_idx:]
                    changed.append(f"logo Link href {cur_href} -> /v2 (homepage)")
                else:
                    changed.append(f"logo ja liga a home ({cur_href}) — ok")
            else:
                changed.append("logo: <Link> sem href explicito — verifica manualmente")
        else:
            changed.append("logo nao esta dentro de <Link> — verifica manualmente")
    else:
        changed.append("logo planta-logo.svg nao encontrado no header — skip")

    if c == orig:
        print("Nada mudou (ja estava corrigido?).")
        return

    f.write_text(c)
    for ch in changed:
        print(f"  OK {ch}")

    print()
    print("=" * 64)
    print("  VERIFICACAO RAPIDA (deve mostrar Chat com hint, sem Inicio)")
    print("=" * 64)
    for line in c.splitlines():
        if "href: '/v2" in line:
            print("   " + line.strip())

    print()
    run("git add frontend/components/v2/TopBar.tsx", cwd=str(root))
    run('git commit -m "fix(v29): TopBar build (Chat com hint), remove Inicio + Chat duplicado, logo->home"', cwd=str(root))
    run("git push", cwd=str(root))

    print()
    print("  ISTO DESBLOQUEIA O BUILD. Aguarda ~90s e CMD+SHIFT+R.")
    print("  Agora /v2/shows (v27) e /v2/chat2 (v28) vao finalmente aparecer.")
    print("  Confirma em vercel.com que o deploy fica 'Ready' (nao 'Error').")


if __name__ == "__main__":
    main()
