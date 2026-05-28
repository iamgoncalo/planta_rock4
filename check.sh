#!/usr/bin/env bash
# PlantaOS · Diagnóstico completo do backend
# Corre do ~/planta_rock4 com:  bash check.sh

set +e
OUT=/tmp/backend_check.txt
API=https://api.plantarockinrio.com

# Limpa output anterior
rm -f "$OUT"
touch "$OUT"

log() { echo "$@" | tee -a "$OUT"; }
sep() { log ""; log "═══════════════════════════════════════════════════════════════"; log "  $1"; log "═══════════════════════════════════════════════════════════════"; log ""; }

sep "DIAGNÓSTICO BACKEND · $(date)"

# ─────────────────────────────────────────────────────────────
sep "1. ESTRUTURA DO PROJECTO"
log "Routers:"
ls app/routers/ 2>/dev/null | tee -a "$OUT"
log ""
log "Services:"
ls app/services/ 2>/dev/null | tee -a "$OUT"
log ""
log "Models:"
ls app/models/ 2>/dev/null | tee -a "$OUT"

# ─────────────────────────────────────────────────────────────
sep "2. PROCURAR WORDS PROIBIDAS"
log "[simulation/simulated]"
grep -rn -e "simulation" -e "simulated" app/ --include="*.py" 2>/dev/null | tee -a "$OUT"
log ""
log "[simulado]"
grep -rn "simulado" app/ --include="*.py" 2>/dev/null | head -30 | tee -a "$OUT"

# ─────────────────────────────────────────────────────────────
sep "3. STATUS HTTP DE TODOS OS ENDPOINTS"
for path in \
  /health \
  /api/v1/health \
  /api/v1/state \
  /api/v1/clusters \
  /api/v1/kpis \
  /api/v1/sensors \
  /api/v1/sensors/summary \
  /api/v1/sensors/battery/status \
  /api/v1/sensors/coverage/geojson \
  /api/v1/shows \
  /api/v1/alerts \
  /api/v1/devices \
  /api/v1/devices/firmware/latest \
  /v1/health \
  /v1/kpis \
  /v1/sections
do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API$path")
  log "  $CODE   GET $path"
done

# ─────────────────────────────────────────────────────────────
sep "4. CONTEÚDO DAS RESPOSTAS PRINCIPAIS"

log "[GET /api/v1/health]"
curl -s --max-time 5 "$API/api/v1/health" >> "$OUT"
log ""
log ""

log "[GET /api/v1/kpis]"
curl -s --max-time 5 "$API/api/v1/kpis" >> "$OUT"
log ""
log ""

log "[GET /api/v1/sensors/summary]"
curl -s --max-time 5 "$API/api/v1/sensors/summary" >> "$OUT"
log ""
log ""

log "[GET /api/v1/state · primeiros 800 chars]"
curl -s --max-time 5 "$API/api/v1/state" | head -c 800 >> "$OUT"
log ""
log ""

log "[GET /api/v1/clusters · primeiros 800 chars]"
curl -s --max-time 5 "$API/api/v1/clusters" | head -c 800 >> "$OUT"
log ""
log ""

log "[GET /api/v1/shows]"
curl -s --max-time 5 "$API/api/v1/shows" >> "$OUT"
log ""
log ""

log "[GET /api/v1/alerts]"
curl -s --max-time 5 "$API/api/v1/alerts" >> "$OUT"
log ""
log ""

log "[POST /api/v1/chat]"
curl -s --max-time 10 -X POST "$API/api/v1/chat" \
  -H "content-type: application/json" \
  -d '{"message":"Resume em duas frases o estado actual"}' >> "$OUT"
log ""
log ""

# ─────────────────────────────────────────────────────────────
sep "5. FRONTEND · WWW.PLANTAROCKINRIO.COM"
WWW=https://www.plantarockinrio.com
for path in / /v2 /v2/twin /v2/sensors /v2/shows /v2/operations /v2/chat
do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -L "$WWW$path")
  log "  $CODE   GET $WWW$path"
done

# ─────────────────────────────────────────────────────────────
sep "6. APEX · PLANTAROCKINRIO.COM (sem www)"
APEX=https://plantarockinrio.com
for path in / /v2
do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$APEX$path")
  log "  $CODE   GET $APEX$path"
done

# ─────────────────────────────────────────────────────────────
sep "7. GIT STATE"
log "Últimos commits:"
git log --oneline -5 2>&1 | tee -a "$OUT"
log ""
log "Trabalho local (não pushed):"
git status --short 2>&1 | tee -a "$OUT"

# ─────────────────────────────────────────────────────────────
sep "8. RAILWAY LOGS · ÚLTIMOS chat.v5 + ERROS"
railway logs --service planta_rock4 2>&1 | grep -E "chat\.v5|ERROR|Traceback|google-genai" | tail -20 | tee -a "$OUT"

# ─────────────────────────────────────────────────────────────
sep "9. FRONTEND CHAMA O BACKEND? VEJO O QUE ESTÁ EM page.tsx"
log "Procurar fetch / api_url no frontend:"
grep -rn "plantarockinrio.com\|NEXT_PUBLIC_API" frontend/app/v2 frontend/lib 2>/dev/null | head -10 | tee -a "$OUT"
log ""
log "Variáveis de ambiente do frontend:"
cat frontend/.env.production 2>/dev/null | tee -a "$OUT"
cat frontend/.env.local 2>/dev/null | tee -a "$OUT"
ls -la frontend/.env* 2>/dev/null | tee -a "$OUT"

sep "FIM · Output completo em $OUT"
echo ""
echo "════════════════════════════════════════════════════"
echo "  Para colar no Claude, mostra o ficheiro com:"
echo "    cat $OUT"
echo "════════════════════════════════════════════════════"
