import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDashboardSummary, useDevices } from "../api/queries";
import type { DeviceStatus } from "../api/types";
import { DeviceTable } from "../components/DeviceTable";
import { KpiCard } from "../components/KpiCard";
import { ScanButton } from "../components/ScanButton";
import { STATUS_LABEL } from "../components/StatusBadge";

const STATUS_OPTIONS: Array<DeviceStatus | "all"> = ["all", "online", "offline", "unknown"];

export function InventoryPage() {
  const { data: devices, isLoading, isError, refetch, isRefetching } = useDevices();
  const dashboard = useDashboardSummary();
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

  // Mostra a tela normal (header, filtros) desde o primeiro render — só a
  // área de dados fica pendente até a GET responder. Nunca troca a página
  // inteira por um texto de loading/erro.
  const pending = isLoading && !devices;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Device inventory</h1>
        <ScanButton />
      </header>

      {isError && (
        <p className="banner banner--warning">
          {devices
            ? "No connection to the server — showing the last known data."
            : "Failed to load devices. Check that the backend is running."}
          <button
            className="btn btn-secondary"
            style={{ marginLeft: "var(--space-4)" }}
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            {isRefetching ? "Retrying..." : "Retry"}
          </button>
        </p>
      )}

      <div className="kpi-grid">
        <KpiCard label="Total" value={pending ? "…" : kpis.total} />
        <KpiCard label="Online" value={pending ? "…" : kpis.online} />
        <KpiCard label="Offline" value={pending ? "…" : kpis.offline} />
        <KpiCard label="Unknown" value={pending ? "…" : kpis.unknown} />
        <KpiCard label="SNMP enabled" value={pending ? "…" : kpis.snmp} />
        <KpiCard
          label="Avg. availability (24h)"
          value={dashboard.data ? `${dashboard.data.avg_availability_pct.toFixed(1)}%` : "—"}
        />
        <KpiCard
          label="Open problems"
          value={dashboard.data ? dashboard.data.open_problems : "—"}
        />
      </div>

      <div className="filters">
        <input
          className="input"
          placeholder="Search hostname or IP"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="input" value={deviceType} onChange={(e) => setDeviceType(e.target.value)}>
          {deviceTypes.map((t) => (
            <option key={t} value={t}>
              {t === "all" ? "All types" : t}
            </option>
          ))}
        </select>
        <select className="input" value={vendor} onChange={(e) => setVendor(e.target.value)}>
          {vendors.map((v) => (
            <option key={v} value={v}>
              {v === "all" ? "All vendors" : v}
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
              {s === "all" ? "All statuses" : STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      {pending ? (
        <p>Loading devices...</p>
      ) : (
        <DeviceTable devices={filtered} onSelect={(id) => navigate(`/devices/${id}`)} />
      )}
    </div>
  );
}
