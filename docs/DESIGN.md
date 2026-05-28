# DESIGN.md

> **Design system aprovado** do PlantaOS (28 Mai 2026).  
> Inspiração: Oxman editorial — sans-serif gigante, branco, micro-tipografia
> mono, sem cromos. **Não negociável.**

---

## 1. Princípios

1. **Cada pixel ganha o seu lugar** por mostrar algo accionável. Sem decoração.
2. **Light mode é o default**. Dark mode automático via CSS vars (futuro).
3. **Sem scroll desnecessário**. Páginas críticas cabem num viewport.
4. **PT-PT** em tudo o que é visível. Inglês só para identificadores.
5. **Cor crítica = `#C25A1A`** (laranja Planta). **Nunca vermelho**.
6. **Label `SIMULADO`** apenas em contextos académicos (Zenodo, FCT).
7. **Tipografia em `clamp(min, vw, max)`** — fluida, nunca px fixo grande.

---

## 2. Identidade

### Logo
- Ficheiro: `/public/planta-logo.svg` (viewBox 0 0 380.99 295.99)
- 4 classes de fill:
  ```css
  .cls-1 { fill: #4a3521 }
  .cls-2 { fill: #28351c }
  .cls-3 { fill: #61805c }
  .cls-4 { fill: #6a8d55 }
  ```
- Tamanho TopBar: `clamp(36px, 4vw, 44px)`
- Sempre acompanhado por **"Planta Smart Homes"** em Inter 600.

### Favicon
- `/public/favicon.svg` (mesma identidade, sem fundo branco)

---

## 3. Tipografia

### Display + sans
**Inter** via CDN do criador:
```css
@import url('https://rsms.me/inter/inter.css');
```

```css
--font-display: 'Inter', 'DM Sans', -apple-system, BlinkMacSystemFont,
                system-ui, sans-serif;
--font-sans:    'Inter', 'DM Sans', -apple-system, BlinkMacSystemFont,
                system-ui, sans-serif;
```

### Mono
**DM Mono** via `next/font/google`:
```ts
const dmMono = DM_Mono({ subsets: ['latin'], weight: ['400', '500'],
                         variable: '--font-dm-mono', display: 'swap' });
```

### Escala fluida
```css
h1, .display-1 { font-size: clamp(40px, 8vw, 144px); }
h2, .display-2 { font-size: clamp(28px, 5vw, 88px);  }
h3, .display-3 { font-size: clamp(20px, 3vw, 44px);  }
h4             { font-size: clamp(16px, 1.8vw, 22px); }

.kpi-value     { font-size: clamp(32px, 6vw, 88px); font-weight: 500; }
.kpi-label     { font-size: clamp(9px, 1vw, 11px); }
.eyebrow       { font-size: clamp(9.5px, 1vw, 11px); letter-spacing: 0.2em; }
```

### Pesos
- 500 para títulos display (Inter parece pesado a 600 em sizes grandes)
- 600 para nomes próprios e botões
- 400 para body

### Tracking
- `-0.04em` para `display-1` (gigante)
- `-0.025em` para `display-2/3`
- `+0.18em` (uppercase) para mono labels e eyebrows

---

## 4. Paleta

### Tons base
```css
--bg:           #FFFFFF;
--bg-soft:      #FAFAF8;     /* hover, secções subtis */
--ink:          #0D1A0F;     /* texto principal */
--muted:        #6B7268;     /* secundário */
--faint:        #B7B9B0;     /* terciário, hints */

--border:        #ECE9E2;
--border-strong: #C9C6BD;
```

### Verdes (brand)
```css
--green-dark:   #1B3A21;     /* CTA, hamburger, indicador activo */
--green:        #2E7D4F;
--green-light:  #6FAF82;
--green-pale:   #EDF4EF;     /* hover de link activo */
```

