import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDevices } from "../api/queries";
import type { DeviceStatus } from "../api/types";
import { DeviceTable } from "../components/DeviceTable";
import { KpiCard } from "../components/KpiCard";
import { ScanButton } from "../components/ScanButton";
import { STATUS_LABEL } from "../components/StatusBadge";

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

  if (isLoading && !devices) return <p>Carregando devices...</p>;
  if (isError && !devices) return <p>Falha ao carregar devices.</p>;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Inventário de devices</h1>
        <ScanButton />
      </header>

      {isError && devices && (
        <p className="banner banner--warning">
          Sem conexão com o servidor — mostrando os últimos dados conhecidos.
        </p>
      )}

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
              {s === "all" ? "Todos os status" : STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      <DeviceTable devices={filtered} onSelect={(id) => navigate(`/devices/${id}`)} />
    </div>
  );
}
