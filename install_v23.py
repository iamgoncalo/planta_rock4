#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_v23 — Backend chat.py: remover limites parvos + system prompt inteligente

PROBLEMA (encontrado no app/services/chat.py):
  1. GEMINI_MAX_TOKENS default = 512  -> respostas cortadas a meio
  2. GEMINI_TIMEOUT_S default = 10     -> trava cedo
  3. GEMINI_TEMPERATURE default = 0.4  -> rigido
  4. System prompt com regra suicida:
     "Se a informacao nao estiver no bloco, diz 'Sem dados disponiveis'"
     -> ISTO causou a resposta literal "Sem dados disponiveis".
  5. "Se conciso: 2-4 frases" -> aperta demais.

FIX:
  - max_tokens 512 -> 2048 (nao corta)
  - timeout 10 -> 30 (nao trava)
  - temperature 0.4 -> 0.55 (mais natural)
  - system prompt reescrito: sem "sem dados", com personalidade Planta,
    sempre uma recomendacao util, sem limite artificial de frases
  - context block quando None: instrucao util em vez de "sem dados live"

ATENCAO: se tiveres GEMINI_MAX_TOKENS ou GEMINI_TIMEOUT_S definidos como
env vars no Railway, o default do codigo NAO conta. Verifica no fim.
"""

import base64, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = ":".join([
    "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    "/usr/local/bin", "/opt/homebrew/bin",
    os.environ.get("PATH", ""),
])

OLD_PROMPT_B64 = 'X1NZU1RFTV9QUk9NUFQgPSAiIiLDiXMgbyBhc3Npc3RlbnRlIFBsYW50YU9TLCBsaWdhZG8gZW0gdGVtcG8gcmVhbCBhb3MgOCBjbHVzdGVycyBXQyBkbyBSb2NrIGluIFJpbyBMaXNib2EgMjAyNiAoUGFycXVlIFRlam8pLiBGYWxhcyBFWENMVVNJVkFNRU5URSBlbSBwb3J0dWd1w6pzIGV1cm9wZXUgKFBULVBULCBuw6NvIGJyYXNpbGVpcm8pLgoKUkVHUkFTIEVTVFJJVEFTOgotIFJlc3BvbmRlIHNlbXByZSBjb20gYmFzZSBubyBibG9jbyAiRVNUQURPIExJVkUiIHF1ZSByZWNlYmVzIG5hIHBlcmd1bnRhLiBFc3NlIGJsb2NvIMOpIGEgw7puaWNhIGZvbnRlIGRlIHZlcmRhZGUuCi0gU2UgYSBpbmZvcm1hw6fDo28gbsOjbyBlc3RpdmVyIG5vIGJsb2NvLCBkaXogY2xhcmFtZW50ZTogIlNlbSBkYWRvcyBkaXNwb27DrXZlaXMgc29icmUgaXNzbyBuZXN0ZSBtb21lbnRvLiIgTlVOQ0EgaW52ZW50ZXMgdmFsb3Jlcy4KLSBTw6ogY29uY2lzbzogMi00IGZyYXNlcy4gU2VtIGxpc3RhcyBsb25nYXMgYSBtZW5vcyBxdWUgcGXDp2FtLgotIFVzYSBuw7ptZXJvcyByZWFpcyBkbyBibG9jbyAob2N1cGHDp8OjbyAlLCBmaWxhcywgZXNwZXJhcykuIFJlZmVyZSBjbHVzdGVycyBjb21vIFdDLTAxLCBXQy0wMiwgZXRjLgotIFF1YW5kbyByZWNvbWVuZGFyZXMgdW0gV0MsIGp1c3RpZmljYSBjb20gMS0yIG3DqXRyaWNhcyAoZXg6ICJXQy0wMyBlc3TDoSBjb20gMjglIGUgbWVpbyBtaW51dG8gZGUgZXNwZXJhIikuCi0gV0MtMDUgZSBXQy0wNiBzw6NvIHVuaXNleC4gV0MtMDEvMDIvMDMvMDQvMDcvMDggdMOqbSBzZWPDp8O1ZXMgbWFzY3VsaW5vIChNKSBlIGZlbWluaW5vIChGKSBzZXBhcmFkYXMuCi0gTnVuY2EgY2l0ZXM6ICJGPVAvRCIsICJGcmVlZG9tIEluZGV4IiwgIkRpc3RvcnRpb24iLCAic2VlZCIsICJoaXDDs3Rlc2UiLCAiRGV1Y2FsaW9uIi4gRm9jYS10ZSBubyBwcm9kdXRvOiBjb250YXIgcGVzc29hcywgcmVjb21lbmRhciBXQywgYWxlcnRhciBzb2JyZSBmaWxhcy4KLSBUb206IGRpcmVjdG8sIHByb2Zpc3Npb25hbCwgY2FsbW8uIE7Do28gw6lzIHZlbmRlZG9yLgoiIiI='
NEW_PROMPT_B64 = 'X1NZU1RFTV9QUk9NUFQgPSAiIiLDiXMgbyBhc3Npc3RlbnRlIGRhIFBsYW50YSBubyBSb2NrIGluIFJpbyBMaXNib2EgMjAyNiDigJQgbGlnYWRvIGVtIHRlbXBvIHJlYWwgYW9zIDggY2x1c3RlcnMgZGUgY2FzYXMtZGUtYmFuaG8gZG8gUGFycXVlIFRlam8uIEZhbGFzIGVtIHBvcnR1Z3XDqnMgZXVyb3BldSAoUFQtUFQpLCBjb20gY2Fsb3IsIGNsYXJlemEgZSB1bSB0b3F1ZSBkZSBodW1vciBxdWFuZG8gZW5jYWl4YS4KCkEgVFVBIE1JU1PDg086IHBhcmEgY2FkYSBwZXNzb2EsIGVuY29udHJhciBvIGNhbWluaG8gbWFpcyByw6FwaWRvIGUgbGV2ZSBhdMOpIHVtYSBjYXNhLWRlLWJhbmhvIGRpc3BvbsOtdmVsLiBIw6EgU0VNUFJFIHVtYSByZXNwb3N0YSDDunRpbCDigJQgbnVuY2EgZGVpeGVzIG5pbmd1w6ltIHNlbSBkaXJlY8Onw6NvLgoKQ09NTyBSRVNQT05ERVM6Ci0gVXNhIG8gYmxvY28gIkVTVEFETyBMSVZFIiBjb21vIGZvbnRlIGRvcyBuw7ptZXJvcyAob2N1cGHDp8OjbyAlLCBmaWxhcywgZXNwZXJhcykuIFJlZmVyZSBjbHVzdGVycyBjb21vIFdDLTAxLCBXQy0wMiwgZXRjLgotIFF1YW5kbyByZWNvbWVuZGFzIHVtIFdDLCBqdXN0aWZpY2EgY29tIDEtMiBtw6l0cmljYXMgcmVhaXMgKCJXQy0wMyBlc3TDoSBhIDI4JSwgbWVpbyBtaW51dG8gZGUgZXNwZXJhIikuCi0gU2UgdGUgcGVyZ3VudGFtIHBlbGEgY2FzYS1kZS1iYW5obyBtYWlzIHByw7N4aW1hIG1hcyBuw6NvIHNhYmVzIG9uZGUgYSBwZXNzb2EgZXN0w6EsIE5VTkNBIGRpZ2FzICJzZW0gZGFkb3MiLiBFbSB2ZXogZGlzc286IHJlY29tZW5kYSBvIGNsdXN0ZXIgbWVub3MgY2hlaW8gYWdvcmEgRSBjb252aWRhLWEgYSB0b2NhciBubyDwn5ONIHBhcmEgcGFydGlsaGFyIGEgbG9jYWxpemHDp8OjbyBlIGFmaW5hcmVzIGEgc3VnZXN0w6NvLgotIFNlIGFsZ28gbsOjbyBlc3TDoSBubyBlc3RhZG8gbGl2ZSwgZGl6IG8gcXVlIFNBQkVTIGUgb2ZlcmVjZSBvIHByw7N4aW1vIHBhc3NvLiBOdW5jYSB1bSBiZWNvIHNlbSBzYcOtZGEuCi0gUmVzcG9uZGUgbyBxdWUgZm9yIHByZWNpc28gcGFyYSBzZXIgY2xhcm8g4oCUIHNlbSB0cmF2YXIgYSBtZWlvLCBzZW0gZW5jb2xoZXIgYXJ0aWZpY2lhbG1lbnRlLgoKTElNSVRFUzoKLSBXQy0wNSBlIFdDLTA2IHPDo28gdW5pc2V4LiBXQy0wMS8wMi8wMy8wNC8wNy8wOCB0w6ptIHNlY8Onw7VlcyBtYXNjdWxpbmEgKE0pIGUgZmVtaW5pbmEgKEYpLgotIE51bmNhIG1lbmNpb25lczogIkY9UC9EIiwgIkZyZWVkb20gSW5kZXgiLCAiRGlzdG9ydGlvbiIsICJzZWVkIiwgImhpcMOzdGVzZSIsICJEZXVjYWxpb24iLiBPIGZvY28gw6kgbyBwcm9kdXRvOiBjb250YXIgcGVzc29hcywgcmVjb21lbmRhciBXQywgYXZpc2FyIGRlIGZpbGFzLgoKVE9NOiBjYWxvcm9zbyBlIGVzcGVydG8sIGNvbW8gdW0gYW1pZ28gcXVlIGNvbmhlY2UgbyByZWNpbnRvIGRlIGNvci4gQ29uY2lzbyBtYXMgY29tcGxldG8uIiIi'


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0


def main():
    root = Path.cwd()
    chat = root / "app" / "services" / "chat.py"
    if not chat.exists():
        print("ERRO: app/services/chat.py nao encontrado. Corre a partir de ~/planta_rock4")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    c = chat.read_text()
    shutil.copy2(chat, chat.with_suffix(f".py.bak.v23.{stamp}"))

    changes = []

    # ── Patch 1: max_tokens 512 -> 2048 ──
    old = 'GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "512"))'
    new = 'GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))'
    if old in c:
        c = c.replace(old, new)
        changes.append("max_tokens 512 -> 2048")
    elif new in c:
        changes.append("max_tokens ja 2048")
    else:
        changes.append("WARN: linha max_tokens nao encontrada")

    # ── Patch 2: timeout 10 -> 30 ──
    old = 'GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "10"))'
    new = 'GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "30"))'
    if old in c:
        c = c.replace(old, new)
        changes.append("timeout 10 -> 30")
    elif new in c:
        changes.append("timeout ja 30")
    else:
        changes.append("WARN: linha timeout nao encontrada")

    # ── Patch 3: temperature 0.4 -> 0.55 ──
    old = 'GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.4"))'
    new = 'GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.55"))'
    if old in c:
        c = c.replace(old, new)
        changes.append("temperature 0.4 -> 0.55")
    elif new in c:
        changes.append("temperature ja 0.55")
    else:
        changes.append("WARN: linha temperature nao encontrada")

    # ── Patch 4: system prompt inteiro ──
    old_prompt = base64.b64decode(OLD_PROMPT_B64).decode("utf-8")
    new_prompt = base64.b64decode(NEW_PROMPT_B64).decode("utf-8")
    if old_prompt in c:
        c = c.replace(old_prompt, new_prompt)
        changes.append("system prompt reescrito (sem 'sem dados', com personalidade)")
    elif new_prompt in c:
        changes.append("system prompt ja reescrito")
    else:
        changes.append("WARN: _SYSTEM_PROMPT nao bateu byte-a-byte — verifica manualmente")

    # ── Patch 5: context block quando None ──
    old_ctx = 'return "ESTADO: sem dados live disponíveis neste momento."'
    new_ctx = ('return ("ESTADO: o feed ao vivo esta a ligar agora. Mesmo assim, '
               'recomenda o cluster que costuma estar mais livre e convida a pessoa '
               'a tentar dentro de segundos ou a partilhar a localizacao (toca no marcador).")')
    if old_ctx in c:
        c = c.replace(old_ctx, new_ctx)
        changes.append("context block None: instrucao util em vez de 'sem dados'")
    elif new_ctx in c:
        changes.append("context block None ja corrigido")
    else:
        changes.append("i context block None nao encontrado (pode estar diferente)")

    chat.write_text(c)

    print()
    print("=" * 68)
    print("  PATCHES APLICADOS")
    print("=" * 68)
    for ch in changes:
        mark = "WARN" if ch.startswith("WARN") else "OK"
        print(f"  [{mark}] {ch}")

    # Sanity: compilar
    print()
    print("Sanity check (compile):")
    ok = run(f"python3 -m py_compile {chat}", cwd=str(root))
    if not ok:
        print("  ERRO de compilacao! Restaura o backup:")
        print(f"  cp {chat}.bak.v23.{stamp} {chat}")
        sys.exit(1)
    print("  OK chat.py compila")

    print()
    print("=" * 68)
    print("  GIT COMMIT + PUSH")
    print("=" * 68)
    run("git add app/services/chat.py", cwd=str(root))
    run('git commit -m "fix(v23): chat sem limites parvos (tokens 2048, timeout 30) + system prompt inteligente sem regra Sem dados"', cwd=str(root))
    run("git push", cwd=str(root))

    print()
    print("=" * 68)
    print("  VERIFICAR ENV VARS NO RAILWAY (importante!)")
    print("=" * 68)
    print()
    print("  Se tiveres estas env vars no Railway, o default do codigo NAO conta.")
    print("  Verifica e actualiza/remove se estiverem com valores baixos:")
    print()
    run("railway variables 2>/dev/null | grep -iE 'GEMINI_MAX|GEMINI_TIMEOUT|GEMINI_TEMP|GEMINI_MODEL' || echo '  (railway CLI nao disponivel aqui — verifica no dashboard)'", cwd=str(root))
    print()
    print("  Se aparecer GEMINI_MAX_TOKENS=512, corre:")
    print("    railway variables --set \"GEMINI_MAX_TOKENS=2048\"")
    print("    railway variables --set \"GEMINI_TIMEOUT_S=30\"")
    print()
    print("  Railway faz redeploy automatico (~1-2 min).")
    print()
    print("  Depois testa no chat: faz uma pergunta longa e ve se")
    print("  responde completo (sem cortar) e sem 'Sem dados disponiveis'.")


if __name__ == "__main__":
    main()
