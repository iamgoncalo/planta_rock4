# PlantaOS · Rock in Rio Lisboa 2026

> Recomendador inteligente de WC ao segundo para 100 000 pessoas/dia no Parque Tejo.

---

## 🌱 O que faz

Para cada pessoa no Rock in Rio Lisboa, recomendamos **o caminho mais rápido,
leve e seguro até uma casa-de-banho disponível, agora**.

Sem pensar em algoritmos. Sem pensar em sensores. **Sem stress**.

---

## 📍 Onde correr

| | |
|---|---|
| Site | [www.plantarockinrio.com](https://www.plantarockinrio.com/v2) |
| API | [api.plantarockinrio.com](https://api.plantarockinrio.com/api/v1/health) |
| Repo | [github.com/iamgoncalo/planta_rock4](https://github.com/iamgoncalo/planta_rock4) |
| Dates | 20, 21, 27, 28 Junho 2026 |

---

## ⚡ Comandos rápidos

```bash
# Setup
git clone https://github.com/iamgoncalo/planta_rock4.git
cd planta_rock4/frontend && npm install && npm run dev

# Backend
cd .. && pip install -r requirements.txt
uvicorn app.main:app --reload

# Deploy (auto via git push)
git push origin main
```

---

## 📖 Documentação

| | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | **Contexto master** para Claude/Cursor/qualquer agente |
| [`docs/PRODUCT.md`](docs/PRODUCT.md) | O que é, para quem, KPIs SCOR |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Stack, real-time, redundância |
| [`docs/SENSORS.md`](docs/SENSORS.md) | 62 dispositivos físicos, fusão sensorial |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Design system Oxman editorial |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Vercel + Railway + troubleshooting |
| [`docs/OPS.md`](docs/OPS.md) | Runbook diário Junho 2026 |

---

## 🔧 Stack

- **Frontend**: Next.js 14 + TypeScript + Inter sans-serif · Vercel
- **Backend**: FastAPI Python 3.11 + PostgreSQL + Redis + MQTT · Railway
- **Edge**: 16 IR · 11 WiFi 6E · 5 OAK-D · 2 LoRa GW · 2 4G Hub · 2 RPi 5 · 24 Reed
- **LLM**: Gemini 2.5 Flash

---

## 🚫 Não-objectivos

- ❌ Tracking individual (MAC, rosto)
- ❌ Medições ambientais (CO₂, T, RH)
- ❌ Cor vermelha em alertas (usar `#C25A1A`)
- ❌ Vocabulário académico no UI

Detalhes em [`CLAUDE.md`](CLAUDE.md).

---

## 📧 Contacto

Gonçalo Melo de Magalhães · `hi@planta.design`  
Planta Smart Homes · Porto, Portugal

> _"I design to free."_
