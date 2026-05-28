#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v8b — Hotfix forecast router

Causa do bug:
  app/routers/forecast.py importava get_current_state (não existe).
  Função real: get_live_payload() — sync, devolve LivePayload.

Fix: reescreve app/routers/forecast.py.
"""

import base64
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

FORECAST_B64 = (
    'IiIiClBsYW50YU9TIMK3IEZvcmVjYXN0IHJvdXRlciAodjhiIOKAlCBjb3JyaWdpZG8pCj09PT09'
    'PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PQpHRVQgL2FwaS92MS9mb3Jl'
    'Y2FzdC9jbHVzdGVyL3tjbHVzdGVyX2lkfT9ob3Jpem9uX21pbj0zMAoKTMOqIG8gZXN0YWRvIGFj'
    'dHVhbCB2aWEgZ2V0X2xpdmVfcGF5bG9hZCgpIChzeW5jKSwgYWdyZWdhIHNlY8Onw7VlcyBwb3Ig'
    'Y2x1c3RlciwKZSBwcm9qZWN0YSBhIGN1cnZhIGEgNS8xMC8xNS8yMC8yNS8zMCBtaW4uCiIiIgpm'
    'cm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRpb25zCgpmcm9tIGRhdGV0aW1lIGltcG9ydCBk'
    'YXRldGltZSwgdGltZXpvbmUKZnJvbSB0eXBpbmcgaW1wb3J0IE9wdGlvbmFsCgpmcm9tIGZhc3Rh'
    'cGkgaW1wb3J0IEFQSVJvdXRlciwgSFRUUEV4Y2VwdGlvbiwgUXVlcnkKZnJvbSBweWRhbnRpYyBp'
    'bXBvcnQgQmFzZU1vZGVsCgpmcm9tIGFwcC5zZXJ2aWNlcyBpbXBvcnQgZm9yZWNhc3QgYXMgZmNf'
    'c2VydmljZQpmcm9tIGFwcC5zZXJ2aWNlcy5zdGF0ZSBpbXBvcnQgZ2V0X2xpdmVfcGF5bG9hZAoK'
    'cm91dGVyID0gQVBJUm91dGVyKHByZWZpeD0iL2FwaS92MS9mb3JlY2FzdCIsIHRhZ3M9WyJmb3Jl'
    'Y2FzdCJdKQoKCmNsYXNzIEZvcmVjYXN0UG9pbnRPdXQoQmFzZU1vZGVsKToKICAgIG1pbnV0ZXNf'
    'YWhlYWQ6IGludAogICAgb2N1cGFjYW9fcGN0OiBmbG9hdAogICAgY29uZmlkZW5jZTogZmxvYXQK'
    'ICAgIHN1cmdlX2FjdGl2ZTogYm9vbAoKCmNsYXNzIEZvcmVjYXN0UmVzcG9uc2UoQmFzZU1vZGVs'
    'KToKICAgIGNsdXN0ZXJfaWQ6IHN0cgogICAgaG9yaXpvbl9taW46IGludAogICAgY3VycmVudF9v'
    'Y3VwYWNhb19wY3Q6IGZsb2F0CiAgICBwb2ludHM6IGxpc3RbRm9yZWNhc3RQb2ludE91dF0KICAg'
    'IHBlYWtfb2N1cGFjYW9fcGN0OiBmbG9hdAogICAgcGVha19hdF9taW46IGludAogICAgbm90ZXM6'
    'IGxpc3Rbc3RyXQogICAgZ2VuZXJhdGVkX2F0OiBkYXRldGltZQoKCmRlZiBfbWludXRlc190b19u'
    'ZXh0X3Nob3dfZW5kKCkgLT4gT3B0aW9uYWxbaW50XToKICAgICIiIlN0dWI6IGxpZ2FyIGFvIHNj'
    'aGVkdWxlIGRlIHNob3dzIGZpY2EgcGFyYSB2OS4gU2VtIHN1cmdlIHByZXZpc3RvIHBvciBkZWZl'
    'aXRvLiIiIgogICAgcmV0dXJuIE5vbmUKCgpAcm91dGVyLmdldCgiL2NsdXN0ZXIve2NsdXN0ZXJf'
    'aWR9IiwgcmVzcG9uc2VfbW9kZWw9Rm9yZWNhc3RSZXNwb25zZSkKZGVmIGNsdXN0ZXJfZm9yZWNh'
    'c3QoCiAgICBjbHVzdGVyX2lkOiBzdHIsCiAgICBob3Jpem9uX21pbjogaW50ID0gUXVlcnkoMzAs'
    'IGdlPTUsIGxlPTYwKSwKKToKICAgICIiIlByb2plY3RhIG9jdXBhw6fDo28gZGUgdW0gY2x1c3Rl'
    'ciBhbyBsb25nbyBkbyBob3Jpem9udGUuIiIiCiAgICB0cnk6CiAgICAgICAgcGF5bG9hZCA9IGdl'
    'dF9saXZlX3BheWxvYWQoKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIHJhaXNl'
    'IEhUVFBFeGNlcHRpb24oNTAwLCBkZXRhaWw9ZiJOw6NvIGNvbnNlZ3VpIGxlciBlc3RhZG86IHtl'
    'fSIpCgogICAgc2VjdGlvbnMgPSBnZXRhdHRyKHBheWxvYWQsICJzZWN0aW9ucyIsIE5vbmUpIG9y'
    'IFtdCiAgICBjbHVzdGVyX3BjdHM6IGxpc3RbZmxvYXRdID0gW10KICAgIGZvciBzIGluIHNlY3Rp'
    'b25zOgogICAgICAgIHNpZCA9IGdldGF0dHIocywgInNlY3Rpb25faWQiLCAiIikgb3IgIiIKICAg'
    'ICAgICAjIHNlY3Rpb25faWQgdMOtcGljbzogIldDLTA0X00iIG91ICJXQy0wNiIgKHVuaXNleCkK'
    'ICAgICAgICBpZiBzaWQuc3RhcnRzd2l0aChjbHVzdGVyX2lkKToKICAgICAgICAgICAgcGN0ID0g'
    'Z2V0YXR0cihzLCAib2N1cGFjYW9fcGN0IiwgMC4wKSBvciAwLjAKICAgICAgICAgICAgY2x1c3Rl'
    'cl9wY3RzLmFwcGVuZChmbG9hdChwY3QpKQoKICAgIGlmIG5vdCBjbHVzdGVyX3BjdHM6CiAgICAg'
    'ICAgcmFpc2UgSFRUUEV4Y2VwdGlvbig0MDQsIGRldGFpbD1mIkNsdXN0ZXIge2NsdXN0ZXJfaWR9'
    'IG7Do28gZW5jb250cmFkbyIpCgogICAgY3VycmVudF9wY3QgPSBzdW0oY2x1c3Rlcl9wY3RzKSAv'
    'IGxlbihjbHVzdGVyX3BjdHMpCgogICAgZm9yZWNhc3QgPSBmY19zZXJ2aWNlLnByb2plY3QoCiAg'
    'ICAgICAgY2x1c3Rlcl9pZD1jbHVzdGVyX2lkLAogICAgICAgIGN1cnJlbnRfcGN0PWN1cnJlbnRf'
    'cGN0LAogICAgICAgIHRyZW5kX3Nsb3BlX3Blcl9taW49MC4wLAogICAgICAgIG1pbnV0ZXNfdG9f'
    'c2hvd19lbmQ9X21pbnV0ZXNfdG9fbmV4dF9zaG93X2VuZCgpLAogICAgICAgIGhvcml6b25fbWlu'
    'PWhvcml6b25fbWluLAogICAgKQoKICAgIHJldHVybiBGb3JlY2FzdFJlc3BvbnNlKAogICAgICAg'
    'IGNsdXN0ZXJfaWQ9Zm9yZWNhc3QuY2x1c3Rlcl9pZCwKICAgICAgICBob3Jpem9uX21pbj1mb3Jl'
    'Y2FzdC5ob3Jpem9uX21pbiwKICAgICAgICBjdXJyZW50X29jdXBhY2FvX3BjdD1mb3JlY2FzdC5j'
    'dXJyZW50X29jdXBhY2FvX3BjdCwKICAgICAgICBwb2ludHM9WwogICAgICAgICAgICBGb3JlY2Fz'
    'dFBvaW50T3V0KAogICAgICAgICAgICAgICAgbWludXRlc19haGVhZD1wLm1pbnV0ZXNfYWhlYWQs'
    'CiAgICAgICAgICAgICAgICBvY3VwYWNhb19wY3Q9cC5vY3VwYWNhb19wY3QsCiAgICAgICAgICAg'
    'ICAgICBjb25maWRlbmNlPXAuY29uZmlkZW5jZSwKICAgICAgICAgICAgICAgIHN1cmdlX2FjdGl2'
    'ZT1wLnN1cmdlX2FjdGl2ZSwKICAgICAgICAgICAgKQogICAgICAgICAgICBmb3IgcCBpbiBmb3Jl'
    'Y2FzdC5wb2ludHMKICAgICAgICBdLAogICAgICAgIHBlYWtfb2N1cGFjYW9fcGN0PWZvcmVjYXN0'
    'LnBlYWtfb2N1cGFjYW9fcGN0LAogICAgICAgIHBlYWtfYXRfbWluPWZvcmVjYXN0LnBlYWtfYXRf'
    'bWluLAogICAgICAgIG5vdGVzPWZvcmVjYXN0Lm5vdGVzLAogICAgICAgIGdlbmVyYXRlZF9hdD1k'
    'YXRldGltZS5ub3codGltZXpvbmUudXRjKSwKICAgICkK'
)

def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0

def main():
    root = Path.cwd()
    if not (root / "app").exists():
        print("ERRO: corre a partir de ~/planta_rock4")
        sys.exit(1)
    
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = root / "app" / "routers" / "forecast.py"
    
    print("=" * 68)
    print("  HOTFIX · forecast.py — usar get_live_payload (sync)")
    print("=" * 68)
    
    if target.exists():
        bk = target.with_suffix(f".py.bak.v8b.{stamp}")
        shutil.copy2(target, bk)
        print(f"  backup → {bk.name}")
    
    data = base64.b64decode("".join(FORECAST_B64))
    target.write_bytes(data)
    print(f"  ✓ escrito ({len(data)} B)")
    
    if not run("python3 -m py_compile app/routers/forecast.py", cwd=str(root)):
        print("ERRO: syntax inválida")
        sys.exit(1)
    print("  ✓ Python OK")
    
    print()
    print("  GIT COMMIT + PUSH")
    run("git add app/routers/forecast.py", cwd=str(root))
    run('git commit -m "fix(forecast): usar get_live_payload sync · resolve deploy fail"', cwd=str(root))
    run("git push", cwd=str(root))
    
    print()
    print("  Aguarda Railway rebuildar (~2min) e testa:")
    print("  curl -s https://api.plantarockinrio.com/api/v1/forecast/cluster/WC-04 | python3 -m json.tool")

if __name__ == "__main__":
    main()
