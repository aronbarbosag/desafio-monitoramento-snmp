import { useNavigate, useParams } from "react-router-dom";
import { parseApiDate } from "../api/dates";
import { useDeviceEvents, useDeviceHistory, useDevices } from "../api/queries";
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

  // Mesma query/cache do inventário (useDevices) — evita o device aparecer
  // com um status diferente aqui do que na tela de inventário por causa de
  // duas fontes de dado buscadas em instantes distintos.
  const devices = useDevices();
  const history = useDeviceHistory(deviceId);
  const events = useDeviceEvents(deviceId);

  const d = devices.data?.find((device) => device.id === deviceId);

  if (devices.isLoading && !devices.data) return <p>Carregando device...</p>;
  if (!d) {
    if (devices.isError) {
      return <p>Falha ao carregar device. Verifique a conexão com o servidor.</p>;
    }
    return <p>Device não encontrado.</p>;
  }

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
            <td>{d.last_checked_at ? parseApiDate(d.last_checked_at).toLocaleString() : "—"}</td>
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
