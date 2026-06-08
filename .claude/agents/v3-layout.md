---
name: v3-layout
description: Criar /v3 com tema RiR (branco, azul #0A6CFF, rosa #FF2E93 raro, âmbar crítico). ALTERA frontend.
tools: Read, Edit, Write, Bash
model: sonnet
---

APENAS DEPOIS da unificação estar completa (audit-unified verde).

Criar frontend/app/v3/layout.tsx e frontend/app/v3/v3.css:
- Fundo branco #FFFFFF · Tinta #0D1117 · Cinza #5A6470 · Linha #E6E9EE
- Azul RiR #0A6CFF (acento principal, CTA, activo)
- Rosa RiR #FF2E93 (raro — máximo 1 por ecrã, só para destaques especiais)
- Crítico âmbar #C25A1A (NUNCA vermelho)
- Inter + DM Mono, clamp(), muito espaço branco
- TopBar v3 com links para as 8 páginas /v3
- PlantaSearchBar v3 em baixo (botão azul #0A6CFF)
- Cada página: 100svh, sem scroll (position:fixed)
- v2 INTACTA — não tocar em nada do v2

npm run build verde antes de commitar.
