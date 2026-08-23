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
