# Monitoramento de Equipamentos via SNMP

Aplicação full-stack para descoberta de equipamentos numa rede local (ARP),
identificação e coleta de métricas via SNMP, e acompanhamento de
disponibilidade (online/offline, downtime, MTTR) com um dashboard de
indicadores.

Monorepo: [`backend/`](backend/README.md) (FastAPI + SQLAlchemy + pandas) e
[`frontend/`](frontend/README.md) (React + TypeScript + Vite).

## Arquitetura

```
IPSCAN (ARP/scapy) → SNMPSCAN (identidade) → polling periódico (métricas +
disponibilidade) → Postgres (Supabase) → camada de ETL (pandas) → API REST
(FastAPI) → SPA React
```

- **Backend**: Clean Architecture em camadas (`models` → `repositories` →
  `services` → `composer`), sem Alembic (`create_all` idempotente) e sem
  APScheduler (loop `asyncio` simples). Banco padrão é Postgres via Supabase,
  tanto local quanto em Docker. Detalhes em [`backend/README.md`](backend/README.md).
- **Frontend**: SPA (React Router + TanStack Query), duas telas — inventário
  com KPIs/filtros/scan e detalhe do device com métricas e disponibilidade.
  Detalhes em [`frontend/README.md`](frontend/README.md).

## Rodando rápido (Docker)

```bash
cp backend/.env.example backend/.env   # preencha DATABASE_URL (Supabase)
docker compose up --build
```

Sobe os dois serviços: `app` (API FastAPI em `http://localhost:8000`) e
`frontend` (build de produção servido por nginx em `http://localhost:8080`,
com `/api/*` proxeado pro `app` — mesmo papel do proxy do Vite em dev, sem
precisar configurar CORS). Abra `http://localhost:8080`.

A descoberta de rede (ARP) não funciona de dentro do container Docker Desktop
(Windows/Mac) — rode o scan direto no host quando precisar descobrir devices
novos (ver [`backend/README.md`](backend/README.md#rodando-via-docker)). O
polling/coleta de métricas via SNMP roda normalmente dentro do container, e
`GET /network/ping-sweep?subnet=<sua-lan>` dá uma varredura ICMP (quem está
de pé na rede) que funciona de dentro do container mesmo sem ARP.

Pra desenvolver o frontend com hot-reload em vez do build estático do
container, use o Vite direto:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                            # http://localhost:5173
```

## Rodando localmente sem Docker

Ver os READMEs de cada parte: [`backend/README.md`](backend/README.md#rodando-localmente)
e [`frontend/README.md`](frontend/README.md#rodando-localmente-backend--frontend).

## Testes

```bash
docker compose -f docker-compose.test.yml up -d --wait   # Postgres descartável
cd backend && uv run pytest -q
```

Suíte fala com rede/banco reais (sem mock), exceto a rota `POST
/devices/scan`, que troca a dependency real de scan via
`app.dependency_overrides`. Dois testes que dependem de um device SNMP real
na LAN ficam `skip` sem `SNMP_TEST_TARGET` configurado — ver
[`backend/README.md`](backend/README.md#rodando-os-testes).

## Funcionalidades

- Descoberta de equipamentos na rede (ARP) e identificação via SNMP; varredura
  ICMP (`GET /network/ping-sweep`) como alternativa de diagnóstico em
  ambientes sem acesso L2 à LAN (ex: dentro de container).
- Polling periódico com backoff e histórico de métricas por device.
- Disponibilidade (eventos online/offline) com % de uptime, downtime e MTTR.
- Dashboard com indicadores agregados (`GET /dashboard/summary`) e por device
  (`GET /devices/{id}/availability`).
- Frontend resiliente: cada tela renderiza seu shell (header, filtros, botão
  de voltar) imediatamente, mesmo com o backend fora do ar, com banners de
  erro e retry manual, e um `ErrorBoundary` global contra falhas inesperadas
  de renderização.
