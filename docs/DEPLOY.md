# DEPLOY.md

> Como **fazer deploy**, **diagnosticar problemas**, e **recuperar** quando algo
> corre mal.

---

## 1. Vercel · Frontend

### Setup
- Project: `iamgoncalos-projects/planta-rock4`
- Branch que deploya em produção: `main`
- Framework detected: Next.js 14.2.3
- Build command: `next build`
- Output: `.next`
- Domínio: `www.plantarockinrio.com` + alias `plantarockinrio.com`

### Auto-deploy
Cada `git push` para `main` dispara automaticamente um build de produção.

### Comandos essenciais
```bash
# Estado dos últimos deploys
vercel ls

# Inspecionar um deploy específico (logs de build)
vercel inspect --logs https://planta-rock4-XXX-iamgoncalos-projects.vercel.app

# Forçar redeploy sem mudar código
vercel --prod

# Ver variáveis de ambiente
vercel env ls
```

### URL do último deploy de produção
```bash
LATEST=$(vercel ls 2>&1 | grep "Ready.*Production" | head -1 \
         | grep -oE 'https://planta-rock4-[a-z0-9]+-iamgoncalos-projects\.vercel\.app')
echo "$LATEST"
```

---

## 2. Railway · Backend

### Setup
- Project: `genuine-imagination` (id `b29c7a30-7384-405d-b4d5-2ec6073b7fda`)
- Service: `planta_rock4` (id `5f2d3ef8-cbc4-4900-be18-23f43e4a00f7`)
- Build: Nixpacks (Python 3.11 detected via `requirements.txt`)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Healthcheck: `GET /api/v1/health`
- Domínio: `api.plantarockinrio.com`

### Variáveis de ambiente essenciais
```
DATABASE_URL              postgresql+asyncpg://...
REDIS_URL                 redis://...
GEMINI_API_KEY            ...
GEMINI_MODEL              gemini-2.5-flash
CORS_ALLOW_ORIGINS        https://www.plantarockinrio.com,https://plantarockinrio.com
SCOR_KPI_TOKEN            gGQhPd2c1kVqQjQglsmt
SCOR_CLUSTER_TOKEN        04614480-c43a-1f5f-af68-86c606bddb32
```

### Comandos essenciais
```bash
# Tail logs
railway logs

# Logs do serviço específico
railway logs --service planta_rock4

# Ver env vars (JSON completo)
railway variables --json

# Deploy manual (sem precisar de commit)
railway up

# One-off com env de prod
railway run python -c "from app.main import app; print(app.routes)"

# Adicionar/remover env var
railway variables --set "FOO=bar"
railway variables delete VAR_NAME
```

---

## 3. Smoke test pós-deploy

```bash
# Health
curl https://api.plantarockinrio.com/api/v1/health
# → {"status": "ok", ...}

# Estado dos clusters agora
curl https://api.plantarockinrio.com/api/v1/telemetry/clusters/now | jq '.kpis'

# Chat
curl -X POST https://api.plantarockinrio.com/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"message": "Olá"}'

# Frontend serve o HTML
curl -sI https://www.plantarockinrio.com/v2 | head -3
```

---

## 4. Troubleshooting · Frontend

### Build falha com "useSearchParams() should be wrapped in a suspense boundary"
**Causa**: Next.js 14 App Router exige `<Suspense>` à volta de componentes que
usam `useSearchParams()` quando o build é estático.

**Fix**:
```tsx
// ❌ Antes
export default function Page() {
  const params = useSearchParams();
  // ...
}

// ✅ Depois
function PageInner() {
  const params = useSearchParams();
  // ...
}

export default function Page() {
  return (
    <Suspense fallback={<div>A carregar…</div>}>
      <PageInner />
    </Suspense>
  );
}
```

### "Module not found: '@/components/v2/X'"
**Causa**: Path alias `@/` aponta para `frontend/` no `tsconfig.json`. Confirma
o caminho real do ficheiro.

### Build OK mas browser mostra versão antiga
**Causa**: cache agressivo do browser ou do Vercel edge.

**Fixes**:
1. Abrir em **janela anónima** (Cmd+Shift+N).
2. **Hard reload**: Cmd+Shift+R no Mac.
3. iOS Safari: **Settings → Safari → Clear History and Website Data**.
4. Ou adicionar `?v=N` ao URL para forçar bypass.

### Hot reload local não funciona
```bash
cd ~/planta_rock4/frontend
rm -rf .next
npm install
npm run dev
```

