# Migração do frontend mockup para React — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o mockup estático `frontend/Network Monitor.dc.html` por uma SPA React real (Vite + TypeScript) que consome a API FastAPI existente (`backend/api/routers/devices.py`), cobrindo Inventário de devices e Detalhe de device com dados reais.

**Architecture:** SPA client-side em `frontend/`, dois componentes de rota (`InventoryPage`, `DeviceDetailPage`) sobre React Router, dados via TanStack Query batendo direto na API FastAPI (CORS já liberado para `http://localhost:5173`). Sem backend próprio do frontend, sem SSR.

**Tech Stack:** Vite, React 18, TypeScript, react-router-dom, @tanstack/react-query. CSS puro (tokens de `ds-industry.css` reaproveitados).

**Spec:** [docs/superpowers/specs/2026-08-23-frontend-react-migration-design.md](../specs/2026-08-23-frontend-react-migration-design.md)

## Global Constraints

- Base URL do backend por padrão: `http://localhost:8000` (env `VITE_API_URL` no frontend).
- CORS do backend já libera `http://localhost:5173` por padrão (`backend/.env.example: CORS_ALLOWED=http://localhost:5173`) — não mexer no backend.
- `DeviceStatus` tem só 3 valores: `"unknown" | "online" | "offline"` (`backend/models/enums.py`) — não inventar outros estados.
- `GET /devices/{id}/history` e `GET /devices/{id}/events` retornam **mais recente primeiro** (`ORDER BY ... DESC`, ver `backend/repositories/metric_history_repository.py` e `availability_event_repository.py`) — quem monta série cronológica (sparkline) precisa inverter a lista.
- Sem suíte de testes automatizada de frontend neste MVP (decisão da spec, aprovada pelo usuário). Verificação de cada task é `npx tsc --noEmit` (checagem de tipos) + verificação manual no navegador contra o backend real rodando localmente. Não criar arquivos `*.test.ts(x)`.
- Os arquivos do mockup antigo (`Network Monitor.dc.html`, `support.js`, `.thumbnail`) não estão versionados no git (`git ls-files frontend/` só lista `.env.example`) — removê-los com `rm` normal, sem `git rm`.
- `ds-industry.css` é mantido e reaproveitado, não descartado.

---

## Task 1: Scaffold do projeto Vite + React + TS, removendo o mockup antigo

**Files:**
- Delete: `frontend/Network Monitor.dc.html`, `frontend/support.js`, `frontend/.thumbnail`
- Modify: `frontend/.env.example`
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/.gitignore`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/vite-env.d.ts`

**Interfaces:**
- Consumes: nada (task inicial).
- Produces: projeto Vite bootável (`npm run dev` serve algo em `http://localhost:5173`); `App` exportado de `frontend/src/App.tsx` como `export function App()`, montado em `main.tsx`. Tasks seguintes importam `App` só indiretamente (via `main.tsx`) e adicionam código dentro de `App`.

- [ ] **Step 1: Remover os arquivos do mockup antigo**

```bash
rm "frontend/Network Monitor.dc.html" frontend/support.js frontend/.thumbnail
```

- [ ] **Step 2: Criar `frontend/package.json`**

```json
{
  "name": "network-observability-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 3: Criar `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
```

- [ ] **Step 4: Criar `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vite/client"]
  },
  "include": ["src"]
}
```

- [ ] **Step 5: Criar `frontend/src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />
```

- [ ] **Step 6: Criar `frontend/index.html`**

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Network Observability</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Criar `frontend/src/App.tsx` (placeholder, substituído na Task 3)**

```tsx
export function App() {
  return <p>Network Observability — carregando...</p>;
}
```

- [ ] **Step 8: Criar `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 9: Sobrescrever `frontend/.env.example`**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 10: Criar `frontend/.gitignore`**

```
node_modules
dist
.env
```

- [ ] **Step 11: Instalar dependências**

