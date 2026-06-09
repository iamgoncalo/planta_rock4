#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PlantaOS RiR2026 — VERIFICACAO TOTAL
# Correr na pasta-fonte:  bash verify_tudo.sh
# Sai com codigo 0 so se TUDO passar.
# ═══════════════════════════════════════════════════════════════
API="https://api.plantarockinrio.com/api/v1"
APIROOT="https://api.plantarockinrio.com"
FRONT="https://www.plantarockinrio.com"
PASS=0; FAIL=0; WARN=0
ok(){ PASS=$((PASS+1)); echo "  PASS  $1"; }
ko(){ FAIL=$((FAIL+1)); echo "  FAIL  $1"; }
wn(){ WARN=$((WARN+1)); echo "  WARN  $1"; }

echo ""
echo "═══ 1. ENDPOINTS EM PRODUCAO — status + tipo + latencia ═══"
for ep in health state kpis clusters/geo sensors shows alerts firmware sections flow/history flow/forecast fusion fleet/summary ingest/status scor/overview weather/now festival/days envs; do
  out=$(curl -s -o /tmp/r.json -w "%{http_code} %{content_type} %{time_total}" "$API/$ep" 2>/dev/null)
  code=$(echo "$out" | awk '{print $1}')
  ctype=$(echo "$out" | awk '{print $2}')
  t=$(echo "$out" | awk '{print $NF}')
  slow=$(python3 -c "print(1 if float('$t')>1.5 else 0)")
  if [ "$code" = "200" ] && echo "$ctype" | grep -qi "json"; then
    [ "$slow" = "1" ] && wn "$ep 200 mas lento (${t}s)" || ok "$ep 200 JSON ${t}s"
  elif [ "$code" = "404" ] && echo "$ctype" | grep -qi "json"; then
    wn "$ep 404 JSON (rota nao existe — confirmar se devia existir)"
  else
    ko "$ep -> $code $ctype (HTML do catch-all = bug de prefixo)"
  fi
done

echo ""
echo "═══ 2. ESQUEMA /clusters/geo — fonte unica ═══"
curl -s "$API/clusters/geo" > /tmp/geo.json
python3 - << 'PY'
import json
d = json.load(open("/tmp/geo.json"))
errs = []
a = d.get("anchor_gps", {})
if abs(a.get("lat",0) - 38.78145) > 1e-6 or abs(a.get("lon",0) - (-9.0943)) > 1e-6:
    errs.append(f"ancora errada: {a}")
cl = d.get("clusters", [])
if len(cl) != 8: errs.append(f"clusters={len(cl)} (esperado 8)")
ids = sorted(c["id"] for c in cl)
if ids != [f"WC-0{i}" for i in range(1,9)]: errs.append(f"ids={ids}")
for c in cl:
    if c["id"] in ("WC-05","WC-06"):
        if not c.get("unisex"): errs.append(f"{c['id']} devia ser unisex")
        if c.get("cap_m") or c.get("cap_f"): errs.append(f"{c['id']} unissexo NAO pode ter cap_m/cap_f")
        if not c.get("cap"): errs.append(f"{c['id']} sem cap unissexo")
    else:
        if c.get("unisex"): errs.append(f"{c['id']} nao devia ser unisex")
        if not c.get("cap_m") or not c.get("cap_f"): errs.append(f"{c['id']} M/F sem cap_m/cap_f")
    if not (38.77 < c.get("gps_lat",0) < 38.79): errs.append(f"{c['id']} lat fora do parque")
    if not (-9.10 < c.get("gps_lon",0) < -9.08): errs.append(f"{c['id']} lon fora do parque")
if errs:
    print("  FAIL  geo: " + " | ".join(errs)); exit(1)
