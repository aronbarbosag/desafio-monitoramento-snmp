from sqlalchemy.orm import Session

from models import MetricHistory


class MetricHistoryRepository:
    """Acesso a dados da entidade MetricHistory (série bruta de coletas)."""

    def __init__(self, session: Session):
        self._session = session

    def save_many(self, histories: list[MetricHistory]) -> None:
        if histories:
            self._session.add_all(histories)
            self._session.flush()