```bash
cd frontend && npm install
```

- [ ] **Step 12: Verificar que o dev server sobe**

```bash
cd frontend && npm run dev &
sleep 2
curl -s http://localhost:5173 | grep -q "Network Observability" && echo OK
kill %1
```

Expected: imprime `OK` (o `index.html` servido contém o `<title>`).

- [ ] **Step 13: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Vite+React+TS, remove mockup antigo"
```

---

## Task 2: Camada de API — tipos, cliente HTTP e hooks do React Query

**Files:**
- Create: `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/api/queries.ts`

**Interfaces:**
- Consumes: nada de tasks anteriores além do projeto scaffolded (Task 1).
- Produces (usados pelas Tasks 4 e 5):
  - Tipos em `types.ts`: `DeviceStatus`, `MetricValueType`, `DeviceOut`, `MetricHistoryOut`, `AvailabilityEventOut`, `ScanResult`.
  - `apiClient` em `client.ts` com métodos `listDevices()`, `getDevice(id)`, `getDeviceHistory(id, limit?)`, `getDeviceEvents(id, limit?)`, `scanDevices()`.
  - Hooks em `queries.ts`: `useDevices()`, `useDevice(id: number)`, `useDeviceHistory(id: number)`, `useDeviceEvents(id: number)`, `useScanMutation()` — todos exportados como funções nomeadas.

- [ ] **Step 1: Criar `frontend/src/api/types.ts`**

```ts
export type DeviceStatus = "unknown" | "online" | "offline";
export type MetricValueType = "integer" | "counter" | "gauge" | "string";

export interface DeviceOut {
  id: number;
  ip: string;
  mac: string;
  vendor: string | null;
  device_type: string | null;
  hostname: string | null;
  sys_descr: string | null;
  model_name: string | null;
  sys_contact: string | null;
  sys_location: string | null;
  snmp_supported: boolean;
  status: DeviceStatus;
  poll_interval_seconds: number;
  consecutive_failures: number;
  last_checked_at: string | null;
}

export interface MetricHistoryOut {
  id: number;
  collected_at: string;
  metric_key: string;
  metric_name: string;
  metric_unit: string | null;
  value_type: MetricValueType;
  value_numeric: number | null;
  value_text: string | null;
}

export interface AvailabilityEventOut {
  id: number;
  status: DeviceStatus;
  started_at: string;
  ended_at: string | null;
}

export interface ScanResult {
  subnet: string | null;
  devices_found: number;
  devices_probed: number;
  snmp_identified: number;
}
```

- [ ] **Step 2: Criar `frontend/src/api/client.ts`**

```ts
import type { AvailabilityEventOut, DeviceOut, MetricHistoryOut, ScanResult } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const DEFAULT_LIST_LIMIT = 100;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new ApiError(res.status, detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  listDevices: () => request<DeviceOut[]>("/devices"),
  getDevice: (id: number) => request<DeviceOut>(`/devices/${id}`),
  getDeviceHistory: (id: number, limit = DEFAULT_LIST_LIMIT) =>
    request<MetricHistoryOut[]>(`/devices/${id}/history?limit=${limit}`),
  getDeviceEvents: (id: number, limit = DEFAULT_LIST_LIMIT) =>
    request<AvailabilityEventOut[]>(`/devices/${id}/events?limit=${limit}`),
  scanDevices: () => request<ScanResult>("/devices/scan", { method: "POST" }),
};
```

- [ ] **Step 3: Criar `frontend/src/api/queries.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

const DEVICES_REFETCH_MS = 30_000;

export function useDevices() {
  return useQuery({
    queryKey: ["devices"],
    queryFn: apiClient.listDevices,
    refetchInterval: DEVICES_REFETCH_MS,
  });
}

export function useDevice(id: number) {
  return useQuery({
    queryKey: ["devices", id],
    queryFn: () => apiClient.getDevice(id),
    refetchInterval: DEVICES_REFETCH_MS,
  });
}

