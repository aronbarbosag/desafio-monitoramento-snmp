# Network Observability — Frontend

SPA em React + TypeScript (Vite) para o inventário de devices monitorados
via SNMP/ICMP. Consome a API FastAPI em `../backend`.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # ajuste VITE_API_URL se o backend não estiver em localhost:8000
```

## Rodando localmente (backend + frontend)

Terminal 1 — backend (ver `../backend/README.md` para setup completo):

```bash
cd backend
uvicorn main:app --reload
```

Terminal 2 — frontend:

```bash
cd frontend
npm run dev
```

Abra `http://localhost:5173`. O backend não tem `CORSMiddleware` configurado
(fora do escopo deste frontend), então em vez de chamar `http://localhost:8000`
direto do navegador, o dev server do Vite faz proxy de `/api/*` para
`http://localhost:8000` (ver `vite.config.ts`) — a chamada do frontend fica
same-origin e o CORS nunca entra em jogo.

## Telas

- **Inventário** (`/`) — lista de devices com busca/filtros, KPIs (total,
  online, offline, SNMP habilitado) e botão de scan (`POST /devices/scan`).
- **Detalhe do device** (`/devices/:id`) — identidade SNMP, métricas
  coletadas (agrupadas por `metric_key`, já que variam por device) e
  histórico de disponibilidade.

## Build de produção

```bash
npm run build   # roda tsc --noEmit + vite build, saída em dist/
```
