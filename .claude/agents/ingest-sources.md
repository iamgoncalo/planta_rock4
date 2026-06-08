---
name: ingest-sources
description: Garante que /ingest aceita Luxonis e Prosegur (campo fonte=) e a fusao usa-os. ALTERA backend.
tools: Read, Edit, Bash
model: sonnet
---
Objetivo: Luxonis OAK e Prosegur enviam POST /api/v1/ingest com campo "fonte":"luxonis"
ou "fonte":"prosegur". O backend deve mapear isso para os campos corretos de FusionInput.

Le app/routers/ingest.py e app/fusion.py.

Verificar e corrigir:
1. IngestParams (Pydantic) tem campo opcional "fonte: str = 'lilygo'".
2. Quando fonte=="luxonis": o campo "contagem_prosegur" (ou campo dedicado) mapeia para
   FusionInput.luxonis_count.
3. Quando fonte=="prosegur": mapeia para FusionInput.contagem_prosegur.
4. Quando fonte=="lilygo": comportamento atual (entradas_ir, saidas_ir, pessoas_estimadas).
5. Regex cluster_id aceita: ^wc-0[1-8]-[mfcu]$ (inclui -u para unissexo).
6. O endpoint nao retorna 500 para nenhum destes casos — usa upsert seguro.

Apos as alteracoes corre: python3 -m pytest tests/ -q -x para confirmar nao quebrou nada.

Faz commit com mensagem clara. NAO toca em frontend.
