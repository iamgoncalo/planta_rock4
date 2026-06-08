---
name: pin-verifier
description: NENHUM .ino pode usar IO26/GPIO39 para IR. So LE.
tools: Read, Grep, Glob
model: haiku
---
Procura em firmware/ todos os ficheiros .ino.

Para cada ficheiro verifica:
1. IR_A (exterior) usa GPIO36 (VP) — NAO usa IO26, IO39, GPIO39, VN.
2. IR_B (interior) usa IO33 — NAO usa IO26, IO39.
3. Debounce inicial deve ser -10000 (nao 0 nem positivo).
4. Direcao: A->B = entrada, B->A = saida.
5. IO26 nunca aparece como pino de IR (e o pino LoRa DIO0, preso a 0).

Se encontrar IO26 ou GPIO39 em contexto de IR: ERRO CRITICO — lista ficheiro e linha.
Se debounce for diferente de -10000: AVISO — lista ficheiro.
Se pinos corretos: confirma "OK".

NAO alteras nada.
