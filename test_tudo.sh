#!/bin/bash
# Teste end-to-end completo da API PlantaOS.
# Roda contra api.plantarockinrio.com (producao).
# Imprime resumo final OK/FALHA.

API="https://api.plantarockinrio.com/api/v1"
TS=$(date +%s)
PASS=0; FAIL=0
declare -a LOG

check() {
  local name="$1"; local cmd="$2"; local check="$3"
  local out; out=$(eval "$cmd" 2>&1)
  if echo "$out" | grep -qE "$check"; then
    PASS=$((PASS+1)); LOG+=("OK   $name")
  else
    FAIL=$((FAIL+1)); LOG+=("FAIL $name -> $(echo "$out" | head -c 120)")
  fi
}

echo "═══ TESTE END-TO-END PlantaOS — $(date +%H:%M:%S) ═══"
echo

echo "─── 1. AMBIENTES base ───"
check "GET /envs lista" \
  "curl -s '$API/envs'" \
  "rock-in-rio"

check "Rock in Rio fixo com 78" \
  "curl -s '$API/envs/rock-in-rio'" \
  '"n_sensores":\s*78'

echo "─── 2. CRIAR 3 ambientes novos ───"
check "criar Bancada A" \
  "curl -s -X POST '$API/envs' -H 'Content-Type: application/json' -d '{\"nome\":\"Bancada A '$TS'\",\"modo\":\"sim\",\"refresh_ms\":1000}'" \
  '"id":'

check "criar Bancada B" \
  "curl -s -X POST '$API/envs' -H 'Content-Type: application/json' -d '{\"nome\":\"Bancada B '$TS'\",\"modo\":\"sim\",\"refresh_ms\":1500}'" \
  '"id":'

check "criar Demo Staff" \
  "curl -s -X POST '$API/envs' -H 'Content-Type: application/json' -d '{\"nome\":\"Demo Staff '$TS'\",\"modo\":\"real\",\"refresh_ms\":2000}'" \
  '"id":'

ENV_A=$(curl -s "$API/envs" | python3 -c "import sys,json; d=json.load(sys.stdin); print([e['id'] for e in d['envs'] if 'bancada-a-$TS' in e['id']][0])")
ENV_B=$(curl -s "$API/envs" | python3 -c "import sys,json; d=json.load(sys.stdin); print([e['id'] for e in d['envs'] if 'bancada-b-$TS' in e['id']][0])")
ENV_S=$(curl -s "$API/envs" | python3 -c "import sys,json; d=json.load(sys.stdin); print([e['id'] for e in d['envs'] if 'demo-staff-$TS' in e['id']][0])")
echo "  IDs: $ENV_A · $ENV_B · $ENV_S"

echo "─── 3. ADICIONAR sensores aos novos ambientes ───"
check "add LilyGo a $ENV_A" \
  "curl -s -X POST '$API/envs/$ENV_A/sensors' -H 'Content-Type: application/json' -d '{\"id\":\"lab-lilygo-1\",\"tipo\":\"lilygo\",\"label\":\"LilyGo principal\"}'" \
  'lab-lilygo-1'

check "add Camara a $ENV_A" \
  "curl -s -X POST '$API/envs/$ENV_A/sensors' -H 'Content-Type: application/json' -d '{\"id\":\"lab-cam-1\",\"tipo\":\"camera\",\"label\":\"Camara teste\"}'" \
  'lab-cam-1'

check "add 3 IR a $ENV_B" \
  "curl -s -X POST '$API/envs/$ENV_B/sensors' -H 'Content-Type: application/json' -d '{\"id\":\"lab-ir-1\",\"tipo\":\"ir\",\"label\":\"IR 1\"}'" \
  'lab-ir-1'
curl -s -X POST "$API/envs/$ENV_B/sensors" -H 'Content-Type: application/json' -d '{"id":"lab-ir-2","tipo":"ir","label":"IR 2"}' > /dev/null
curl -s -X POST "$API/envs/$ENV_B/sensors" -H 'Content-Type: application/json' -d '{"id":"lab-ir-3","tipo":"ir","label":"IR 3"}' > /dev/null

check "add LilyGo de staff" \
  "curl -s -X POST '$API/envs/$ENV_S/sensors' -H 'Content-Type: application/json' -d '{\"id\":\"staff-wc-lilygo-1\",\"tipo\":\"lilygo\",\"label\":\"Staff WC LilyGo 1\"}'" \
  'staff-wc-lilygo-1'