export function useDeviceHistory(id: number) {
  return useQuery({
    queryKey: ["devices", id, "history"],
    queryFn: () => apiClient.getDeviceHistory(id),
  });
}

export function useDeviceEvents(id: number) {
  return useQuery({
    queryKey: ["devices", id, "events"],
    queryFn: () => apiClient.getDeviceEvents(id),
  });
}

export function useScanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: apiClient.scanDevices,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
    },
  });
}
```

- [ ] **Step 4: Instalar o React Query (não incluído no scaffold da Task 1 alem da entrada em package.json — garantir que foi instalado)**

```bash
cd frontend && npm install
```

- [ ] **Step 5: Checar tipos**

```bash
cd frontend && npx tsc --noEmit
```

Expected: sem erros (a task ainda não usa esses módulos em nenhum componente, então isso valida só sintaxe/tipos internos).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/
git commit -m "feat(frontend): tipos, cliente HTTP e hooks de query para a API de devices"
```

---

## Task 3: App shell — Router, QueryClientProvider e estilos

**Files:**
- Create: `frontend/src/styles/ds-industry.css` (copiado de `frontend/ds-industry.css`), `frontend/src/styles/app.css`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`
- Delete: `frontend/ds-industry.css` (movido para `src/styles/`)

**Interfaces:**
- Consumes: nada novo de código (não depende da Task 2 diretamente, mas roda em paralelo a ela na árvore de arquivos).
- Produces: `App` agora monta `QueryClientProvider` + `BrowserRouter` + `Routes` com duas rotas placeholder (`/` e `/devices/:id`), consumidas pelas Tasks 4 e 5, que só precisam trocar o elemento de cada `<Route>`. Classes CSS utilitárias disponíveis globalmente: `.page`, `.page-header`, `.kpi-grid`, `.filters`, `.metric-grid`, `.event-timeline`, `.scan-button`, `.scan-result`, `.kpi-card`, `.metric-card`, `.status-badge` (+ variantes `--online`, `--offline`, `--unknown`).

- [ ] **Step 1: Mover `ds-industry.css` para `src/styles/`**

```bash
mkdir -p frontend/src/styles
git mv frontend/ds-industry.css frontend/src/styles/ds-industry.css 2>/dev/null || mv frontend/ds-industry.css frontend/src/styles/ds-industry.css
```

(o arquivo não está versionado ainda nesta migração — se `git mv` falhar por não estar trackeado, o `mv` do fallback resolve.)

- [ ] **Step 2: Criar `frontend/src/styles/app.css`**

```css
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-6) var(--space-8);
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--space-4);
}

.kpi-card {
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.kpi-card__value {
  font-family: var(--font-heading);
  font-size: 32px;
  line-height: 1;
}

.kpi-card__hint {
  font-size: 12px;
  color: color-mix(in srgb, var(--color-text) 55%, transparent);
}

.filters {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-4);
}

.metric-card {
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.metric-card__value {
  font-family: var(--font-heading);
  font-size: 24px;
  line-height: 1;
}

.event-timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.event-timeline__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-divider);
  font-size: 13px;
}

.event-timeline__duration {
  margin-left: auto;
  color: color-mix(in srgb, var(--color-text) 55%, transparent);
}

