# PRODUCT.md

> **O que** o PlantaOS faz, **para quem**, e **como** se mede o sucesso.

---

## 1. Pitch

> Para cada pessoa no Rock in Rio Lisboa, recomendar o caminho mais rápido,
> leve e seguro até uma casa-de-banho disponível, **agora**.

Sem pensar em algoritmos. Sem pensar em sensores. **Sem stress**.
A pessoa abre o telefone, vê a sugestão, vai à casa-de-banho.
Volta ao concerto sem perder música.

---

## 2. Para quem

| Persona | Necessidade | Como o PlantaOS resolve |
|---|---|---|
| **Concertgoer** (~80 mil por dia) | Saber qual WC tem fila menor agora | Recomendação push + página web `/v2/route?to=me` |
| **Equipa Rock World** | Saber se há clusters em apuros | Dashboard `/v2` + Operações + Alertas |
| **Limpeza Prosegur (8 pessoas)** | Saber qual cluster precisa de atenção | `/v2/cleaning` com calendário preditivo |
| **Câmara de Lisboa** | Provar eficiência operacional | Relatórios diários + dados Smart City |
| **Investigação FCT/Deucalion** | Validar modelo empírico | Datasets anónimos exportados |

---

## 3. Capacidade operacional

| | Valor |
|---|---|
| **Capacidade** | 100 000 pessoas/dia × 4 dias = 400 000 pessoas |
| **Dias** | 20, 21, 27, 28 Junho 2026 |
| **Clusters WC** | 8 estruturas físicas (14 secções operacionais) |
| **Lugares totais** | 1 137 simultâneos (773 MASC + 364 FEM) |
| **Pessoas servidas** | ~75 000 idas/hora no pico (19:30–21:30) |

### 14 secções operacionais

```
WC-01_M  WC-01_F        # M+F separados
WC-02_M  WC-02_F        # M+F separados, FEM > MASC
WC-03_M  WC-03_F        # M+F separados, melhor F
WC-04_M  WC-04_F        # M+F separados, pior F (+20m altura)
WC-05    UNISSEX        # 133 lugares unissex
WC-06    UNISSEX        # 208 lugares unissex (maior)
WC-07_M  WC-07_F        # M servidos por 8 calhas (ZERO cabines individuais M)
WC-08_M  WC-08_F        # M+F separados, mais distante do palco
```

> **Importante**: WC-05 e WC-06 são **UNISSEX**. Os restantes têm M/F separados.
> A UI nunca expõe `FEM=0` para os unissex — mostra apenas "Unissex".

---

## 4. KPIs (SCOR / Sensaway)

Publicamos 4 KPIs em tempo real para SCOR:

| ID | Nome | Range | Onde mostrar |
|---|---|---|---|
| `kpi_01` | Flow Index | 0–100 | Home `/v2` |
| `kpi_02` | Avg WC Occupancy % | 0–100 | Home + Drawer mobile |
| `kpi_03` | Active Critical Alerts | inteiro | Home + Operações |
| `kpi_04` | People Redirected (daily) | inteiro | Operações + Pipelines |

### Tokens
```
KPI geral:           gGQhPd2c1kVqQjQglsmt
Cluster telemetry:   04614480-c43a-1f5f-af68-86c606bddb32
```

### Telemetria por minuto
Por cada uma das 14 secções, enviamos:
```json
{
  "cluster_id": "WC-01_M",
  "fila_actual": 3,
  "tempo_espera_min": 4,
  "fluxo_entrada_pmin": 12,
  "ocupacao_pct": 72
}
```

---

## 5. Funcionalidades

### Páginas activas (`/v2/*`)

| Página | URL | Função |
|---|---|---|
| **Início** | `/v2` | Hero editorial + 4 KPIs + 8 clusters live (SSE 1s) |
| **Twin** | `/v2/twin` | 3D do Parque Tejo (Three.js CDN) |
| **Sensores** | `/v2/sensors` | Malha de 62 dispositivos físicos |
| **Shows** | `/v2/shows` | Programa por dia + previsão de pico |
| **Operações** | `/v2/operations` | Painel staff + redirecionamentos ACO |
| **Limpeza** | `/v2/cleaning` | Calendário 24h + 8 pessoas Prosegur |
| **Incidentes** | `/v2/incidents` | Lista activos + histórico |
| **SCOR** | `/v2/scor` | 8 cards com 10 params cada, SSE 1s |
| **Pipelines** | `/v2/pipelines` | 4 colunas com partículas animadas |
| **Chat** | `/v2/chat` | Gemini 2.5 Flash + histórico localStorage |

### Funcionalidades transversais

- **Stream ao segundo** via SSE em `/api/v1/telemetry/clusters/stream`.
- **Hamburger veggie** (verde escuro Planta) à direita em mobile.
- **PlantaSearchBar** fixa em baixo — submit naviga para `/v2/chat?q=…`.
- **Hist. chat** persistente em localStorage `planta-chat-history-v1`.
- **Recentes** no drawer mobile: últimas 3 páginas visitadas.

---

## 6. Custo de routing

Para cada pedido de recomendação, calculamos:

```
custo_total = walk_time
            + queue_wait
            + congestion_penalty
            + show_surge_penalty
            + low_confidence_penalty
            + safety_penalty
```

Componentes:
- **walk_time** — segundos do ponto actual ao WC (mapa do venue)
- **queue_wait** — fila × tempo médio de serviço
- **congestion_penalty** — densidade no caminho
- **show_surge_penalty** — 3.8× nos 25 min pós-show
- **low_confidence_penalty** — quando sensores offline reduzem certeza
- **safety_penalty** — clusters com restrições (entrada-única, etc.)

O cluster com **menor custo total** é recomendado. Nunca damos várias
opções — uma decisão clara é melhor do que três opções.

---

## 7. O que NÃO é o PlantaOS

- ❌ Não é uma app de tracking individual.
- ❌ Não medimos CO₂, temperatura, humidade.
- ❌ Não usamos rosto, MAC, biometria.
- ❌ Não publicamos conceitos académicos no produto.
- ❌ Não inventamos dados quando o backend falha — dizemos a verdade.
- ❌ Não usamos vermelho em alertas. Cor crítica: `#C25A1A`.

---

## 8. Próximas vistas (futuro PR)

Especificadas mas ainda não implementadas:

- **Sensor Mesh** — vista do digital twin para gestão dos 62 dispositivos
  físicos (calibrar, manutenção, sugestão de posicionamento).
- **Heatmap de ocupação** — mapa de calor temporal por cluster.
- **Flow ACO** — visualização do routing inteligente em tempo real.
- **Reports diários** — geração automática PDF para Rock World.
- **Alertas operacionais** com escalação à Prosegur.

Cada uma destas vistas reaproveita o mesmo backend e os mesmos sensores —
ver [`docs/SENSORS.md`](SENSORS.md).

---

## 9. Definição de pronto

> A vista está pronta quando o Gonçalo a abre no telefone numa quinta-feira às
> 21h00 do Rock in Rio, vê os dados, percebe num segundo o que se passa,
> clica e age, e volta a ver o concerto **sem ter pensado em nada técnico**.

Esse é o teste.
