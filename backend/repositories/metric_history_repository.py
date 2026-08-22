from sqlalchemy.orm import Session, joinedload

from models import MetricHistory


class MetricHistoryRepository:
    """Acesso a dados da entidade MetricHistory (série bruta de coletas)."""

    def __init__(self, session: Session):
        self._session = session

    def save_many(self, histories: list[MetricHistory]) -> None:
        if histories:
            self._session.add_all(histories)
            self._session.flush()

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
