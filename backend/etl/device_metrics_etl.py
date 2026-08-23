from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from repositories.metric_definition_repository import MetricDefinitionRepository
from repositories.metric_history_repository import MetricHistoryRepository
from repositories.metric_trend_repository import MetricTrendRepository

# Teto de pontos devolvidos por série, qualquer que seja o range pedido —
# sem isso, um range de 30d com poll a cada 60s devolveria dezenas de
# milhares de pontos pro frontend plotar.
MAX_POINTS = 200


@dataclass(frozen=True)
class ChartPoint:
    t: datetime
    v: float


@dataclass(frozen=True)
class ChartSeriesResult:
    metric_key: str
    metric_name: str
    unit: str | None
    points: list[ChartPoint]


def _resample_rule(range_hours: int) -> str:
    bucket_seconds = max(60, (range_hours * 3600) // MAX_POINTS)
    return f"{bucket_seconds}s"


class DeviceMetricsETL:
    """Monta a série temporal de uma métrica pronta pra gráfico (ECharts, no
    frontend) a partir de metric_history (bruto, retenção curta) +
    metric_trend (agregado horário, retenção longa) — etapa ETL do diagrama
    em backend/docs/fluxo_de_chamadas.png, entre o SQLDATABASE e o
    DASHBOARD."""

    def __init__(self, session: Session):
        self._session = session

    def build_series(self, device_id: int, metric_key: str, range_hours: int) -> ChartSeriesResult:
        definition = MetricDefinitionRepository(self._session).get_by_key(metric_key)
        if definition is None:
            return ChartSeriesResult(
                metric_key=metric_key, metric_name=metric_key, unit=None, points=[]
            )

        since = datetime.now(UTC) - timedelta(hours=range_hours)

        raw_rows = MetricHistoryRepository(self._session).list_by_device_and_metric_since(
            device_id, metric_key, since
        )
        raw_points = [
            (row.collected_at, row.value_numeric)
            for row in raw_rows
            if row.value_numeric is not None
        ]

        trend_rows = MetricTrendRepository(self._session).list_by_device_and_metric_since(
            device_id, metric_key, since
        )
        trend_points = [(row.bucket_start, row.value_avg) for row in trend_rows]

        # metric_history só cobre a retenção curta (ver
        # registry_history_housekeeping.py); trend complementa períodos mais
        # antigos, mas nunca duplica um instante já coberto pelo bruto.
        if raw_points:
            earliest_raw = min(t for t, _ in raw_points)
            trend_points = [(t, v) for t, v in trend_points if t < earliest_raw]

        combined = trend_points + raw_points
        if not combined:
            return ChartSeriesResult(
                metric_key=definition.key,
                metric_name=definition.name,
                unit=definition.unit,
                points=[],
            )

        series = pd.DataFrame(combined, columns=["t", "v"]).set_index("t").sort_index()["v"]
        resampled = series.resample(_resample_rule(range_hours)).mean().dropna()

        points = [
            ChartPoint(t=idx.to_pydatetime(), v=float(value)) for idx, value in resampled.items()
        ]
        return ChartSeriesResult(
            metric_key=definition.key,
            metric_name=definition.name,
            unit=definition.unit,
            points=points,
        )
