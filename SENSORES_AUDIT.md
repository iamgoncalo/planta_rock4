# SENSORES_AUDIT.md
## PlantaOS · Rock in Rio Lisboa 2026 · FASE 1 — Auditoria Paralela
**Data**: 2026-06-08 | **Agentes**: fusion-auditor + arch-auditor + pin-verifier

---

## TL;DR — O QUE ESTÁ MAL (por prioridade)

| # | Problema | Severidade | Ficheiro |
|---|---|---|---|
| 1 | GPIO26 usado como pino IR no firmware v6 (LoRa DIO0 — preso a 0) | CRÍTICO | firmware/rockinrio_v6/rockinrio_v6.ino |
| 2 | Pinos IR firmware: GPIO13/14/26/27 em vez de **GPIO36/IO33** | CRÍTICO | firmware/rockinrio_v6/rockinrio_v6.ino |
| 3 | Debounce firmware: 200ms em vez de **−10000** | CRÍTICO | firmware/rockinrio_v6/rockinrio_v6.ino |
| 4 | Campo `"fonte"` ausente no `/ingest` — impossível distinguir Luxonis de WiFi | CRÍTICO | app/routers/ingest.py |
| 5 | Campo `"porta"` ausente em IngestParams — LLH/LRH/LLW/LRW indistinguíveis | CRÍTICO | app/routers/ingest.py |
| 6 | `ingest_store.put()` sobrescreve — 4 POSTs do mesmo cluster destroem-se mutuamente | CRÍTICO | app/services/ingest_store.py |
| 7 | Regex cluster_id `^wc-0[1-8]$` rejeita `wc-01-m`, `wc-01-f`, `wc-01-c`, `wc-05-u` | CRÍTICO | app/sensors_topology.py + clusters_capacity.py |
| 8 | `LC` (center, wc-0X-c) seria rejeitado com 422 | ALTA | app/routers/ingest.py |

---

## O QUE ESTÁ BEM

| Item | Status |
|---|---|
| Pesos base IR=0.50 / WiFi=0.30 / Cam=0.20 | ✅ PASS |
| Prosegur como âncora (drift correction + confidence) — não entra no weighted sum | ✅ PASS |
| Fonte offline → peso 0, redistribuição, nunca ÷0 (I-4) | ✅ PASS |
| `FusionInput.luxonis_count` existe e entra como "cam" | ✅ PASS |
| `FusionInput.contagem_prosegur` existe e é guardado | ✅ PASS |
| confiança ∈ [0,1] sempre — invariante I-5 | ✅ PASS |
| `USAR_IR=False` para wc-05 e wc-06 | ✅ PASS |
| Watchdog 6 falhas (firmware staff) | ✅ PASS |
| WiFi `setAutoReconnect`, sem `esp_wifi_deinit` (firmware staff) | ✅ PASS |

---

## DETALHE POR AGENTE

### 1 · FUSION-AUDITOR

**CRÍTICO — Campo `fonte` ausente no `/ingest`**

`IngestParams` não tem campo `fonte`. O endpoint aceita `extra="allow"`, mas ignora-o.
Consequência: se Luxonis enviar POST com `fonte=luxonis`, os dados caem em `pessoas_estimadas`
e são tratados como WiFi — não são roteados para `FusionInput.luxonis_count`.

**O que falta (2 linhas de código):**
```python
# app/routers/ingest.py — adicionar a IngestParams:
fonte: Optional[str] = "lilygo"   # "lilygo" | "luxonis" | "prosegur"

# E em _run_fusion / fuse_section:
if params.get("fonte") == "luxonis":
    fi.luxonis_count = params.get("pessoas_estimadas")
```

**Tudo o resto na fusão está correto.** Prosegur já entra como âncora. IR/WiFi redistribuem peso. I-5 garantido.

---

### 2 · ARCH-AUDITOR

**4 problemas críticos de arquitectura:**

**A — Campo "porta" ausente**
Os 4 LilyGo com IR enviam porta (`"LL"` ou `"LR"`). O backend não guarda nem usa este campo.
Sem porta, é impossível saber qual das duas portas de um corredor registou as entradas.

**B — ingest_store sobrescreve (não acumula)**
```python
# app/services/ingest_store.py linha 20
_STORE[cid] = {...}   # ← SOBRESCREVE o POST anterior
```
Se LLH e LRH enviarem para o mesmo `cluster_id` com ~1s de diferença,
o segundo POST destrói o primeiro. O backend vê apenas o último LilyGo.

