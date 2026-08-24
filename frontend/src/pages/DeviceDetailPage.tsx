import { useNavigate, useParams } from "react-router-dom";
import { formatApiDate } from "../api/dates";
import { useDeviceAvailability, useDeviceEvents, useDeviceHistory, useDevices } from "../api/queries";
import type { MetricHistoryOut } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { KpiCard } from "../components/KpiCard";
import { MetricCard } from "../components/MetricCard";
import { EventTimeline, formatDuration } from "../components/EventTimeline";

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

  // Mesma query/cache do inventário (useDevices) — evita o device aparecer
  // com um status diferente aqui do que na tela de inventário por causa de
  // duas fontes de dado buscadas em instantes distintos.
  const devices = useDevices();
  const history = useDeviceHistory(deviceId);
  const events = useDeviceEvents(deviceId);
  const availability = useDeviceAvailability(deviceId);

  const d = devices.data?.find((device) => device.id === deviceId);
  // Mostra o botão de voltar desde o primeiro render — só o conteúdo (header,
  // métricas, disponibilidade) fica pendente até a GET responder.
  const pending = devices.isLoading && !devices.data;

  const groups = groupByMetricKey(history.data ?? []);

  return (
    <div className="page">
      <button className="btn btn-secondary" onClick={() => navigate("/")} style={{ alignSelf: "flex-start" }}>
        ← Inventory
      </button>

      {pending && <p>Loading device...</p>}

      {!pending && !d && (
        <p>
          {devices.isError
            ? "Failed to load device. Check the server connection."
            : "Device not found."}
          {devices.isError && (
            <button
              className="btn btn-secondary"
              style={{ marginLeft: "var(--space-4)" }}
              onClick={() => devices.refetch()}
              disabled={devices.isRefetching}
            >
              {devices.isRefetching ? "Retrying..." : "Retry"}
            </button>
          )}
        </p>
      )}

      {d && (
        <>
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
                <td>{d.mac ?? "— (found via ping sweep, no ARP data)"}</td>
              </tr>
              <tr>
                <td>Vendor / model</td>
                <td>{[d.vendor, d.model_name].filter(Boolean).join(" ") || "—"}</td>
              </tr>
              <tr>
                <td>sysDescr</td>
                <td>{d.sys_descr ?? "—"}</td>
              </tr>
              <tr>
                <td>Contact</td>
                <td>{d.sys_contact ?? "—"}</td>
              </tr>
              <tr>
                <td>Location</td>
                <td>{d.sys_location ?? "—"}</td>
              </tr>
              <tr>
                <td>Poll interval</td>
                <td>{d.poll_interval_seconds}s</td>
              </tr>
              <tr>
                <td>Last checked</td>
                <td>{d.last_checked_at ? formatApiDate(d.last_checked_at) : "—"}</td>
              </tr>
            </tbody>
          </table>

          <section>
            <h2>Metrics</h2>
            {Object.keys(groups).length === 0 && <p>No metric history.</p>}
            <div className="metric-grid">
              {Object.entries(groups).map(([key, points]) => (
                <MetricCard key={key} points={points} />
              ))}
            </div>
          </section>

          <section>
            <h2>Availability (last {availability.data?.range_hours ?? 24}h)</h2>
            <div className="kpi-grid">
              <KpiCard
                label="Availability"
                value={availability.data ? `${availability.data.availability_pct.toFixed(1)}%` : "—"}
              />
              <KpiCard
                label="Downtime"
                value={availability.data ? formatDuration(availability.data.downtime_seconds * 1000) : "—"}
              />
              <KpiCard
                label="MTTR"
                value={
                  availability.data?.mttr_seconds != null
                    ? formatDuration(availability.data.mttr_seconds * 1000)
                    : "—"
                }
              />
            </div>
            <EventTimeline events={events.data ?? []} />
          </section>
        </>
      )}
    </div>
  );
}