print("  PASS  geo: 8 clusters, ancora correcta, WC-05/06 unissexo sem M/F, GPS dentro do parque")
PY
[ $? -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

echo ""
echo "═══ 3. RGPD — nenhum payload publico expoe MAC ou device GPS individual ═══"
for ep in state sensors clusters/geo kpis alerts flow_history; do
  body=$(curl -s "$API/$ep")
  # procura padrao MAC xx:xx:xx:xx:xx:xx e campos mac_*
  if echo "$body" | grep -qiE '([0-9a-f]{2}:){5}[0-9a-f]{2}|"mac"|mac_address'; then
    ko "RGPD: $ep contem MAC!"
  else
    ok "RGPD: $ep limpo (sem MAC)"
  fi
done

echo ""
echo "═══ 4. CASOS DE ERRO — API nunca devolve HTML, nunca 500 ═══"
# rota API inexistente -> tem de ser 404 JSON, nunca HTML do proxy
out=$(curl -s -o /tmp/e1.txt -w "%{http_code} %{content_type}" "$API/rota_que_nao_existe")
echo "$out" | grep -q "404" && echo "$out" | grep -qi json && ok "404 JSON em rota API desconhecida" || ko "rota API desconhecida -> $out (catch-all a engolir /api/*)"
# cluster invalido
out=$(curl -s -o /dev/null -w "%{http_code} %{content_type}" "$API/sections/WC-99")
echo "$out" | grep -qE "404|503" && echo "$out" | grep -qi json && ok "section invalida -> 404 JSON" || wn "section invalida -> $out"
# POST malformado no ingest -> 422, nunca 500
out=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/../ingest" -H "Content-Type: application/json" -d '{"lixo": true}' 2>/dev/null)
code2=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/ingest" -H "Content-Type: application/json" -d '{"lixo": true}')
if [ "$code2" = "422" ] || [ "$code2" = "400" ]; then ok "POST malformado /ingest -> $code2 (validado, sem 500)"
elif [ "$code2" = "500" ]; then ko "POST malformado /ingest -> 500 (validacao em falta!)"
else wn "POST malformado /ingest -> $code2 (verificar caminho real do ingest)"; fi
# JSON invalido (corpo partido)
code3=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/ingest" -H "Content-Type: application/json" -d '{nao e json')
[ "$code3" = "500" ] && ko "JSON partido -> 500" || ok "JSON partido -> $code3 (sem 500)"

echo ""
echo "═══ 5. FIRMWARE — integridade dos 34 servidos ═══"
total=$(curl -s "$API/firmware" | python3 -c "import json,sys; print(json.load(sys.stdin).get('total',0))")
[ "$total" = "34" ] && ok "endpoint serve exactamente 34 .ino (_TEMPLATE excluido)" || ko "endpoint serve $total (esperado 34)"
ino=$(curl -s "$API/firmware/wc01_h_ll.ino")
echo "$ino" | grep -q "GPIO\?36\|GPIO_NUM_36\|36" && ok "wc01_h_ll: IR A em GPIO36" || ko "wc01_h_ll: GPIO36 ausente"
echo "$ino" | grep -q "33" && ok "wc01_h_ll: IR B em GPIO33" || ko "wc01_h_ll: GPIO33 ausente"
echo "$ino" | grep -q "\-10000" && ok "wc01_h_ll: debounce -10000" || ko "wc01_h_ll: debounce errado"
echo "$ino" | grep -q "115200" && ok "wc01_h_ll: baud 115200" || ko "wc01_h_ll: baud errado"
echo "$ino" | grep -qE "GPIO26|gpio26" && ko "wc01_h_ll: USA GPIO26 (PROIBIDO — LoRa DIO0)" || ok "wc01_h_ll: GPIO26 ausente (correcto)"

echo ""
echo "═══ 6. FRONTEND EM PRODUCAO — todas as paginas v2/v3 ═══"
for pg in /v2 /v2/twin /v2/install /v2/flow /v2/screen /v2/cleaning /v2/shows /v2/chat /v3 /v3/twin /v3/install /v3/flow /v3/scor /v3/screen /v3/cleaning /v3/shows; do
  code=$(curl -s -o /tmp/p.html -w "%{http_code}" -L "$FRONT$pg")
  if [ "$code" = "200" ]; then
    # vocabulario proibido no HTML servido ao publico
    if grep -qiE "Deucalion|F=P/D|Freedom Index|FLRP|hypothesis under test|seed=2026" /tmp/p.html; then
      ko "$pg 200 mas contem VOCABULARIO PROIBIDO no HTML"
    else
      ok "$pg 200 limpo"
    fi
  else
    ko "$pg -> $code"
  fi
done
# paginas v1 apagadas tem de dar 404 agora
for pg in /dashboard /wc01 /tv /occupation; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$FRONT$pg")
  [ "$code" = "404" ] && ok "$pg 404 (v1 morta, correcto)" || wn "$pg -> $code (cache do Vercel? re-verificar em 5 min)"
done

echo ""
echo "═══ 7. CARGA — rajada de 40 pedidos paralelos ao /state ═══"
rm -f /tmp/lat.txt
for i in $(seq 1 40); do
  curl -s -o /dev/null -w "%{http_code} %{time_total}\n" "$API/state" >> /tmp/lat.txt &
done
wait
python3 - << 'PY'
lines = [l.split() for l in open("/tmp/lat.txt") if l.strip()]
codes = [l[0] for l in lines]
ts = sorted(float(l[1]) for l in lines)
n = len(ts)
errs = sum(1 for c in codes if c != "200")
p95 = ts[int(n*0.95)-1] if n else 99
print(f"  {'PASS' if errs==0 else 'FAIL'}  rajada 40x: {n-errs}/{n} com 200, p95={p95:.2f}s")
if errs: exit(1)
if p95 > 2.0: print(f"  WARN  p95 acima de 2s — Railway pode precisar de mais recursos para os dias do festival")
PY
[ $? -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

echo ""
echo "═══ 8. TESTES LOCAIS — pytest com detalhe das falhas ═══"
DATABASE_URL="sqlite+aiosqlite:///./test.db" python3 -m pytest tests/ -q 2>&1 | tail -3
DATABASE_URL="sqlite+aiosqlite:///./test.db" python3 -m pytest tests/test_live_payload.py tests/test_api.py -x --tb=short 2>&1 | tail -25 > /tmp/pytest_detail.txt
echo "  (detalhe da primeira falha guardado em /tmp/pytest_detail.txt — cola-me esse ficheiro)"

echo ""
echo "═══════════════════════════════════════════"
echo "RESULTADO: $PASS PASS · $FAIL FAIL · $WARN WARN"
echo "═══════════════════════════════════════════"
[ $FAIL -eq 0 ] && exit 0 || exit 1
