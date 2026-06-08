---
name: install-page
description: /v2/install SEM scroll, mostra TODAS as fontes por cluster online/offline em tempo real. Wow. ALTERA frontend.
tools: Read, Write, Edit, Bash
model: sonnet
---
Cria frontend/app/v2/install/page.tsx — pagina de instalacao/monitorizacao de hardware.

LAYOUT (SEM SCROLL — position:fixed, overflow:hidden, 100dvh):
  - TopBar 72px (ja existe globalmente)
  - Barra de estado: N fontes online / total, ultima atualizacao, dot LIVE/POLL
  - Grid de clusters (8 clusters, 2 colunas) — cada card tem:
    Para clusters M/F (wc-01,02,03,04,07,08): 7 fontes por cluster:
      LLH (IR + paxcount), LRH (IR + paxcount), LLW (IR + paxcount), LRW (IR + paxcount),
      LC (so paxcount), Luxonis, Prosegur
    Para unissexo (wc-05,06): 3 fontes:
      UNI-A (paxcount), UNI-B (paxcount), Prosegur

CADA FONTE mostra:
  - Bolinha de status: verde (#2E7D4F) = online (sinal < 5 min), cinzento (#B7B9B0) = offline
  - Nome da fonte (ex: "LLH", "Luxonis", "Prosegur")
  - Tipo: IR/paxcount/camera_ml/prosegur
  - Ultimo sinal: "Xx min atras" ou "nunca"
  - Confianca da fusao desse cluster: X%
  - Ao clicar numa fonte LilyGo: painel lateral desliza com:
    - CLUSTER_ID e PORTA
    - Pinos: A=GPIO36 B=IO33
    - Snippet do cabecalho do .ino correspondente (para copiar)
    - Teste ao vivo: mostra ultimos valores (entradas/saidas se IR, pessoas se paxcount)

DADOS: Le de GET /api/v1/sensors (lista de sensores com ts_last, status, cluster_id).
       Complementa com GET /api/v1/flow (confianca por secao).
       Poll a cada 10s.

ANIMACAO WOW:
  - Bolinhas pulsam suavemente quando online (keyframe pulse com box-shadow verde)
  - Cards com sinal recente (< 30s) tem borda esquerda verde animada
  - Transicao de offline->online: bolinha "pop" scale 1.4->1.0 durante 300ms
  - Fundo: #FAFAF8 (bg-soft), sem vermelho, ambar #C25A1A so para critico

REGRAS:
  - Sem SIMULADO visivel
  - Ambar (#C25A1A) nunca vermelho
  - SEM SCROLL (position:fixed ou flex com overflow:hidden)
  - Design consistente com /v2/flow (Inter, variaveis CSS --ink --muted --green)
  - Testar npm run build antes de reportar concluido

Le: app/routers/sensors.py, frontend/app/v2/flow/page.tsx (para padrao de layout),
    frontend/app/globals.css ou v2.css (variaveis CSS existentes).