.scan-button {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.scan-result {
  font-size: 12px;
  color: color-mix(in srgb, var(--color-text) 60%, transparent);
}

.scan-result--error {
  color: oklch(0.55 0.14 27);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.status-badge::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}

.status-badge--online::before {
  background: oklch(0.6 0.09 155);
}

.status-badge--offline::before {
  background: oklch(0.55 0.14 27);
}

.status-badge--unknown::before {
  background: var(--color-neutral-500);
}
```

- [ ] **Step 3: Reescrever `frontend/src/App.tsx`**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { InventoryPage } from "./pages/InventoryPage";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<InventoryPage />} />
          <Route path="/devices/:id" element={<DeviceDetailPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 4: Criar placeholders `frontend/src/pages/InventoryPage.tsx` e `frontend/src/pages/DeviceDetailPage.tsx` (substituídos nas Tasks 4 e 5)**

```tsx
// frontend/src/pages/InventoryPage.tsx
export function InventoryPage() {
  return <p>Inventário — em construção.</p>;
}
```

```tsx
// frontend/src/pages/DeviceDetailPage.tsx
export function DeviceDetailPage() {
  return <p>Detalhe do device — em construção.</p>;
}
```

- [ ] **Step 5: Atualizar `frontend/src/main.tsx` para importar os estilos**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/ds-industry.css";
import "./styles/app.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 6: Checar tipos**

```bash
cd frontend && npx tsc --noEmit
```

Expected: sem erros.

- [ ] **Step 7: Verificar visualmente**

```bash
cd frontend && npm run dev &
sleep 2
curl -s http://localhost:5173 | grep -q "Network Observability" && echo OK
kill %1
```

Abrir `http://localhost:5173` manualmente e navegar para `http://localhost:5173/devices/1` confirmando que o roteamento troca o texto exibido e que a tipografia (`Barlow`/`Barlow Condensed`) e as cores de `ds-industry.css` estão aplicadas (fundo `--color-bg`, texto `--color-text`).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/ frontend/ds-industry.css
git commit -m "feat(frontend): app shell com router, react-query e estilos base"
```

---

## Task 4: Tela de Inventário

**Files:**
- Create: `frontend/src/components/StatusBadge.tsx`, `frontend/src/components/KpiCard.tsx`, `frontend/src/components/DeviceTable.tsx`, `frontend/src/components/ScanButton.tsx`
- Modify: `frontend/src/pages/InventoryPage.tsx`

**Interfaces:**
- Consumes: `DeviceOut`, `DeviceStatus` (Task 2 `types.ts`), `useDevices`, `useScanMutation` (Task 2 `queries.ts`), classes CSS da Task 3.
- Produces: `StatusBadge({ status: DeviceStatus })`, usado também pela Task 5. `InventoryPage` renderiza a rota `/` com dados reais.

- [ ] **Step 1: Criar `frontend/src/components/StatusBadge.tsx`**

```tsx
import type { DeviceStatus } from "../api/types";

const STATUS_LABEL: Record<DeviceStatus, string> = {
  online: "Online",
  offline: "Offline",
  unknown: "Desconhecido",
};

export function StatusBadge({ status }: { status: DeviceStatus }) {
  return <span className={`status-badge status-badge--${status}`}>{STATUS_LABEL[status]}</span>;
}
```

- [ ] **Step 2: Criar `frontend/src/components/KpiCard.tsx`**

```tsx
interface KpiCardProps {
  label: string;
  value: string | number;
  hint?: string;
}

export function KpiCard({ label, value, hint }: KpiCardProps) {
  return (
    <div className="card blueprint kpi-card">
      <div className="card-kicker">{label}</div>
      <div className="kpi-card__value">{value}</div>
      {hint && <div className="kpi-card__hint">{hint}</div>}
    </div>
  );
}
```

- [ ] **Step 3: Criar `frontend/src/components/DeviceTable.tsx`**

```tsx
import type { DeviceOut } from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface DeviceTableProps {
  devices: DeviceOut[];
  onSelect: (id: number) => void;
}

export function DeviceTable({ devices, onSelect }: DeviceTableProps) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Device</th>
          <th>Tipo</th>
          <th>Vendor / modelo</th>
          <th>IP</th>
          <th>Status</th>
          <th>SNMP</th>
          <th>Última checagem</th>
        </tr>
      </thead>
      <tbody>
        {devices.map((d) => (
          <tr key={d.id} onClick={() => onSelect(d.id)} style={{ cursor: "pointer" }}>
            <td>{d.hostname ?? d.ip}</td>
            <td>{d.device_type ?? "—"}</td>
            <td>{[d.vendor, d.model_name].filter(Boolean).join(" ") || "—"}</td>
            <td>{d.ip}</td>
            <td>
              <StatusBadge status={d.status} />
            </td>
            <td>{d.snmp_supported ? "Sim" : "Não"}</td>
            <td>{d.last_checked_at ? new Date(d.last_checked_at).toLocaleString() : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Criar `frontend/src/components/ScanButton.tsx`**

```tsx
import { useState } from "react";
import { useScanMutation } from "../api/queries";

export function ScanButton() {
  const scan = useScanMutation();
  const [showResult, setShowResult] = useState(false);

  return (
    <div className="scan-button">
      <button
        className="btn btn-primary"
        disabled={scan.isPending}
        onClick={() => {
          setShowResult(false);
          scan.mutate(undefined, { onSuccess: () => setShowResult(true) });
        }}
      >
        {scan.isPending ? "Executando scan..." : "Executar scan"}
      </button>
      {showResult && scan.data && (
        <div className="scan-result">
          {scan.data.devices_found} encontrados · {scan.data.devices_probed} sondados ·{" "}
          {scan.data.snmp_identified} identificados via SNMP
          {scan.data.subnet ? ` · ${scan.data.subnet}` : ""}
        </div>
      )}
      {scan.isError && <div className="scan-result scan-result--error">Falha ao executar scan.</div>}
    </div>
  );
}
```

- [ ] **Step 5: Reescrever `frontend/src/pages/InventoryPage.tsx`**

```tsx
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDevices } from "../api/queries";
import type { DeviceStatus } from "../api/types";
import { DeviceTable } from "../components/DeviceTable";
import { KpiCard } from "../components/KpiCard";
import { ScanButton } from "../components/ScanButton";

const STATUS_OPTIONS: Array<DeviceStatus | "all"> = ["all", "online", "offline", "unknown"];

export function InventoryPage() {
  const { data: devices, isLoading, isError } = useDevices();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [deviceType, setDeviceType] = useState("all");
  const [vendor, setVendor] = useState("all");
  const [status, setStatus] = useState<DeviceStatus | "all">("all");

  const deviceTypes = useMemo(
    () => ["all", ...new Set((devices ?? []).map((d) => d.device_type).filter((v): v is string => !!v))],
    [devices],
  );
  const vendors = useMemo(
    () => ["all", ...new Set((devices ?? []).map((d) => d.vendor).filter((v): v is string => !!v))],
    [devices],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (devices ?? []).filter((d) => {
      if (deviceType !== "all" && d.device_type !== deviceType) return false;
      if (vendor !== "all" && d.vendor !== vendor) return false;
      if (status !== "all" && d.status !== status) return false;
      if (q && !`${d.hostname ?? ""} ${d.ip}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [devices, query, deviceType, vendor, status]);

  const kpis = useMemo(() => {
    const all = devices ?? [];
    return {
      total: all.length,
      online: all.filter((d) => d.status === "online").length,
      offline: all.filter((d) => d.status === "offline").length,
      unknown: all.filter((d) => d.status === "unknown").length,
      snmp: all.filter((d) => d.snmp_supported).length,
    };
  }, [devices]);

  if (isLoading) return <p>Carregando devices...</p>;
  if (isError) return <p>Falha ao carregar devices.</p>;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Inventário de devices</h1>
        <ScanButton />
      </header>

      <div className="kpi-grid">
        <KpiCard label="Total" value={kpis.total} />
        <KpiCard label="Online" value={kpis.online} />
        <KpiCard label="Offline" value={kpis.offline} />
        <KpiCard label="Desconhecido" value={kpis.unknown} />
        <KpiCard label="SNMP habilitado" value={kpis.snmp} />
      </div>

      <div className="filters">
        <input
          className="input"
          placeholder="Buscar hostname ou IP"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="input" value={deviceType} onChange={(e) => setDeviceType(e.target.value)}>
          {deviceTypes.map((t) => (
            <option key={t} value={t}>
              {t === "all" ? "Todos os tipos" : t}
            </option>
          ))}
        </select>
        <select className="input" value={vendor} onChange={(e) => setVendor(e.target.value)}>
          {vendors.map((v) => (
            <option key={v} value={v}>
              {v === "all" ? "Todos os vendors" : v}
            </option>
          ))}
        </select>
        <select
          className="input"
          value={status}
          onChange={(e) => setStatus(e.target.value as DeviceStatus | "all")}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "all" ? "Todos os status" : s}
            </option>
          ))}
        </select>
      </div>

      <DeviceTable devices={filtered} onSelect={(id) => navigate(`/devices/${id}`)} />
    </div>
  );
}
```

- [ ] **Step 6: Checar tipos**

```bash
cd frontend && npx tsc --noEmit
```

Expected: sem erros.

- [ ] **Step 7: Verificar manualmente contra o backend real**

```bash
cd backend && uvicorn main:app --reload &
sleep 2
cd frontend && npm run dev &
```

Abrir `http://localhost:5173`, confirmar: KPIs batem com a contagem de devices retornada por `GET http://localhost:8000/devices`; busca e filtros funcionam; clicar "Executar scan" mostra o resumo do `ScanResult`. Encerrar os dois processos (`kill %1 %2` ou Ctrl+C em cada terminal) ao terminar.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): tela de inventario com KPIs, filtros e scan"
```

---

## Task 5: Tela de Detalhe do device

**Files:**
- Create: `frontend/src/components/MetricCard.tsx`, `frontend/src/components/EventTimeline.tsx`
- Modify: `frontend/src/pages/DeviceDetailPage.tsx`

**Interfaces:**
- Consumes: `MetricHistoryOut`, `AvailabilityEventOut` (Task 2 `types.ts`), `useDevice`, `useDeviceHistory`, `useDeviceEvents` (Task 2 `queries.ts`), `StatusBadge` (Task 4).
- Produces: `computeUptimePercent(events: AvailabilityEventOut[]): number | null`, exportado de `EventTimeline.tsx` (função pura, sem estado — usada só dentro de `DeviceDetailPage`).

- [ ] **Step 1: Criar `frontend/src/components/MetricCard.tsx`**

```tsx
import type { MetricHistoryOut } from "../api/types";