### Alertas
```css
--amber:        #C25A1A;     /* CRÍTICO — nunca vermelho */
--amber-soft:   #FFF2E0;     /* fundo de pill SIMULADO */
```

### Quando usar
| Cor | Uso |
|---|---|
| `--ink` | texto, ícones de UI |
| `--muted` | labels, captions |
| `--faint` | divisores, hints kbd |
| `--green-dark` | botões verdes, links activos, hamburger background |
| `--green-pale` | fundo de link activo no drawer |
| `--amber` | alertas críticos · pill SIMULADO |
| `#F5F3EC` | linhas creme dentro do hamburger verde |

---

## 5. Espaçamento e raios

```css
--radius-sm:   6px;
--radius:      12px;       /* cards, inputs */
--radius-lg:   20px;       /* modais */
--radius-pill: 999px;      /* pills, botões CTA */
```

Padding em `clamp()` para escalar:
- Cards: `padding: clamp(12px, 1.8vw, 22px)`
- Page: `padding: clamp(20px, 3vw, 40px) clamp(14px, 3vw, 32px)`
- Gap em grids: `gap: clamp(10px, 1vw, 16px)`

---

## 6. Sombras

```css
--shadow-sm: 0 1px 2px rgba(13, 26, 15, 0.04);
--shadow-md: 0 8px 24px rgba(13, 26, 15, 0.08);
--shadow-lg: 0 20px 60px rgba(13, 26, 15, 0.10);
```

Usar com parcimónia. O design é maioritariamente flat com sombras para
emphasis (hover, modal, drawer).

---

## 7. Componentes-chave

### TopBar (72px fixo)
```
┌──────────────────────────────────────────────────────────┐
│ [🌱logo] Planta Smart Homes  · · · nav · · · [pill][⏱]  │ desktop
│ [🌱logo] Planta Smart Homes  · · · · · · · · · · · · [☰] │ mobile
└──────────────────────────────────────────────────────────┘
```

Breakpoint mobile: **920px**. Abaixo:
- Esconde nav linha + pill + clock
- Mostra hamburger veggie à **direita**

### Hamburger veggie
- Tamanho: 44 × 44
- Background: `--green-dark` (verde escuro Planta)
- Linhas creme: `#F5F3EC`, larguras assimétricas 18-14-18 (toque orgânico)
- BorderRadius: 12
- Sombra: `0 2px 10px rgba(27, 58, 33, 0.22)`
- Animação: 3 linhas → X com `cubic-bezier(0.32, 0.72, 0, 1)` 340ms

### Drawer mobile
- Slide-in da **direita** (mesmo lado do hamburger)
- Largura: `min(360px, 90vw)`
- Backdrop: `rgba(13, 26, 15, 0.42)` + `blur(8px)`
- Estrutura:
  1. Logo + close (X)
  2. **AGORA · ao segundo** — pessoas + ocupação (fetch a cada 4s)
  3. Search input com filtragem live
  4. **Recentes** (últimas 3 páginas via localStorage)
  5. **Tudo** (10 links)
  6. Footer "ESC fecha · 12:34:56"

### PlantaSearchBar (88px fixa em baixo)
- Width: `min(720px, calc(100% - 32px))`
- BorderRadius: 999 (pill)
- Sombra: `0 14px 38px rgba(13, 26, 15, 0.10)`
- Ícones: mic + clip + send
- Botão send: círculo 40×40, **verde escuro** quando há texto
- Submit → `router.push('/v2/chat?q=…')`
- Caption: "PlantaOS can make mistakes" em mono 11px

### Cards
```css
.card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: clamp(12px, 1.8vw, 22px);
  transition: border-color 0.22s, box-shadow 0.22s;
}
.card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-md); }
```

Variantes:
- `.card-soft` → bg `--bg-soft`
- `.card-accent` → border-left 3px verde

