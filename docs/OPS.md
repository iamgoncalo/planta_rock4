# OPS.md

> **Runbook diário** durante Rock in Rio Lisboa 2026 · Parque Tejo  
> 20, 21, 27, 28 Junho 2026

---

## 1. Quem está de turno

| Dia | Primary on-call | Backup |
|---|---|---|
| 20 Jun (Sáb) | Gonçalo Melo | — |
| 21 Jun (Dom) | Gonçalo Melo | — |
| 27 Jun (Sáb) | Gonçalo Melo | — |
| 28 Jun (Dom) | Gonçalo Melo | — |

**Contactos**:
- Planta CEO — `hi@planta.design` · WhatsApp privado
- Rock World COO Ricardo Acto — `ricardoacto@rockinrio.com`
- Rock World Operações Matheus — `matheuszanin@rockinrio.com`

---

## 2. Horário operacional por dia

```
06:00  Inspeção do site + UPS dos edge nodes
09:00  Cleaning briefing — 8 pessoas Prosegur
12:00  Briefing geral CCO (auditório)
13:45  Sistema online + smoke test
14:00  Doors open — começa o telemetria-stream
17:00  Heat alert se T > 28°C
19:30  Pre-show monitoring intensivo
22:00  Headliner — alta densidade
23:30  Pre-position equipas para egress
01:00  Peak exit ~40 000/h
03:00  Site clear + relatório dia
```

---

## 3. Dashboards a abrir

Em laptop no CCO (Centro Coordenação Operacional):

1. **`/v2`** — visão geral, KPIs, 8 clusters live
2. **`/v2/operations`** — alertas activos + redirecionamentos
3. **`/v2/cleaning`** — próxima limpeza por cluster
4. **`/v2/incidents`** — incidentes em curso

No telefone (Gonçalo):

1. **`/v2`** em PWA (instalar antes do dia 20)
2. **`/v2/chat`** — Gemini fala sobre estado actual

---

## 4. Alertas e respostas

### Alert: Cluster com ocupação > 90%

**O que ver na UI**: cor amber `#C25A1A` no cluster card + pill `CRÍTICO`.

**Acção**:
1. Verificar em `/v2/operations` se ACO já está a redirecionar.
2. Se sim, comunicar a Matheus (Rock World) por WhatsApp:
   > "WC-{ID} em {OCC}% — staff a redirecionar para WC-{ID_alvo}"
3. Se não, ajustar manualmente em `/v2/route`.

### Alert: Sensor offline > 30 min

**O que ver**: badge `offline` no sensor em `/v2/sensors`.

**Acção**:
1. Avisar Flinotech (Francisco Lino) para inspecção.
2. Verificar em `/v2/operations` que o cluster ainda tem cobertura > 60%.
3. Se cobertura cair, alertar Matheus para steward no local.

### Alert: API caída (5xx em > 30 reqs/min)

**Sinal**: `/v2` mostra "A LIGAR" em vez de "STREAM AO SEGUNDO".

**Acção**:
1. `railway logs --service planta_rock4 | tail -50`
2. Se crash → `railway redeploy` ou rollback.
3. Se DB → verificar Postgres health no painel Railway.
4. Frontend continua a funcionar com último estado em cache.

### Alert: 4G NOS dropped

**Sinal**: latência aumenta em `/v2`. SCOR pára de receber telemetria.

**Acção**:
1. Failover automático para Vodafone deve activar em < 5s.
2. Se não, ligar via WiFi do venue como Layer 3.
3. Avisar Francisco para troca de SIM se persistir.

---

## 5. Cleaning workflow

8 pessoas Prosegur em 2 turnos:

| Turno | Horário | Supervisor | Equipa |
|---|---|---|---|
| Tarde | 14:00–22:00 | Maria Silva (+351 962 145 778) | João Costa, Ana Pereira, Rui Mendes |
| Noite | 22:00–06:00 | Carla Fonseca (+351 935 776 102) | Pedro Antunes, Sofia Reis, Tiago Marques |

