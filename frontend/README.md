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

Abra `http://localhost:5173`. O backend já tem `CORSMiddleware` configurável
via `CORS_ALLOWED` (ver `backend/README.md`), mas em dev o frontend nem
depende disso: o dev server do Vite faz proxy de `/api/*` para
`http://localhost:8000` (ver `vite.config.ts`) — a chamada do frontend fica
same-origin e o CORS nunca entra em jogo. Pra build de produção servido de
uma origem diferente da API, configure `CORS_ALLOWED` no backend com a
origem do frontend.

## Rodando via Docker

```bash
docker compose up --build   # a partir da raiz do repo
```

Build multi-stage: `npm run build` numa imagem `node`, servido depois por
`nginx` (ver `Dockerfile`/`nginx.conf`). O nginx faz proxy de `/api/*` pro
serviço `app` do backend — mesmo mecanismo do proxy do Vite em dev, então o
build de produção também não depende de CORS configurado. Sobe em
`http://localhost:8080` (ver `docker-compose.yml` na raiz).

## Telas

- **Inventário** (`/`) — lista de devices com busca/filtros, KPIs (total,
  online, offline, SNMP habilitado, disponibilidade média e problemas em
  aberto — os dois últimos vindos da camada de ETL via `GET
  /dashboard/summary`) e botão de scan (`POST /devices/scan`), com um campo
  opcional de subnet (CIDR) — necessário quando rodando via Docker, onde o
  backend não enxerga a LAN física do host sozinho (ver `backend/README.md`).
  Se o ARP não achar nada, o backend cai automaticamente pro ping sweep
  (ICMP) e o resultado do scan avisa isso (`used_ping_sweep_fallback`) —
  nesse modo os devices achados entram sem MAC/fabricante.
- **Detalhe do device** (`/devices/:id`) — identidade SNMP, métricas
  coletadas (agrupadas por `metric_key`, já que variam por device) e
  disponibilidade (% de uptime, downtime e MTTR na janela de 24h, via `GET
  /devices/{id}/availability`) com o histórico de eventos que sustenta esses
  números.

## Build de produção

```bash
npm run build   # roda tsc --noEmit + vite build, saída em dist/
```