interface MetricCardProps {
  points: MetricHistoryOut[]; // mesma metric_key, ordenados mais recente primeiro (vem da API)
}

function buildSparklinePath(values: number[], width: number, height: number): string {
  if (values.length < 2) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const coords = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x.toFixed(1)} ${y.toFixed(1)}`;
  });
  return `M${coords.join(" L")}`;
}

export function MetricCard({ points }: MetricCardProps) {
  const latest = points[0];
  const chronological = [...points].reverse();
  const numeric = chronological.map((p) => p.value_numeric).filter((v): v is number => v !== null);

  return (
    <div className="card blueprint metric-card">
      <div className="card-kicker">
        {latest.metric_name}
        {latest.metric_unit ? ` (${latest.metric_unit})` : ""}
      </div>
      <div className="metric-card__value">
        {latest.value_type === "string" ? latest.value_text : latest.value_numeric}
      </div>
      {numeric.length >= 2 && (
        <svg width="100%" height="32" viewBox="0 0 120 32" preserveAspectRatio="none">
          <path
            d={buildSparklinePath(numeric, 120, 32)}
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth="1.4"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Criar `frontend/src/components/EventTimeline.tsx`**

```tsx
import type { AvailabilityEventOut } from "../api/types";
import { StatusBadge } from "./StatusBadge";

