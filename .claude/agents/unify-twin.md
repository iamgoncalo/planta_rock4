---
name: unify-twin
description: Um só digital twin. Apaga frontend/app/twin (antigo), fica v2/twin. ALTERA frontend.
tools: Read, Edit, Bash
model: sonnet
---

v2/twin é o twin correto e actual. frontend/app/twin é o antigo e deve ser apagado.

Passos:
1. Confirmar que v2/twin/page.tsx está funcional (não é vazio/stub)
2. Verificar que nenhum link em produção aponta para /twin (só /v2/twin)
3. rm -rf frontend/app/twin
4. npm run build → verde

Confirmar que TopBar e qualquer outro ficheiro de navegação só tem /v2/twin.
