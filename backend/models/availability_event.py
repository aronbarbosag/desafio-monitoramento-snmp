from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import DeviceStatus

if TYPE_CHECKING:
    from .device import Device


class AvailabilityEvent(Base):
    """Intervalo de tempo em que um Device permaneceu num status.

    Uma linha por MUDANÇA de estado (aberta pelo MetricsCollectionService ao
    detectar a transição), não uma linha por check — dá uptime % e histórico
    de indisponibilidade sem varrer o metric_history bruto. ended_at nulo
    significa evento em aberto (estado atual)."""

    __tablename__ = "availability_events"
    __table_args__ = (Index("ix_availability_events_device_started", "device_id", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    device: Mapped["Device"] = relationship()

    status: Mapped[DeviceStatus] = mapped_column(SAEnum(DeviceStatus, native_enum=False, length=16))
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
