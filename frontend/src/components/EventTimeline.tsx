import { parseApiDate } from "../api/dates";
import type { AvailabilityEventOut } from "../api/types";
import { StatusBadge } from "./StatusBadge";

function formatDuration(ms: number): string {
  const minutes = Math.floor(Math.max(0, ms) / 60_000);
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
    const start = parseApiDate(e.started_at).getTime();
    const end = e.ended_at ? parseApiDate(e.ended_at).getTime() : now;
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
        const start = parseApiDate(e.started_at).getTime();
        const end = e.ended_at ? parseApiDate(e.ended_at).getTime() : Date.now();
        return (
          <li key={e.id} className="event-timeline__item">
            <StatusBadge status={e.status} />
            <span>
              {parseApiDate(e.started_at).toLocaleString()}
              {e.ended_at ? ` → ${parseApiDate(e.ended_at).toLocaleString()}` : " → em curso"}
            </span>
            <span className="event-timeline__duration">{formatDuration(end - start)}</span>
          </li>
        );
      })}
    </ul>
  );
}