function formatDuration(ms: number): string {
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}min`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

export function computeUptimePercent(events: AvailabilityEventOut[]): number | null {
  if (events.length === 0) return null;
  const now = Date.now();
  let onlineMs = 0;
  let totalMs = 0;
  for (const e of events) {
    const start = new Date(e.started_at).getTime();
    const end = e.ended_at ? new Date(e.ended_at).getTime() : now;
    const duration = Math.max(0, end - start);
    totalMs += duration;
    if (e.status === "online") onlineMs += duration;
  }
  if (totalMs === 0) return null;
  return (onlineMs / totalMs) * 100;
}

export function EventTimeline({ events }: { events: AvailabilityEventOut[] }) {
  if (events.length === 0) return <p>Sem eventos de disponibilidade registrados.</p>;

  return (
    <ul className="event-timeline">
      {events.map((e) => {
        const start = new Date(e.started_at).getTime();
        const end = e.ended_at ? new Date(e.ended_at).getTime() : Date.now();
        return (
          <li key={e.id} className="event-timeline__item">
            <StatusBadge status={e.status} />
            <span>
              {new Date(e.started_at).toLocaleString()}
              {e.ended_at ? ` → ${new Date(e.ended_at).toLocaleString()}` : " → em curso"}
            </span>
            <span className="event-timeline__duration">{formatDuration(end - start)}</span>
          </li>
        );
      })}
    </ul>
  );
}
```