**Cadência**: 1 limpeza por cluster por hora, slot de 8 min, round-robin.

**Aplicação a usar**: `/v2/cleaning` no telefone Prosegur.

**Quando se desvia do plano**:
- Em `/v2/cleaning` → click no cluster → "Marcar limpeza"
- Sistema regista timestamp + pessoa
- Próxima limpeza é recalculada

---

## 6. Comandos rápidos no terminal

### Estado geral
```bash
# Health do backend
curl https://api.plantarockinrio.com/api/v1/health

# Snapshot agora
curl https://api.plantarockinrio.com/api/v1/telemetry/clusters/now | jq '.kpis'

# Últimos 3 deploys Vercel
vercel ls 2>&1 | head -5

# Últimos logs Railway (tail-30)
railway logs --service planta_rock4 2>&1 | tail -30
```

### Forçar refresh do CDN
```bash
# Vercel cache bust
vercel --prod
```

### Adicionar alerta manualmente
```bash
curl -X POST https://api.plantarockinrio.com/api/v1/alerts \
  -H "content-type: application/json" \
  -H "authorization: Bearer $JWT" \
  -d '{"cluster_id": "WC-04", "severity": "warning", "message": "Verificar fluxo"}'
```

---

## 7. Comunicações com Rock World

### Canal primário
**WhatsApp grupo** "Rock in Rio LX26 · Smart Operations":
- Gonçalo (Planta)
- Ricardo Acto (COO)
- Matheus Zanin (Ops)
- Bernardo Lorga, Fernanda Trostdorf, Anna Pinheiro

### Templates

**Início do dia (12:00)**:
> Dia {N}/4 do festival. Sistema online. 8 clusters a reportar.
> KPIs em www.plantarockinrio.com/v2. Estou disponível.

**Alert (durante o dia)**:
> ⚠️ WC-{ID} em {OCC}% — redirecionamento activo para WC-{ALT}.
> Sugiro 1 steward extra junto à entrada de WC-{ID}.

**Fim do dia (03:00)**:
> Dia {N} encerrado. Pessoas servidas: {N_total}.
> Pico {HH:MM} com {N_pico}/min. 0 incidentes críticos.
> Relatório detalhado amanhã.

---

## 8. Critérios de escalação

### Verde (continuar)
- Ocupação média < 70%
- 0 sensores offline
- 0 alertas criticos

### Amber (atenção)
- Ocupação cluster > 80% em qualquer momento
- 1–2 sensores offline (cobertura ainda > 80%)
- 1–3 alertas activos

**Acção**: avisar Matheus por WhatsApp.

### Critical (escalar)
- Cluster > 95% durante > 10 min
- ≥ 3 sensores offline (cobertura cluster < 60%)
- API caída > 2 min
- Incidente reportado por Prosegur

**Acção**: chamar Ricardo Acto + ir ao CCO.

---

## 9. Lições de simulação (não repetir)

Aprendido em testing:

- **Pico real é mais cedo que esperado**: começar monitoring intensivo às
  19:00, não 20:00.
- **Pós-show surge dura 25 min**, não 15.
- **WC-04** (mais distante do palco) recebe menos do que se esperaria.
  Considerar redirecionamento manual ACO se sub-utilizado.
- **WC-05/06 UNISSEX** absorvem melhor o pico que separados M/F.
- **Cleaning a meio da hora** (não no minuto 0) reduz colisão com fluxos.

---

## 10. Anexos

- [`PRODUCT.md`](PRODUCT.md) — 14 secções, KPIs SCOR
- [`SENSORS.md`](SENSORS.md) — 62 dispositivos, cobertura, manutenção
- [`DEPLOY.md`](DEPLOY.md) — comandos Vercel + Railway
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — 3-layer real-time strategy
- [`DESIGN.md`](DESIGN.md) — design system
