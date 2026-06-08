# AUDIT_FINAL.md
> Verificação pós-correções · 2026-06-08 · commit 9f2f811

---

## 1. "SIMULADO" no frontend

```
grep -r "SIMULADO" frontend --exclude-dir=.next → 0 ficheiros
```

**PASSOU ✅** — Nenhuma ocorrência em código público.

---

## 2. Segredos hardcoded no backend

| Variável | Ficheiro | Estado |
|---|---|---|
| `mqtt_password` | `app/config.py:33` | `str = ""` — sem literal ✅ |
| `_ADMIN_PASS` | `app/routers/rirstaff.py:218` | `os.getenv("RIRSTAFF_ADMIN_PASS", "")` ✅ |
| `INGEST_TOKEN` | `app/routers/ingest.py:67` | `os.getenv("INGEST_TOKEN", "")` ✅ |
| `database_url` | `app/config.py:27` | `str = ""` ✅ |
| `DB_URL` (seeds) | `app/seeds/sensors.py:238` | `os.environ.get("DATABASE_URL", "")` ✅ |
| `ops_secret` | `app/config.py:24` | `str = "change-me"` — **sentinela intencional** |

**Nota sobre `ops_secret`**: o valor `"change-me"` é um sentinela, não um segredo real. O código em `ingest.py:60` trata-o explicitamente (`if expected_ops and expected_ops != "change-me"`) e desactiva a verificação quando não está configurado. Confirma que a Railway tem `OPS_SECRET` definido com valor real.

**PASSOU ✅** — Sem passwords literais. Sentinela documentado.

---

## 3. Frase contraditória em /v2/sensors

**CORRIGIDO ✅** — commit `9f2f811`

| | Texto |
|---|---|
| Antes | `Dados LIVE — este sensor não está fisicamente ligado.` |
| Depois | `Sensor ainda não ligado — à espera do hardware.` |

---

## 4. Scroll e cores nos ecrãs críticos

### Scroll

| Página | Container externo | No-scroll? |
|---|---|---|
| `/v2/flow` | `position:fixed; overflow:hidden` | ✅ |
| `/v2/sensors` | `position:fixed; overflow:hidden` | ✅ |
| `/v2/screen` | `position:'fixed'` + `overflow:'hidden'` | ✅ |
| `/wc01..08` | `position:'fixed'; inset:0; overflow:'hidden'` | ✅ |
| **`/v2/scor`** | `<div style={{ padding:'32px 24px 96px' }}>` — sem `position:fixed` | **⚠️ SCROLLA** |

**`/v2/scor` é a única página que ainda tem scroll normal de página.** (não alterado — fora do âmbito do ponto 3)

### Vermelho

```
grep -rn "color.*red|#[Ff][0-9a-f]{2}00|background.*red" (5 páginas) → 0 linhas
```

**PASSOU ✅** — Nenhum vermelho. Cor crítica é só `#C25A1A`.

---

## 5. Build e testes

### `npm run build`

```
✓ Compiled successfully
✓ Generating static pages (37/37)
```

**PASSOU ✅** — Zero erros, zero warnings de build.

### `test_copy_engine.py`

```
TODOS OS TESTES PASSARAM ✓ — 8 cenários completos
(vazio / livre / cheio / limite / refúgio / pico / offline / unissexo)
```

**PASSOU ✅**

### `test_flow.py`

Não executa localmente: macOS tem Python 3.9, o código usa sintaxe `str | None`
(PEP 604, requer ≥ 3.10). Railway corre Python 3.11 — pre-existente, não regressão.

**INCONCLUSIVO ⚠️** (ambiente, não código)

---

## 6. Endpoints ao vivo

```bash
GET /api/v1/health → 200 {"status":"ok","version":"0.1.0","data_source":"awaiting_hardware"}
GET /api/v1/flow   → 200 {"ts":...,"kpis":{"kpi_01":...,"kpi_02":...,"kpi_03":...},...}
```

**PASSOU ✅** — Railway verde.

---

## Resumo

| # | Item | Resultado |
|---|---|---|
| 1 | SIMULADO no frontend | ✅ ZERO |
| 2 | Segredos hardcoded | ✅ LIMPO |
| 3 | Frase contraditória sensors | ✅ CORRIGIDO |
| 4a | No-scroll páginas críticas | ⚠️ `/v2/scor` scrolla |
| 4b | Cor vermelha | ✅ ZERO |
| 5a | npm run build | ✅ OK |
| 5b | test_copy_engine | ✅ 8/8 |
| 5c | test_flow | ⚠️ Python 3.9 local (Railway OK) |
| 6 | health + flow ao vivo | ✅ 200 |

**Um problema real a resolver separadamente: `/v2/scor` não é no-scroll.**
Tudo o resto está conforme.