echo "─── 4. LER FROTAS dos ambientes ───"
check "fleet $ENV_A (2 sensores)" \
  "curl -s '$API/envs/$ENV_A/fleet'" \
  '"total":\s*2'

check "fleet $ENV_B (4 sensores)" \
  "curl -s '$API/envs/$ENV_B/fleet'" \
  '"total":\s*4'

check "fleet rock-in-rio (78)" \
  "curl -s '$API/envs/rock-in-rio/fleet'" \
  '"total":\s*78'

echo "─── 5. REMOVER sensor (Bancada A: tira a Camara) ───"
check "remove lab-cam-1" \
  "curl -s -X DELETE '$API/envs/$ENV_A/sensors/lab-cam-1'" \
  '"removed":\s*true'

check "$ENV_A agora tem 1 sensor" \
  "curl -s '$API/envs/$ENV_A/fleet'" \
  '"total":\s*1'

echo "─── 6. TENTAR mexer no Rock in Rio (deve falhar) ───"
check "delete rock-in-rio NEGADO" \
  "curl -s -X DELETE '$API/envs/rock-in-rio'" \
  'nao e possivel|nao é possivel'

check "add sensor a rock-in-rio NEGADO" \
  "curl -s -X POST '$API/envs/rock-in-rio/sensors' -H 'Content-Type: application/json' -d '{\"id\":\"x\",\"tipo\":\"lilygo\"}'" \
  'nao adicionado|fixo'

echo "─── 7. COMANDOS de sensor (sensorctl) ───"
check "ping wc-01-lilygo-1" \
  "curl -s -X POST '$API/sensorctl/wc-01-lilygo-1/cmd' -H 'Content-Type: application/json' -d '{\"cmd\":\"ping\"}'" \
  'pong'

check "diagnostico wc-06-cam-1 (OAK 4 D)" \
  "curl -s '$API/sensorctl/wc-06-cam-1/diagnostics'" \
  'OAK 4 D|modelo'

check "detalhe lab-lilygo-1 (custom)" \
  "curl -s '$API/sensorctl/lab-lilygo-1'" \
  '"id"'

echo "─── 8. FUSAO dos 8 clusters ───"
for cid in wc-01 wc-02 wc-03 wc-04 wc-05 wc-06 wc-07 wc-08; do
  check "fusion $cid" \
    "curl -s '$API/fusion/$cid?mode=sim'" \
    '"estado":\s*"ok"'
done

echo "─── 9. ALERTAS e CONTRAFACTUAIS ───"
check "GET /alerts" \
  "curl -s '$API/alerts'" \
  'sumario'

check "POST close_cluster wc-05" \
  "curl -s -X POST '$API/counterfactual' -H 'Content-Type: application/json' -d '{\"cluster\":\"wc-05\",\"cenario\":\"close_cluster\"}'" \
  'recomendacao'

check "POST surge_concert wc-02" \
  "curl -s -X POST '$API/counterfactual' -H 'Content-Type: application/json' -d '{\"cluster\":\"wc-02\",\"cenario\":\"surge_concert\",\"params\":{\"multiplicador\":1.8}}'" \
  'simulado'

echo "─── 10. PERFIL DO FESTIVAL ───"
check "GET /festival/days (4 dias)" \
  "curl -s '$API/festival/days'" \
  'Katy Perry'

check "GET /festival/pressure 21-06 23h" \
  "curl -s '$API/festival/pressure?day=21-06&h=23'" \
  'CRITICA|pressao_relativa'

echo "─── 11. LIMPEZA: apagar ambientes de teste ───"
check "delete $ENV_A" \
  "curl -s -X DELETE '$API/envs/$ENV_A'" \
  '"deleted"'
check "delete $ENV_B" \
  "curl -s -X DELETE '$API/envs/$ENV_B'" \
  '"deleted"'
check "delete $ENV_S" \
  "curl -s -X DELETE '$API/envs/$ENV_S'" \
  '"deleted"'

echo
echo "═══════════ RESUMO ═══════════"
for line in "${LOG[@]}"; do echo "$line"; done
echo "──────────────────────────────"
echo "PASS: $PASS · FAIL: $FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "✓ TUDO A FUNCIONAR"
else
  echo "✗ HA FALHAS — ver acima"
fi
