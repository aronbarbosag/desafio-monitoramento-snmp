# Migração do frontend para React — design

Data: 2026-08-23

## Contexto

O `frontend/` atual não é um app funcional: é um mockup estático gerado pela
ferramenta de Design Canvas do Claude (`Network Monitor.dc.html`, formato
`.dc.html`, interpretado em runtime por `support.js`), com dados 100%
inventados (array `DEV` hardcoded no próprio HTML). Ele nunca fez uma
chamada real ao backend.

O backend (`backend/`) é uma API FastAPI real, já rodando, com um único
router (`devices`):

- `GET /devices` — lista (`DeviceOut`)
- `GET /devices/{id}` — detalhe (`DeviceOut`)
- `GET /devices/{id}/history?limit=` — histórico de métricas (`MetricHistoryOut[]`)
- `GET /devices/{id}/events?limit=` — eventos de disponibilidade (`AvailabilityEventOut[]`)
- `POST /devices/scan` — dispara scan IP+SNMP síncrono, devolve `ScanResult`

CORS já está configurado (`CORS_ALLOWED_ORIGINS`, default
`http://localhost:5173` em `.env.example`) — o backend já espera um
frontend Vite rodando na porta padrão.

O mockup imagina bem mais do que o backend entrega hoje: topologia LLDP,
KPIs de SLA/latência/disponibilidade 30d, layout "por subnet", e um form de
discovery com job assíncrono e credenciais persistidas. Nenhuma dessas
entidades/endpoints existe no backend atual.

## Decisão de escopo

Migração cobre **apenas o que o backend já suporta com dados reais**:

- Inventário de devices (lista, busca, filtros, KPIs derivados de dados reais)
- Ação de scan (dispara `POST /devices/scan`, mostra o resultado)
- Detalhe de um device (identidade, histórico de métricas, eventos de disponibilidade)

Ficam de fora (sem endpoint/dado real no backend hoje): topologia/mapa LLDP,
layout "por subnet" (não há entidade Subnet exposta via API), form de
discovery com credenciais salvas e job assíncrono, KPIs de latência/SLA/
disponibilidade fixa em 30 dias (não há latência armazenada — `PingService`
só retorna booleano online/offline; ver `backend/services/ping_service.py`).

Os arquivos do mockup antigo são substituídos pelo novo app:
`Network Monitor.dc.html`, `support.js` e `.thumbnail` são removidos como
parte da migração. `ds-industry.css` é mantido e reaproveitado (ver seção
Visual).

## Stack

- **Vite + React + TypeScript**, SPA em `frontend/`.
- **React Router** — duas rotas: `/` (Inventory) e `/devices/:id` (Device Detail).
- **TanStack Query** — data fetching, cache, refetch periódico (alinhado ao
  ciclo de polling do backend, ~30-60s), estados de loading/error.
- Cliente HTTP fino (`fetch` nativo) em `src/api/client.ts`, base URL via
  `VITE_API_URL` (`.env`, default `http://localhost:8000`).
- Tipos TS em `src/api/types.ts` espelhando `backend/api/schemas.py`
  (`DeviceOut`, `MetricHistoryOut`, `AvailabilityEventOut`, `ScanResult`) e
  `backend/models/enums.py` (`DeviceStatus`: `unknown | online | offline`).

## Estrutura de arquivos

```
frontend/
  index.html
  vite.config.ts
  tsconfig.json
  package.json
  .env.example          (VITE_API_URL=http://localhost:8000)
  src/
    main.tsx
    App.tsx              (Router + QueryClientProvider)
    api/
      client.ts           (fetch wrapper, trata erro HTTP)
      types.ts             (interfaces espelhando os schemas do backend)
      queries.ts           (hooks: useDevices, useDevice, useDeviceHistory,
                             useDeviceEvents, useScanMutation)
    pages/
      InventoryPage.tsx
      DeviceDetailPage.tsx
    components/
      DeviceTable.tsx
      StatusBadge.tsx       (mapeia DeviceStatus -> cor/label)
      KpiCard.tsx
      ScanButton.tsx        (dispara scan, mostra ScanResult em toast/painel)
      MetricCard.tsx        (agrupado por metric_key, sparkline)
      EventTimeline.tsx
    styles/
      ds-industry.css        (copiado/adaptado do mockup atual)
      app.css                 (ajustes específicos do app: paleta de 3 status)
  README.md               (setup, como rodar junto do backend)
```

## Telas

### Inventory (`/`)

Fonte: `GET /devices` (React Query, `refetchInterval`).

- Busca por hostname/IP, filtros por `device_type`, `vendor`, `status`
  (client-side, sobre a lista já carregada — sem endpoint de filtro no
  backend).
- KPIs (derivados só de campos reais de `DeviceOut`): total de devices,
  contagem online, contagem offline, contagem unknown, quantos têm
  `snmp_supported = true`.
- Tabela: hostname/ip, device_type, vendor + model_name, status (via
  `StatusBadge`), snmp_supported, last_checked_at. Clique na linha navega
  para `/devices/:id`.
- Botão "Executar scan" → `useScanMutation` (`POST /devices/scan`); ao
  concluir, mostra o `ScanResult` retornado (subnet, devices_found,
  devices_probed, snmp_identified) e invalida a query de `devices` pra
  refletir novos devices encontrados.

### Device Detail (`/devices/:id`)

Fontes: `GET /devices/{id}`, `GET /devices/{id}/history`,
`GET /devices/{id}/events`.

- Cabeçalho: hostname (ou ip se hostname nulo), `StatusBadge`, ip, mac,
  vendor, sys_descr, model_name, sys_contact, sys_location,
  poll_interval_seconds, last_checked_at.
- Métricas: agrupa `history` por `metric_key` (chave dinâmica — CPU,
  memória, interfaces etc. variam por device conforme o walk SNMP
  disponível). Para cada grupo, um `MetricCard` com: nome/unidade
  (`metric_name`/`metric_unit`), último valor, sparkline dos últimos N
  pontos `value_numeric` (quando `value_type` é numérico); quando
  `value_type` é `string`, mostra só o último valor textual sem gráfico.
- Disponibilidade: `EventTimeline` renderiza os `AvailabilityEventOut` em
  ordem cronológica (status, started_at, ended_at); calcula um % de tempo
  online **sobre a própria janela retornada** (soma dos intervalos com
  status online / duração total coberta pelos eventos), rotulado
  explicitamente com o período coberto — não assume "30 dias" fixo.

## Visual

Reaproveita os tokens/classes de `ds-industry.css` (`--color-*`,
`--font-heading`/`--font-body`, `.card`, `.table`, `.btn`, `.tag`, `.field`,
`.input`, `.seg`) como CSS estático importado — sem o runtime de templating
`{{ }}` do `.dc.html`/`support.js`, que não faz sentido fora da ferramenta de
Design Canvas. Paleta de status ajustada para os 3 valores reais de
`DeviceStatus` (online = verde, offline = vermelho, unknown = neutro),
substituindo os 4 estados fictícios do mockup (up/warn/down/maint).

## Testes e verificação

Sem suíte automatizada de frontend neste MVP (fora do escopo pedido).
Verificação manual: `npm run dev` (Vite) rodando contra o backend real
(`uvicorn` local, mesmo `.env`/Supabase do backend), navegando Inventory →
scan → Device Detail e conferindo que os dados batem com o que a API
devolve. README documenta os dois comandos (`backend` + `frontend`) lado a
lado.
