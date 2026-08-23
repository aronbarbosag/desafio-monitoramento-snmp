from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import AvailabilityEvent, DeviceStatus


class AvailabilityEventRepository:
    """Acesso a dados da entidade AvailabilityEvent (histórico de transições
    de status de um Device)."""

    def __init__(self, session: Session):
        self._session = session

    def close_open_event(self, device_id: int, ended_at: datetime) -> None:
        """Fecha o evento em aberto (ended_at nulo) do device, se existir —
        chamado logo antes de abrir o próximo, ao detectar uma transição."""
        open_event = (
            self._session.query(AvailabilityEvent)
            .filter(AvailabilityEvent.device_id == device_id)
            .filter(AvailabilityEvent.ended_at.is_(None))
            .one_or_none()
        )
        if open_event is not None:
            open_event.ended_at = ended_at
            self._session.flush()

    def open_event(
        self,
        device_id: int,
        status: DeviceStatus,
        started_at: datetime,
    ) -> AvailabilityEvent:
        event = AvailabilityEvent(device_id=device_id, status=status, started_at=started_at)
        self._session.add(event)
        self._session.flush()
        return event

    def list_by_device(self, device_id: int, limit: int) -> list[AvailabilityEvent]:
        """Eventos mais recentes primeiro (o em aberto, se houver, vem sempre
        primeiro por ter o started_at mais recente)."""
        return (
            self._session.query(AvailabilityEvent)
            .filter(AvailabilityEvent.device_id == device_id)
            .order_by(AvailabilityEvent.started_at.desc())
            .limit(limit)
            .all()
        )

    def _overlaps_since(self, query, since: datetime):
        """Evento se sobrepõe à janela [since, agora) se ainda está aberto
        (ended_at nulo) ou se fechou depois de `since` — um evento fechado
        antes disso não tem nenhum segundo dentro da janela."""
        return query.filter(
            or_(AvailabilityEvent.ended_at.is_(None), AvailabilityEvent.ended_at >= since)
        )

    def list_by_device_since(self, device_id: int, since: datetime) -> list[AvailabilityEvent]:
        """Eventos do device que se sobrepõem à janela [since, agora) — usado
        pela camada de ETL (backend/etl/) pra calcular % de disponibilidade."""
        query = self._session.query(AvailabilityEvent).filter(
            AvailabilityEvent.device_id == device_id
        )
        return self._overlaps_since(query, since).order_by(AvailabilityEvent.started_at.asc()).all()

    def list_since(self, since: datetime) -> list[AvailabilityEvent]:
        """Como list_by_device_since, mas pra todos os devices de uma vez —
        usado pelo resumo agregado do dashboard (evita N queries, uma por
        device)."""
        query = self._session.query(AvailabilityEvent)
        return self._overlaps_since(query, since).order_by(AvailabilityEvent.started_at.asc()).all()