- [ ] **Step 3: Reescrever `frontend/src/pages/DeviceDetailPage.tsx`**

```tsx
import { useNavigate, useParams } from "react-router-dom";
import { useDevice, useDeviceEvents, useDeviceHistory } from "../api/queries";
import type { MetricHistoryOut } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { MetricCard } from "../components/MetricCard";
import { EventTimeline, computeUptimePercent } from "../components/EventTimeline";

function groupByMetricKey(history: MetricHistoryOut[]): Record<string, MetricHistoryOut[]> {
  const groups: Record<string, MetricHistoryOut[]> = {};
  for (const point of history) {
    (groups[point.metric_key] ??= []).push(point);
  }
  return groups;
}

export function DeviceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const deviceId = Number(id);
  const navigate = useNavigate();

  const device = useDevice(deviceId);
  const history = useDeviceHistory(deviceId);
  const events = useDeviceEvents(deviceId);

  if (device.isLoading) return <p>Carregando device...</p>;
  if (device.isError || !device.data) return <p>Device não encontrado.</p>;

  const d = device.data;
  const groups = groupByMetricKey(history.data ?? []);
  const uptimePercent = computeUptimePercent(events.data ?? []);

  return (
    <div className="page">
      <button className="btn btn-secondary" onClick={() => navigate("/")} style={{ alignSelf: "flex-start" }}>
        ← Inventário
      </button>

      <header className="page-header">
        <h1>{d.hostname ?? d.ip}</h1>
        <StatusBadge status={d.status} />
      </header>

      <table className="table">
        <tbody>
          <tr>
            <td>IP</td>
            <td>{d.ip}</td>
          </tr>
          <tr>
            <td>MAC</td>
            <td>{d.mac}</td>
          </tr>
          <tr>
            <td>Vendor / modelo</td>
            <td>{[d.vendor, d.model_name].filter(Boolean).join(" ") || "—"}</td>
          </tr>
          <tr>
            <td>sysDescr</td>
            <td>{d.sys_descr ?? "—"}</td>
          </tr>
          <tr>
            <td>Contato</td>
            <td>{d.sys_contact ?? "—"}</td>
          </tr>
          <tr>
            <td>Localização</td>
            <td>{d.sys_location ?? "—"}</td>
          </tr>
          <tr>
            <td>Intervalo de poll</td>
            <td>{d.poll_interval_seconds}s</td>
          </tr>
          <tr>
            <td>Última checagem</td>
            <td>{d.last_checked_at ? new Date(d.last_checked_at).toLocaleString() : "—"}</td>
          </tr>
        </tbody>
      </table>

      <section>
        <h2>Métricas</h2>
        {Object.keys(groups).length === 0 && <p>Sem histórico de métricas.</p>}
        <div className="metric-grid">
          {Object.entries(groups).map(([key, points]) => (
            <MetricCard key={key} points={points} />
          ))}
        </div>
      </section>

      <section>
        <h2>
          Disponibilidade
          {uptimePercent !== null ? ` · ${uptimePercent.toFixed(1)}% online na janela retornada` : ""}
        </h2>
        <EventTimeline events={events.data ?? []} />
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Checar tipos**

```bash
cd frontend && npx tsc --noEmit
```

Expected: sem erros.

- [ ] **Step 5: Verificar manualmente contra o backend real**

```bash
cd backend && uvicorn main:app --reload &
sleep 2
cd frontend && npm run dev &
```

Abrir `http://localhost:5173`, clicar em uma linha da tabela de inventário, confirmar: navega para `/devices/:id`; identidade (ip/mac/vendor/sysDescr/etc) bate com `GET /devices/{id}`; cards de métrica aparecem agrupados por `metric_key` (um por métrica coletada); timeline de eventos mostra as transições de `GET /devices/{id}/events`; botão "← Inventário" volta pra `/`. Encerrar os processos ao terminar.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): tela de detalhe do device com metricas e eventos"
```

---

## Task 6: README do frontend e verificação end-to-end

**Files:**
- Create: `frontend/README.md`

**Interfaces:**
- Consumes: nada novo — task de documentação e verificação final sobre o que as Tasks 1-5 produziram.
- Produces: nada consumido por outra task (é a última).

- [ ] **Step 1: Criar `frontend/README.md`**

```markdown
# Network Observability — Frontend

