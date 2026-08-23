from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session, joinedload

from models import MetricDefinition, MetricHistory


class MetricHistoryRepository:
    """Acesso a dados da entidade MetricHistory (série bruta de coletas)."""

    def __init__(self, session: Session):
        self._session = session

    def save_many(self, histories: list[MetricHistory]) -> None:
        if histories:
            self._session.add_all(histories)
            self._session.flush()

    def delete_older_than(self, cutoff: datetime) -> int:
        """Apaga leituras brutas mais velhas que cutoff — chamado só depois
        de MetricTrendRepository.upsert_hourly_aggregates ter agregado essas
        horas (ver run_housekeeping_cycle), senão perde dado sem trend
        correspondente. Numérico e texto são apagados igual: texto nunca vira
        trend (ver models/metric_trend.py), só existe na janela bruta."""
        result = self._session.execute(
            delete(MetricHistory).where(MetricHistory.collected_at < cutoff)
        )
        self._session.flush()
        return result.rowcount

    def list_by_device(self, device_id: int, limit: int) -> list[MetricHistory]:
        """Leituras mais recentes primeiro, com o MetricDefinition já
        carregado (evita N+1 pra expor key/name/unit na API)."""
        return (
            self._session.query(MetricHistory)
            .options(joinedload(MetricHistory.metric_definition))
            .filter(MetricHistory.device_id == device_id)
            .order_by(MetricHistory.collected_at.desc())
            .limit(limit)
            .all()
        )

    def list_by_device_and_metric_since(
        self, device_id: int, metric_key: str, since: datetime
    ) -> list[MetricHistory]:
        """Leituras de uma métrica específica do device desde `since`, mais
        antigas primeiro — usado pela camada de ETL (backend/etl/) pra montar
        série temporal. Métrica desconhecida devolve lista vazia (join não
        casa nenhuma linha), não erro."""
        return (
            self._session.query(MetricHistory)
            .join(MetricDefinition, MetricHistory.metric_definition_id == MetricDefinition.id)
            .filter(MetricHistory.device_id == device_id)
            .filter(MetricDefinition.key == metric_key)
            .filter(MetricHistory.collected_at >= since)
            .order_by(MetricHistory.collected_at.asc())
            .all()
        )