---

## 5. Troubleshooting · Backend

### 502 Bad Gateway via Railway
**Causa**: serviço crashou no startup. Logs:
```bash
railway logs --service planta_rock4 | tail -50
```

Erros comuns:
- `ModuleNotFoundError`: falta dependência no `requirements.txt`
- `OperationalError: connection refused`: Postgres URL errado ou serviço inactivo
- `RuntimeError: Event loop is closed`: lifespan handlers mal escritos

### CORS error no browser
```
Access to fetch at 'https://api...' has been blocked by CORS policy
```
**Fix**: confirma `CORS_ALLOW_ORIGINS` no Railway tem o domínio correcto e
**sem espaços** entre vírgulas:
```bash
railway variables --set 'CORS_ALLOW_ORIGINS=https://www.plantarockinrio.com,https://plantarockinrio.com'
```

### SSE não funciona em produção mas funciona localmente
**Causa**: proxies intermediários (Cloudflare, Vercel edge) podem buffer SSE.

**Fix**: garantir headers no endpoint:
```python
return StreamingResponse(
    gen(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",       # nginx
        "Connection": "keep-alive",
    },
)
```

### WebSocket dropped depois de 60s
**Causa**: alguns proxies fecham conexões idle. Manter heartbeat:
```python
async def heartbeat(ws):
    while True:
        await asyncio.sleep(15)
        await ws.send_json({"type": "heartbeat", "ts": now_iso()})
```

---

## 6. Rollback rápido

### Frontend (Vercel)
```bash
# Promover deploy anterior a produção
vercel ls
vercel promote <URL-do-deploy-bom>
```

### Backend (Railway)
```bash
# Reverter para commit anterior
cd ~/planta_rock4
git revert HEAD --no-edit
git push
# Railway redeploy automático
```

Ou ir à dashboard Railway → **Deployments** → "Redeploy" no anterior.

---

## 7. Setup de uma máquina nova

```bash
# Clonar
git clone https://github.com/iamgoncalo/planta_rock4.git
cd planta_rock4

# Frontend
cd frontend
npm install
npm run dev      # http://localhost:3000

# Backend (noutro terminal)
cd ..
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Vercel CLI
npm i -g vercel
vercel login

# Railway CLI
brew install railway   # ou: curl -fsSL https://railway.app/install.sh | sh
railway login
railway link           # selecciona planta_rock4
```

---

## 8. Padrão de installers `install_vN.py`

Toda a mudança significativa é empacotada num script Python idempotente.

### Anatomia
1. **Backup** dos ficheiros que vai alterar (`.bak.vN.{timestamp}`)
2. **Escrita** dos ficheiros novos (via base64 embebido no script)
3. **Patches** opcionais (regex no código existente)
4. **Git commit + push** com mensagem descritiva

### Exemplo
```bash
mv ~/Downloads/install_v17.py ~/planta_rock4/
cd ~/planta_rock4
python3 install_v17.py
# Vercel rebuilds em ~90s
```

### Convenção
- `v10`–`v10b` → telemetria
- `v11`–`v11b` → CSS Zara minimalista
- `v12`–`v12b` → editorial Oxman + remove BottomNav
- `v13` → responsivo via media queries
- `v14` → mobile menu hamburger
- `v15` → drawer da esquerda com KPIs live
- `v16` → hamburger veggie verde à direita + drawer da direita
- `v17` → favicon + documentação master

---

## 9. Versionamento Git

Branch única (`main`). Cada commit deve ser:
- **Atómico**: uma alteração, uma mensagem
- **Descritivo**: `feat(v16):`, `fix(v12b):`, `docs:`, `chore:`
- **Sem código morto**: limpar `.bak` em PRs separados

### Limpar `.bak` acumulados
```bash
find ~/planta_rock4 -name "*.bak.*" -delete
git add -A
git commit -m "chore: limpar backups acumulados"
```

---

## 10. Checklist pré-Junho 2026

- [ ] Sensores físicos instalados (11–12 Jun)
- [ ] Rótulo `SIMULADO` removido da UI
- [ ] `/metrics` Prometheus exposto
- [ ] `/health` + `/ready` distintos no Railway
- [ ] Rate limit nginx/Cloudflare configurado
- [ ] Backup automático Postgres diário
- [ ] On-call rotation (Gonçalo primário)
- [ ] Runbook impresso e visível no CCO ([`OPS.md`](OPS.md))