### Pills
```css
.pill-sim   { background: var(--amber-soft); color: var(--amber); }
.pill-live  { background: var(--green-pale); color: var(--green-dark); }
.pill-live::before { width: 6px; height: 6px; background: var(--green);
                     animation: pulse-dot 1.4s ease-in-out infinite; }
```

### KPI
```html
<div class="kpi">
  <div class="kpi-label">PESSOAS ESTIMADAS</div>
  <div class="kpi-value">381</div>
</div>
```

---

## 8. Breakpoints

```css
@media (max-width: 1024px) { /* tablet */ }
@media (max-width: 920px)  { /* mobile — hamburger aparece */ }
@media (max-width: 760px)  { /* mobile médio */ }
@media (max-width: 460px)  { /* phone pequeno */ }
@media (max-width: 380px)  { /* phone muito pequeno — brand truncada */ }
```

### Comportamento responsivo automático
O `v2.css` apanha grids inline via attribute selectors:
```css
@media (max-width: 760px) {
  .v2-content [style*="repeat(4, 1fr)"] {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
@media (max-width: 460px) {
  .v2-content [style*="repeat("] {
    grid-template-columns: 1fr !important;
  }
}
```

Isto significa que páginas com grids inline `gridTemplateColumns: 'repeat(4, 1fr)'`
colapsam automaticamente sem precisar de mexer no JSX.

---

## 9. Animações

### Easing standard
```css
transition: ... cubic-bezier(0.32, 0.72, 0, 1);
```
(Linear/Vercel style — suave mas presente.)

### Pulse-dot
```css
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.35; }
}
```

### Pulse-soft (link activo no drawer)
```css
@keyframes pulse-soft {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.6; transform: scale(0.85); }
}
```

### Burger → X
```ts
top: open ? 6 : 0,
transform: open ? 'rotate(45deg)' : 'rotate(0)',
transition: 'all 0.34s cubic-bezier(0.32, 0.72, 0, 1)'
```

---

## 10. Anti-padrões — NUNCA fazer

- ❌ Cormorant Garamond serif (foi substituído por Inter em v12)
- ❌ BottomNav (foi removido em v12)
- ❌ Vermelho em alertas
- ❌ Emoji nos títulos
- ❌ `useSearchParams()` sem `<Suspense>` wrapper (rebenta o build estático Next.js 14)
- ❌ Padding fixo > 20px em mobile (apertar via `clamp`)
- ❌ Grids `gridTemplateColumns: 'repeat(4, 1fr)'` sem media query (mas as
  media queries globais apanham — preferir `.grid-4` se possível)
- ❌ Texto a 11px ou menos (mínimo 11px)
- ❌ `position: fixed` sem `zIndex` declarado

---

## 11. Como adicionar uma nova página

1. Cria `frontend/app/v2/{nome}/page.tsx` com `'use client'` se precisar de hooks.
2. Adiciona à NAV em `frontend/components/v2/TopBar.tsx`:
   ```ts
   { href: '/v2/{nome}', label: '{Label}', hint: 'G {tecla}' }
   ```
3. Usa `<div className="page">` ou `<div className="page-full">` como container.
4. Para grids, prefere `<div className="grid grid-4">` em vez de inline styles.
5. Estado server-side via `EventSource` para `/api/v1/telemetry/clusters/stream`.
6. **Não** mexas em `v2.css` — usa as classes existentes.

---

## 12. Checklist visual antes de cada deploy

- [ ] Páginas críticas cabem em 1 viewport (sem scroll vertical) em desktop?
- [ ] Hamburger veggie aparece em mobile abaixo de 920px?
- [ ] Drawer abre da direita com KPIs e search?
- [ ] Searchbar verde escura submite para `/v2/chat`?
- [ ] Logo + "Planta Smart Homes" presentes no topo?
- [ ] Nenhuma label "SIMULADO" no UI público?
- [ ] Nenhum termo proibido (F=P/D, seed=2026, etc) visível?
- [ ] Nenhum vermelho em alertas (`#C25A1A` para crítico)?
