import { formatApiDate, parseApiDate } from "../api/dates";
import type { AvailabilityEventOut } from "../api/types";
import { StatusBadge } from "./StatusBadge";

export function formatDuration(ms: number): string {
  const minutes = Math.floor(Math.max(0, ms) / 60_000);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}min`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

export function EventTimeline({ events }: { events: AvailabilityEventOut[] }) {
  if (events.length === 0) return <p>No availability events recorded.</p>;

  return (
    <ul className="event-timeline">
      {events.map((e) => {
        const start = parseApiDate(e.started_at).getTime();
        const end = e.ended_at ? parseApiDate(e.ended_at).getTime() : Date.now();
        return (
          <li key={e.id} className="event-timeline__item">
            <StatusBadge status={e.status} />
            <span>
              {formatApiDate(e.started_at)}
              {e.ended_at ? ` → ${formatApiDate(e.ended_at)}` : " → in progress"}
            </span>
            <span className="event-timeline__duration">{formatDuration(end - start)}</span>
          </li>
        );
      })}
    </ul>
  );
}