SPA em React + TypeScript (Vite) para o inventário de devices monitorados
via SNMP/ICMP. Consome a API FastAPI em `../backend`.

## Setup

\`\`\`bash
cd frontend
npm install
cp .env.example .env   # ajuste VITE_API_URL se o backend não estiver em localhost:8000
\`\`\`

## Rodando localmente (backend + frontend)

Terminal 1 — backend (ver `../backend/README.md` para setup completo):

\`\`\`bash
cd backend
uvicorn main:app --reload
\`\`\`

Terminal 2 — frontend:

\`\`\`bash
cd frontend
npm run dev
\`\`\`

Abra `http://localhost:5173`. O backend já libera CORS para essa origem por
padrão (`CORS_ALLOWED` em `backend/.env`).

## Telas

- **Inventário** (`/`) — lista de devices com busca/filtros, KPIs (total,
  online, offline, SNMP habilitado) e botão de scan (`POST /devices/scan`).
- **Detalhe do device** (`/devices/:id`) — identidade SNMP, métricas
  coletadas (agrupadas por `metric_key`, já que variam por device) e
  histórico de disponibilidade.

## Build de produção

\`\`\`bash
npm run build   # roda tsc --noEmit + vite build, saída em dist/
\`\`\`
```

- [ ] **Step 2: Rodar o build de produção**

```bash
cd frontend && npm run build
```

Expected: termina sem erros, gera `frontend/dist/`.

- [ ] **Step 3: Verificação end-to-end manual**

```bash
cd backend && uvicorn main:app --reload &
sleep 2
cd frontend && npm run dev &
```

Percorrer o fluxo completo no navegador: abrir `/`, conferir KPIs e tabela;
rodar "Executar scan" e ver o resumo aparecer; abrir um device pela tabela;
conferir identidade, métricas e eventos na tela de detalhe; voltar pro
inventário. Encerrar os processos ao terminar.

- [ ] **Step 4: Commit**

```bash
git add frontend/README.md
git commit -m "docs(frontend): README de setup e verificacao end-to-end"
```