**Solução proposta:**
```python
# ingest_store deve acumular IR por porta:
_STORE[cid]["portas"][porta] = {ir_data}
# e expor: sum(p["entradas_ir"] for p in portas.values())
```

**C — Regex incompatível com campo**
- Backend: `CLUSTER_ID_RE = r"^wc-0[1-8]$"` + `ALL_CLUSTERS = ["wc-01".."wc-08"]`
- Campo: firmware enviará `wc-01-m`, `wc-01-f`, `wc-01-c`, `wc-05-u`
- Qualquer POST com sufixo → **HTTP 422**

**D — Ponto único de decisão**
Há duas opções de design (a decidir antes de implementar):

| Opção | Descrição | Prós | Contras |
|---|---|---|---|
| **A** (recomendada) | Firmware envia `cluster_id="wc-01"` + `porta="LL"` + `secao="m"/"f"/"u"` | Mantém regex simples, só muda ingest_store | Requer campo `porta` e `secao` |
| **B** | Firmware envia `cluster_id="wc-01-m"` diretamente | Mais simples no firmware | Precisa expandir regex, ALL_CLUSTERS, fusão |

**Status único que é PASS:** `USAR_IR=False` para wc-05/06 — correto e bem implementado.

---

### 3 · PIN-VERIFIER

**ERROS CRÍTICOS no firmware existente (`firmware/rockinrio_v6/rockinrio_v6.ino`):**

| Pino | Spec correta | Encontrado no v6 | Status |
|---|---|---|---|
| IR_A (exterior) | **GPIO36 (VP)** | GPIO13 / GPIO14 | ❌ ERRADO |
| IR_B (interior) | **IO33** | GPIO26 / GPIO27 | ❌ ERRADO |
| IO26 como IR | **PROIBIDO** (LoRa DIO0) | IR3_SAI_INT = GPIO26 | ❌ ERRO CRÍTICO |
| Debounce | **-10000** | 200ms (positivo) | ❌ ERRADO |

**Nota importante:** O ficheiro `rockinrio_v6.ino` é o firmware de staff (casas de banho de pessoal),
com arquitetura diferente. **Os novos .ino para WC do festival (firmware/rir2026/) ainda não existem.**
O gerador (ino-template + ino-generator-mf) vai criar os ficheiros corretos com GPIO36/IO33.

---

## PLANO DE CORREÇÃO (para FASE 2+)

```
FASE 2 — FUSÃO + INGEST (backend, ingest-sources):
  [1] Adicionar campo fonte: Optional[str] = "lilygo" a IngestParams
  [2] Adicionar campo porta: Optional[str] = None a IngestParams
  [3] Adicionar campo secao: Optional[str] = None a IngestParams (se opção A)
  [4] Refatorar ingest_store.put() para acumular IR por porta (não sobrescrever)
  [5] Rotear fonte=luxonis → FusionInput.luxonis_count
  [6] Rotear fonte=prosegur → FusionInput.contagem_prosegur
  [7] Expandir regex e ALL_CLUSTERS para aceitar variantes -m/-f/-c/-u
      (ou manter ^wc-0[1-8]$ e resolver via porta+secao — decisão de design A vs B)
  [8] pytest -q para confirmar que nada quebrou

FASE 3 — FIRMWARE (ino-template → ino-generator-mf → ino-generator-uni):
  [9]  Criar firmware/rir2026/_TEMPLATE.ino com GPIO36/IO33, debounce=-10000
  [10] Gerar 30 .ino M/F (wc-01,02,03,04,07,08 × LLH/LRH/LLW/LRW/LC)
  [11] Gerar 4 .ino unissexo (wc-05-u × 2, wc-06-u × 2)

FASE 4 — PÁGINA /install (install-page):
  [12] frontend/app/v2/install/page.tsx — fontes online/offline, wow, sem scroll
```

---

## DECISÃO NECESSÁRIA ANTES DE FASE 2

> **Opção A (recomendada):** Firmware envia `cluster_id="wc-01"` (sem sufixo) + campo `"porta"` ("LL"/"LR"/"C") + campo `"secao"` ("m"/"f"/"u"). Backend mantém regex simples, acumula por porta.
>
> **Opção B:** Firmware envia `cluster_id="wc-01-m"` diretamente. Backend expande regex e ALL_CLUSTERS. Mais mudanças no backend.

Aguardo aprovação para prosseguir para FASE 2.
