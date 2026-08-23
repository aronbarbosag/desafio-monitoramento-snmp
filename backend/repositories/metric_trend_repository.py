from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models import MetricDefinition, MetricHistory, MetricTrend


class MetricTrendRepository:
    """Acesso a dados da entidade MetricTrend (agregado por hora de métricas
    numéricas, ver models/metric_trend.py)."""

    def __init__(self, session: Session):
        self._session = session

    def upsert_hourly_aggregates(self, before: datetime) -> int:
        """Agrega em metric_trends todo metric_history numérico com
        collected_at < before (hora corrente nunca entra — ainda pode receber
        leituras, ver run_housekeeping_cycle). Upsert por
        (device_id, metric_definition_id, bucket_start): idempotente, rodar
        de novo sobre a mesma hora recalcula em vez de duplicar. Devolve
        quantos buckets foram gravados/atualizados."""
        bucket = func.date_trunc("hour", MetricHistory.collected_at)
        rows = self._session.execute(
            select(
                MetricHistory.device_id,
                MetricHistory.metric_definition_id,
                bucket.label("bucket_start"),
                func.min(MetricHistory.value_numeric),
                func.max(MetricHistory.value_numeric),
                func.avg(MetricHistory.value_numeric),
                func.count(MetricHistory.id),
            )
            .where(MetricHistory.value_numeric.isnot(None))
            .where(MetricHistory.collected_at < before)
            .group_by(MetricHistory.device_id, MetricHistory.metric_definition_id, bucket)
        ).all()

        if not rows:
            return 0

        stmt = pg_insert(MetricTrend).values(
            [
                {
                    "device_id": device_id,
                    "metric_definition_id": metric_definition_id,
                    "bucket_start": bucket_start,
                    "value_min": value_min,
                    "value_max": value_max,
                    "value_avg": float(value_avg),
                    "sample_count": sample_count,
                }
                for (
                    device_id,
                    metric_definition_id,
                    bucket_start,
                    value_min,
                    value_max,
                    value_avg,
                    sample_count,
                ) in rows
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_metric_trends_bucket",
            set_={
                "value_min": stmt.excluded.value_min,
                "value_max": stmt.excluded.value_max,
                "value_avg": stmt.excluded.value_avg,
                "sample_count": stmt.excluded.sample_count,
            },
        )
        self._session.execute(stmt)
        self._session.flush()
        return len(rows)

    def list_by_device(self, device_id: int) -> list[MetricTrend]:
        return (
            self._session.query(MetricTrend)
            .filter(MetricTrend.device_id == device_id)
            .order_by(MetricTrend.bucket_start.desc())
            .all()
        )

    def list_by_device_and_metric_since(
        self, device_id: int, metric_key: str, since: datetime
    ) -> list[MetricTrend]:
        """Buckets horários de uma métrica específica desde `since`, mais
        antigos primeiro — usado pela camada de ETL (backend/etl/) pra
        complementar a série além da retenção do dado bruto."""
        return (
            self._session.query(MetricTrend)
            .join(MetricDefinition, MetricTrend.metric_definition_id == MetricDefinition.id)
            .filter(MetricTrend.device_id == device_id)
            .filter(MetricDefinition.key == metric_key)
            .filter(MetricTrend.bucket_start >= since)
            .order_by(MetricTrend.bucket_start.asc())
            .all()
        )
