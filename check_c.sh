#!/usr/bin/env bash
# PlantaOS · Caminho C · Diagnose pré-fix
# Cola este comando no terminal:  bash check_c.sh
# E cola tudo o que aparece de volta no chat.

set +e
OUT=/tmp/check_c.txt
rm -f "$OUT"

log() { echo "$@" | tee -a "$OUT"; }
sep() { log ""; log "═════════════════════════════════════════════════════════════"; log "  $1"; log "═════════════════════════════════════════════════════════════"; log ""; }

sep "PASSO 1 · Onde está 'simulation' no Python"
grep -rn "simulation" app/ --include="*.py" 2>/dev/null | tee -a "$OUT"

sep "PASSO 2 · Onde está 'simulated'/'simulado' no Python"
grep -rn -e "simulated" -e "simulado" app/ --include="*.py" 2>/dev/null | tee -a "$OUT"

sep "PASSO 3 · Onde aparecem no frontend?"
grep -rn -e "simulation" -e "simulated" -e "simulado" -e "SIMULADO" frontend/app/v2 frontend/components/v2 frontend/lib 2>/dev/null | tee -a "$OUT"

sep "PASSO 4 · Resposta crua do /api/v1/health (procuramos 'simulation')"
curl -s --max-time 5 https://api.plantarockinrio.com/api/v1/health | tee -a "$OUT"
log ""

sep "PASSO 5 · Resposta crua do /api/v1/state (primeiros 600 chars)"
curl -s --max-time 5 https://api.plantarockinrio.com/api/v1/state | head -c 600 | tee -a "$OUT"
log ""

sep "PASSO 6 · /v2 página HTML — pessoas estimadas e ocupação a render"
curl -s --max-time 5 https://www.plantarockinrio.com/v2 > /tmp/v2.html
log "Tamanho HTML: $(wc -c < /tmp/v2.html) bytes"
log ""
log "Mostra-me se as palavras 'Pessoas estimadas' e '0%' aparecem juntas no HTML:"
grep -o "Pessoas estimadas[^<]*\|Ocupação média[^<]*\|Lugares livres[^<]*\|Flow Index[^<]*" /tmp/v2.html | head -10 | tee -a "$OUT"
log ""
log "Mostra-me se aparece 'NEXT_PUBLIC_API_URL' ou o URL hardcoded:"
grep -o "api\.plantarockinrio\.com[^\"']*\|NEXT_PUBLIC_API_URL" /tmp/v2.html | head -5 | tee -a "$OUT"

sep "PASSO 7 · Frontend tem .env file?"
ls -la frontend/.env* 2>/dev/null | tee -a "$OUT"
log ""
log "Conteúdo do frontend/.env.production se existir:"
cat frontend/.env.production 2>/dev/null | tee -a "$OUT"
cat frontend/.env.local 2>/dev/null | tee -a "$OUT"

sep "PASSO 8 · O page.tsx do /v2 está mesmo a chamar api.state()?"
log "Procurar chamadas a 'api.' no /v2/page.tsx:"
grep -n "api\." frontend/app/v2/page.tsx 2>/dev/null | head -10 | tee -a "$OUT"
log ""
log "Procurar useEffect / useState no /v2/page.tsx:"
grep -n "useEffect\|useState" frontend/app/v2/page.tsx 2>/dev/null | head -5 | tee -a "$OUT"

sep "PASSO 9 · O lib/v2-api.ts está a apontar para o URL certo?"
grep -n "API_BASE\|api\.plantarockinrio\|NEXT_PUBLIC_API" frontend/lib/v2-api.ts 2>/dev/null | head -5 | tee -a "$OUT"

sep "PASSO 10 · Vercel logs do frontend (deployment recente)?"
log "Último commit:"
git log --oneline -3 2>&1 | tee -a "$OUT"
log ""

sep "FIM"
log "Cola TODO o output desta caixa no chat. Vou ler ponto a ponto e arranjar tudo."
