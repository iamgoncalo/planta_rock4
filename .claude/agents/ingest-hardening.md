---
name: ingest-hardening
description: Adiciona validacao e token ao /ingest. ALTERA backend.
tools: Read, Edit, Bash
model: sonnet
---
No /ingest: valida cluster_id com regex ^wc-0[1-8]_[mfu]$ (rejeita 422 se invalido).
Aceita header X-Ingest-Token comparado a os.getenv('INGEST_TOKEN'); se a env existir
e o token nao bater, 401. Se a env nao existir, deixa passar (compat). Nao quebrar placas.
