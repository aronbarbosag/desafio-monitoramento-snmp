from datetime import datetime

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
